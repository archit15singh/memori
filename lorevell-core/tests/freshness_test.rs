use lorevell_core::{schema, Freshness, Lorevell, LorevellError, SearchQuery};
use rusqlite::Connection;
use std::path::PathBuf;

struct DatabaseFile(PathBuf);
impl DatabaseFile {
    fn new() -> Self {
        Self(std::env::temp_dir().join(format!("lorevell-freshness-{}.db", uuid::Uuid::new_v4())))
    }
    fn path(&self) -> &str {
        self.0.to_str().unwrap()
    }
}
impl Drop for DatabaseFile {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.0);
    }
}

fn legacy_database(path: &str) -> Connection {
    let conn = Connection::open(path).unwrap();
    conn.execute_batch(
        "CREATE TABLE lorevelles (
            id TEXT PRIMARY KEY, content TEXT NOT NULL, vector BLOB, metadata TEXT,
            created_at REAL NOT NULL, updated_at REAL NOT NULL,
            last_accessed REAL DEFAULT 0, access_count INTEGER DEFAULT 0);
         CREATE VIRTUAL TABLE lorevelles_fts USING fts5(content, content=lorevelles, content_rowid=rowid);
         CREATE TRIGGER lorevelles_ai AFTER INSERT ON lorevelles BEGIN
            INSERT INTO lorevelles_fts(rowid, content) VALUES(new.rowid, new.content || ' ' || coalesce(new.metadata, ''));
         END;
         CREATE TRIGGER lorevelles_ad AFTER DELETE ON lorevelles BEGIN
            INSERT INTO lorevelles_fts(lorevelles_fts,rowid,content) VALUES('delete',old.rowid,old.content || ' ' || coalesce(old.metadata, ''));
         END;
         CREATE TRIGGER lorevelles_au AFTER UPDATE ON lorevelles BEGIN
            INSERT INTO lorevelles_fts(lorevelles_fts,rowid,content) VALUES('delete',old.rowid,old.content || ' ' || coalesce(old.metadata, ''));
            INSERT INTO lorevelles_fts(rowid,content) VALUES(new.rowid,new.content || ' ' || coalesce(new.metadata, ''));
         END;
         CREATE INDEX idx_lorevelles_type ON lorevelles(json_extract(metadata, '$.type'));
         INSERT INTO lorevelles(id,content,created_at,updated_at,last_accessed,access_count)
            VALUES('legacy','PostgreSQL architecture',100,200,250,7);
         PRAGMA user_version=3;"
    ).unwrap();
    conn
}

#[test]
fn v3_migration_preserves_records_fts_and_access_and_is_idempotent() {
    let file = DatabaseFile::new();
    drop(legacy_database(file.path()));
    for _ in 0..2 {
        let db = Lorevell::open(file.path()).unwrap();
        let record = db.get_readonly("legacy").unwrap().unwrap();
        assert_eq!(record.created_at, 100.0);
        assert_eq!(record.updated_at, 200.0);
        assert_eq!(record.content_updated_at, 200.0); // legacy last-write approximation
        assert_eq!(record.validated_at, None);
        assert_eq!(record.last_accessed, 250.0);
        assert_eq!(record.access_count, 7);
        assert_eq!(
            db.search(SearchQuery {
                text: Some("PostgreSQL".into()),
                text_only: true,
                ..Default::default()
            })
            .unwrap()
            .len(),
            1
        );
    }
    let conn = Connection::open(file.path()).unwrap();
    assert_eq!(
        conn.pragma_query_value(None, "user_version", |row| row.get::<_, i32>(0))
            .unwrap(),
        schema::SCHEMA_VERSION
    );
}

#[test]
fn failed_migration_rolls_back_columns_and_version() {
    let conn = legacy_database(":memory:");
    // Force failure at the second ALTER after the first column was added.
    conn.execute("ALTER TABLE lorevelles ADD COLUMN validated_at REAL", [])
        .unwrap();
    assert!(schema::init_db(&conn).is_err());
    assert_eq!(
        conn.pragma_query_value(None, "user_version", |row| row.get::<_, i32>(0))
            .unwrap(),
        3
    );
    assert!(conn
        .prepare("SELECT content_updated_at FROM lorevelles")
        .is_err());
    assert_eq!(
        conn.query_row("SELECT content FROM lorevelles", [], |row| row
            .get::<_, String>(0))
            .unwrap(),
        "PostgreSQL architecture"
    );
}

