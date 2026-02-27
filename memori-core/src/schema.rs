use rusqlite::Connection;

pub fn init_db(conn: &Connection) -> rusqlite::Result<()> {
  // Base table and WAL mode (always idempotent)
  conn.execute_batch(
    "
    PRAGMA journal_mode=WAL;

    CREATE TABLE IF NOT EXISTS memories (
        id          TEXT PRIMARY KEY,
        content     TEXT NOT NULL,
        vector      BLOB,
        metadata    TEXT,
        created_at  REAL NOT NULL,
        updated_at  REAL NOT NULL
    );
    ",
  )?;

  // Check schema version to decide if FTS5 needs migration
  let version: i32 = conn.pragma_query_value(None, "user_version", |r| r.get(0))?;

  if version < 1 {
    // Drop old FTS and triggers, recreate with metadata-aware triggers.
    // The FTS5 content column label stays "content" but the data fed into it
    // via triggers now concatenates content + metadata JSON text, so text
    // searches match metadata values (e.g. searching "kafka" hits
    // memories where metadata contains {"topic": "kafka"}).
    conn.execute_batch(
      "
      DROP TRIGGER IF EXISTS memories_ai;
      DROP TRIGGER IF EXISTS memories_ad;
      DROP TRIGGER IF EXISTS memories_au;
      DROP TABLE IF EXISTS memories_fts;

      CREATE VIRTUAL TABLE memories_fts USING fts5(
          content,
          content=memories,
          content_rowid=rowid
      );

      CREATE TRIGGER memories_ai AFTER INSERT ON memories BEGIN
          INSERT INTO memories_fts(rowid, content)
          VALUES (new.rowid, new.content || ' ' || COALESCE(new.metadata, ''));
      END;

      CREATE TRIGGER memories_ad AFTER DELETE ON memories BEGIN
          INSERT INTO memories_fts(memories_fts, rowid, content)
          VALUES('delete', old.rowid, old.content || ' ' || COALESCE(old.metadata, ''));
      END;

      CREATE TRIGGER memories_au AFTER UPDATE ON memories BEGIN
          INSERT INTO memories_fts(memories_fts, rowid, content)
          VALUES('delete', old.rowid, old.content || ' ' || COALESCE(old.metadata, ''));
          INSERT INTO memories_fts(rowid, content)
          VALUES (new.rowid, new.content || ' ' || COALESCE(new.metadata, ''));
      END;

      INSERT INTO memories_fts(memories_fts) VALUES('rebuild');

      PRAGMA user_version = 1;
      ",
    )?;
  }

  // Re-read version after potential v0->v1 migration
  let version: i32 = conn.pragma_query_value(None, "user_version", |r| r.get(0))?;

  if version < 2 {
    // Add access tracking columns for v0.3 ranking boost.
    // SQLite ALTER TABLE ADD COLUMN sets defaults for existing rows.
    conn.execute_batch(
      "
      ALTER TABLE memories ADD COLUMN last_accessed REAL DEFAULT 0.0;
      ALTER TABLE memories ADD COLUMN access_count INTEGER DEFAULT 0;
      PRAGMA user_version = 2;
      ",
    )?;
  }

  // Re-read version after potential v1->v2 migration
  let version: i32 = conn.pragma_query_value(None, "user_version", |r| r.get(0))?;

  if version < 3 {
    // Expression index on metadata $.type for fast filtered queries.
    // json_extract expression indexes are supported since SQLite 3.9.0.
    conn.execute_batch(
      "
      CREATE INDEX IF NOT EXISTS idx_memories_type
          ON memories(json_extract(metadata, '$.type'));
      PRAGMA user_version = 3;
      ",
    )?;
  }

  Ok(())
}
