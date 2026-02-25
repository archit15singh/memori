use memori_core::{Memori, SearchQuery};
use serde_json::json;
use std::time::{SystemTime, UNIX_EPOCH};

fn open_temp() -> Memori {
    Memori::open(":memory:").expect("failed to open in-memory db")
}

#[test]
fn test_insert_and_get() {
    let db = open_temp();
    let id = db
        .insert("hello world", None, Some(json!({"tag": "test"})))
        .unwrap();

    let mem = db.get(&id).unwrap().expect("memory should exist");
    assert_eq!(mem.content, "hello world");
    assert_eq!(mem.metadata, Some(json!({"tag": "test"})));
    assert!(mem.vector.is_none());
    assert!(mem.created_at > 0.0);
}

#[test]
fn test_insert_with_vector() {
    let db = open_temp();
    let vec = vec![1.0, 2.0, 3.0];
    let id = db.insert("with vector", Some(&vec), None).unwrap();

    let mem = db.get(&id).unwrap().unwrap();
    let stored = mem.vector.unwrap();
    assert_eq!(stored.len(), 3);
    assert!((stored[0] - 1.0).abs() < 1e-6);
    assert!((stored[1] - 2.0).abs() < 1e-6);
    assert!((stored[2] - 3.0).abs() < 1e-6);
}

#[test]
fn test_update_content() {
    let db = open_temp();
    let id = db.insert("original", None, None).unwrap();
    db.update(&id, Some("updated"), None, None).unwrap();

    let mem = db.get(&id).unwrap().unwrap();
    assert_eq!(mem.content, "updated");
    assert!(mem.updated_at >= mem.created_at);
}

#[test]
fn test_update_metadata() {
    let db = open_temp();
    let id = db.insert("test", None, Some(json!({"a": 1}))).unwrap();
    db.update(&id, None, None, Some(json!({"b": 2}))).unwrap();

    let mem = db.get(&id).unwrap().unwrap();
    assert_eq!(mem.metadata, Some(json!({"b": 2})));
}

#[test]
fn test_update_nonexistent() {
    let db = open_temp();
    let result = db.update("nonexistent-id", Some("x"), None, None);
    assert!(result.is_err());
}

#[test]
fn test_delete() {
    let db = open_temp();
    let id = db.insert("to delete", None, None).unwrap();
    assert_eq!(db.count().unwrap(), 1);

    db.delete(&id).unwrap();
    assert_eq!(db.count().unwrap(), 0);
    assert!(db.get(&id).unwrap().is_none());
}

#[test]
fn test_delete_nonexistent() {
    let db = open_temp();
    let result = db.delete("nonexistent-id");
    assert!(result.is_err());
}

#[test]
fn test_count() {
    let db = open_temp();
    assert_eq!(db.count().unwrap(), 0);

    for i in 0..5 {
        db.insert(&format!("memory {}", i), None, None).unwrap();
    }
    assert_eq!(db.count().unwrap(), 5);
}

#[test]
fn test_vector_search_cosine_similarity() {
    let db = open_temp();

    // Insert vectors with known similarity properties
    let v1 = vec![1.0, 0.0, 0.0];
    let v2 = vec![0.0, 1.0, 0.0];
    let v3 = vec![0.9, 0.1, 0.0]; // similar to v1

    db.insert("north", Some(&v1), None).unwrap();
    db.insert("east", Some(&v2), None).unwrap();
    db.insert("mostly north", Some(&v3), None).unwrap();

    let query = SearchQuery {
        vector: Some(vec![1.0, 0.0, 0.0]),
        limit: 3,
        ..Default::default()
    };

    let results = db.search(query).unwrap();
    assert_eq!(results.len(), 3);
    // "north" (identical vector) should be first
    assert_eq!(results[0].content, "north");
    // "mostly north" should be second
    assert_eq!(results[1].content, "mostly north");
    // All should have scores
    assert!(results[0].score.unwrap() > results[1].score.unwrap());
    assert!(results[1].score.unwrap() > results[2].score.unwrap());
}

#[test]
fn test_text_search_fts5() {
    let db = open_temp();

    db.insert("the quick brown fox jumps over the lazy dog", None, None)
        .unwrap();
    db.insert("a fast red car drives on the highway", None, None)
        .unwrap();
    db.insert("the brown bear sleeps in the forest", None, None)
        .unwrap();

    let query = SearchQuery {
        text: Some("brown".to_string()),
        limit: 10,
        ..Default::default()
    };

    let results = db.search(query).unwrap();
    assert_eq!(results.len(), 2);
    assert!(results.iter().all(|r| r.content.contains("brown")));
}

#[test]
fn test_hybrid_search() {
    let db = open_temp();

    let v1 = vec![1.0, 0.0, 0.0];
    let v2 = vec![0.0, 1.0, 0.0];
    let v3 = vec![0.5, 0.5, 0.0];

    db.insert("machine learning models", Some(&v1), None)
        .unwrap();
    db.insert("database optimization", Some(&v2), None)
        .unwrap();
    db.insert("machine learning optimization", Some(&v3), None)
        .unwrap();

    let query = SearchQuery {
        vector: Some(vec![0.9, 0.1, 0.0]),
        text: Some("optimization".to_string()),
        limit: 3,
        ..Default::default()
    };

    let results = db.search(query).unwrap();
    assert!(!results.is_empty());
    // "machine learning optimization" should rank high (matches both vector and text)
    assert!(results
        .iter()
        .any(|r| r.content == "machine learning optimization"));
}