#[test]
fn newer_schema_is_rejected_without_creating_tables() {
    let conn = Connection::open_in_memory().unwrap();
    conn.pragma_update(None, "user_version", schema::SCHEMA_VERSION + 1)
        .unwrap();
    assert!(matches!(
        schema::init_db(&conn),
        Err(LorevellError::UnsupportedSchema(_))
    ));
    let count: i64 = conn
        .query_row(
            "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='lorevelles'",
            [],
            |row| row.get(0),
        )
        .unwrap();
    assert_eq!(count, 0);
}

#[test]
fn failed_content_and_metadata_update_preserves_clock_and_history() {
    let file = DatabaseFile::new();
    let db = Lorevell::open(file.path()).unwrap();
    db.insert_with_id_and_freshness(
        "old",
        "old fact",
        Some(&[1.0, 0.0]),
        None,
        100.0,
        200.0,
        Freshness {
            content_updated_at: 150.0,
            validated_at: Some(175.0),
        },
    )
    .unwrap();
    let conn = Connection::open(file.path()).unwrap();
    conn.execute_batch("CREATE TRIGGER reject_metadata BEFORE UPDATE OF metadata ON lorevelles BEGIN SELECT RAISE(ABORT, 'test rejection'); END;").unwrap();
    assert!(db
        .update(
            "old",
            Some("new fact"),
            Some(&[0.0, 1.0]),
            Some(serde_json::json!({"tag": true})),
            true
        )
        .is_err());
    let record = db.get_readonly("old").unwrap().unwrap();
    assert_eq!(record.content, "old fact");
    assert_eq!(record.content_updated_at, 150.0);
    assert_eq!(record.validated_at, Some(175.0));
    assert_eq!(record.vector, Some(vec![1.0, 0.0]));
    assert_eq!(record.updated_at, 200.0);
}

#[test]
fn stale_review_uses_factual_age_even_after_reads_and_tag_writes() {
    let db = Lorevell::open(":memory:").unwrap();
    db.insert_with_id("old", "old fact", Some(&[1.0, 0.0]), None, 100.0, 100.0)
        .unwrap();
    db.get("old").unwrap();
    db.update(
        "old",
        None,
        Some(&[1.0, 0.0]),
        Some(serde_json::json!({"tag": true})),
        true,
    )
    .unwrap();
    // Previously the CLI only inspected 20 candidates before testing for staleness.
    for index in 0..21 {
        let id = format!("validated-{index}");
        db.insert_with_id(
            &id,
            "revalidated fact",
            Some(&[1.0, 0.0]),
            None,
            100.0,
            100.0,
        )
        .unwrap();
        db.revalidate(&id).unwrap();
    }
    let stale = db.stale(200.0, 5).unwrap();
    assert_eq!(stale.len(), 1);
    assert_eq!(stale[0].id, "old");
    db.revalidate("old").unwrap();
    assert!(db.stale(200.0, 5).unwrap().is_empty());
    assert!(matches!(
        db.stale(f64::NAN, 5),
        Err(LorevellError::InvalidTimestamp(_))
    ));
}

#[test]
fn restores_validate_clocks_before_any_write() {
    let db = Lorevell::open(":memory:").unwrap();
    for freshness in [
        Freshness {
            content_updated_at: f64::INFINITY,
            validated_at: None,
        },
        Freshness {
            content_updated_at: 100.0,
            validated_at: Some(f64::NAN),
        },
    ] {
        assert!(matches!(
            db.insert_with_id_and_freshness(
                "bad",
                "bad",
                Some(&[1.0]),
                None,
                100.0,
                100.0,
                freshness
            ),
            Err(LorevellError::InvalidTimestamp(_))
        ));
    }
    assert_eq!(db.count().unwrap(), 0);
}

#[test]
fn old_negative_similarity_does_not_receive_an_age_boost() {
    let db = Lorevell::open(":memory:").unwrap();
    db.insert_with_id("old", "old", Some(&[1.0, 0.0]), None, 0.0, 0.0)
        .unwrap();
    db.insert("new", Some(&[1.0, 0.0]), None, None, true)
        .unwrap();
    let results = db
        .search(SearchQuery {
            vector: Some(vec![-1.0, 0.0]),
            ..Default::default()
        })
        .unwrap();
    assert_eq!(results[0].content, "new");
    assert!(results[1].score.unwrap().is_finite());
    assert!(results[1].score < results[0].score);
}