#[test]
fn test_metadata_filter() {
    let db = open_temp();

    db.insert("preference: dark mode", None, Some(json!({"type": "preference"})))
        .unwrap();
    db.insert("fact: earth is round", None, Some(json!({"type": "fact"})))
        .unwrap();
    db.insert("preference: vim keys", None, Some(json!({"type": "preference"})))
        .unwrap();

    let query = SearchQuery {
        filter: Some(json!({"type": "preference"})),
        limit: 10,
        ..Default::default()
    };

    let results = db.search(query).unwrap();
    assert_eq!(results.len(), 2);
    assert!(results.iter().all(|r| {
        r.metadata
            .as_ref()
            .unwrap()
            .get("type")
            .unwrap()
            .as_str()
            .unwrap()
            == "preference"
    }));
}

#[test]
fn test_search_no_query_returns_recent() {
    let db = open_temp();

    for i in 0..5 {
        db.insert(&format!("memory {}", i), None, None).unwrap();
    }

    let query = SearchQuery {
        limit: 3,
        ..Default::default()
    };

    let results = db.search(query).unwrap();
    assert_eq!(results.len(), 3);
}

#[test]
fn test_vector_search_limit() {
    let db = open_temp();

    for i in 0..10 {
        let v = vec![i as f32, 0.0, 0.0];
        db.insert(&format!("item {}", i), Some(&v), None).unwrap();
    }

    let query = SearchQuery {
        vector: Some(vec![5.0, 0.0, 0.0]),
        limit: 3,
        ..Default::default()
    };

    let results = db.search(query).unwrap();
    assert_eq!(results.len(), 3);
}

#[test]
fn test_empty_db_search() {
    let db = open_temp();

    let query = SearchQuery {
        text: Some("anything".to_string()),
        limit: 10,
        ..Default::default()
    };

    let results = db.search(query).unwrap();
    assert!(results.is_empty());
}

#[test]
fn test_insert_with_id() {
    let db = open_temp();
    let ts = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs_f64();

    let id = db
        .insert_with_id(
            "custom-id-123",
            "imported memory",
            None,
            Some(json!({"type": "fact"})),
            ts - 3600.0, // created 1 hour ago
            ts,
        )
        .unwrap();

    assert_eq!(id, "custom-id-123");
    let mem = db.get("custom-id-123").unwrap().unwrap();
    assert_eq!(mem.content, "imported memory");
    assert_eq!(mem.metadata, Some(json!({"type": "fact"})));
    assert!((mem.created_at - (ts - 3600.0)).abs() < 0.01);
}

#[test]
fn test_type_distribution() {
    let db = open_temp();
    db.insert("pref 1", None, Some(json!({"type": "preference"})))
        .unwrap();
    db.insert("pref 2", None, Some(json!({"type": "preference"})))
        .unwrap();
    db.insert("fact 1", None, Some(json!({"type": "fact"})))
        .unwrap();
    db.insert("no type", None, None).unwrap();

    let dist = db.type_distribution().unwrap();
    assert_eq!(dist.get("preference"), Some(&2));
    assert_eq!(dist.get("fact"), Some(&1));
    assert_eq!(dist.len(), 2); // "no type" excluded
}

#[test]
fn test_delete_before() {
    let db = open_temp();
    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs_f64();

    // Insert with old timestamps via insert_with_id
    db.insert_with_id("old-1", "old memory", None, None, now - 7200.0, now - 7200.0)
        .unwrap();
    db.insert_with_id("old-2", "also old", None, None, now - 3600.0, now - 3600.0)
        .unwrap();
    // Recent one via normal insert
    db.insert("recent memory", None, None).unwrap();

    assert_eq!(db.count().unwrap(), 3);

    // Delete memories created before 30 minutes ago
    let deleted = db.delete_before(now - 1800.0).unwrap();
    assert_eq!(deleted, 2);
    assert_eq!(db.count().unwrap(), 1);
}

#[test]
fn test_delete_by_type() {
    let db = open_temp();
    db.insert("temp 1", None, Some(json!({"type": "temporary"})))
        .unwrap();
    db.insert("temp 2", None, Some(json!({"type": "temporary"})))
        .unwrap();
    db.insert("fact 1", None, Some(json!({"type": "fact"})))
        .unwrap();
    db.insert("no type", None, None).unwrap();

    let deleted = db.delete_by_type("temporary").unwrap();
    assert_eq!(deleted, 2);
    assert_eq!(db.count().unwrap(), 2);
}

#[test]
fn test_fts5_hyphenated_search() {
    let db = open_temp();

    db.insert(
        "some note",
        None,
        Some(json!({"type": "architecture", "topic": "fts5-migration"})),
    )
    .unwrap();

    // Hyphenated terms should not crash FTS5 (hyphens are FTS5 operators)
    let query = SearchQuery {
        text: Some("fts5-migration".to_string()),
        limit: 10,
        ..Default::default()
    };

    let results = db.search(query).unwrap();
    assert_eq!(results.len(), 1);
    assert_eq!(results[0].content, "some note");
}

#[test]
fn test_fts5_metadata_search() {
    let db = open_temp();

    db.insert(
        "some architecture note",
        None,
        Some(json!({"type": "architecture", "topic": "kafka"})),
    )
    .unwrap();
    db.insert("unrelated note", None, Some(json!({"type": "fact"})))
        .unwrap();

    // Search for "kafka" which only appears in metadata, not content
    let query = SearchQuery {
        text: Some("kafka".to_string()),
        limit: 10,
        ..Default::default()
    };

    let results = db.search(query).unwrap();
    assert_eq!(results.len(), 1);
    assert_eq!(results[0].content, "some architecture note");
}
