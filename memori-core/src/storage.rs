use rusqlite::params;
use serde_json::Value;
use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};

use crate::types::{Memory, MemoriError, Result};

fn now() -> f64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs_f64()
}

fn vec_to_blob(v: &[f32]) -> &[u8] {
    unsafe { std::slice::from_raw_parts(v.as_ptr() as *const u8, v.len() * 4) }
}

fn blob_to_vec(b: &[u8]) -> Vec<f32> {
    assert!(b.len() % 4 == 0);
    let mut v = vec![0.0f32; b.len() / 4];
    unsafe {
        std::ptr::copy_nonoverlapping(b.as_ptr(), v.as_mut_ptr() as *mut u8, b.len());
    }
    v
}

pub fn insert(
    conn: &rusqlite::Connection,
    content: &str,
    vector: Option<&[f32]>,
    metadata: Option<Value>,
) -> Result<String> {
    let id = uuid::Uuid::new_v4().to_string();
    let ts = now();
    let vector_blob = vector.map(vec_to_blob);
    let metadata_str = metadata.map(|m| m.to_string());

    conn.execute(
        "INSERT INTO memories (id, content, vector, metadata, created_at, updated_at)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
        params![id, content, vector_blob, metadata_str, ts, ts],
    )?;

    Ok(id)
}

pub fn insert_with_id(
    conn: &rusqlite::Connection,
    id: &str,
    content: &str,
    vector: Option<&[f32]>,
    metadata: Option<Value>,
    created_at: f64,
    updated_at: f64,
) -> Result<String> {
    let vector_blob = vector.map(vec_to_blob);
    let metadata_str = metadata.map(|m| m.to_string());

    conn.execute(
        "INSERT INTO memories (id, content, vector, metadata, created_at, updated_at)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
        params![id, content, vector_blob, metadata_str, created_at, updated_at],
    )?;

    Ok(id.to_string())
}

pub fn get(conn: &rusqlite::Connection, id: &str) -> Result<Option<Memory>> {
    let mut stmt = conn.prepare(
        "SELECT id, content, vector, metadata, created_at, updated_at
         FROM memories WHERE id = ?1",
    )?;

    let mut rows = stmt.query(params![id])?;
    match rows.next()? {
        Some(row) => Ok(Some(row_to_memory(row)?)),
        None => Ok(None),
    }
}

pub fn update(
    conn: &rusqlite::Connection,
    id: &str,
    content: Option<&str>,
    vector: Option<&[f32]>,
    metadata: Option<Value>,
) -> Result<()> {
    let existing = get(conn, id)?;
    if existing.is_none() {
        return Err(MemoriError::NotFound(id.to_string()));
    }

    let ts = now();

    if let Some(content) = content {
        conn.execute(
            "UPDATE memories SET content = ?1, updated_at = ?2 WHERE id = ?3",
            params![content, ts, id],
        )?;
    }

    if let Some(v) = vector {
        let blob = vec_to_blob(v);
        conn.execute(
            "UPDATE memories SET vector = ?1, updated_at = ?2 WHERE id = ?3",
            params![blob, ts, id],
        )?;
    }

    if let Some(m) = metadata {
        let json_str = m.to_string();
        conn.execute(
            "UPDATE memories SET metadata = ?1, updated_at = ?2 WHERE id = ?3",
            params![json_str, ts, id],
        )?;
    }

    Ok(())
}

pub fn delete(conn: &rusqlite::Connection, id: &str) -> Result<()> {
    let affected = conn.execute("DELETE FROM memories WHERE id = ?1", params![id])?;
    if affected == 0 {
        return Err(MemoriError::NotFound(id.to_string()));
    }
    Ok(())
}

pub fn count(conn: &rusqlite::Connection) -> Result<usize> {
    let c: i64 = conn.query_row("SELECT COUNT(*) FROM memories", [], |row| row.get(0))?;
    Ok(c as usize)
}

pub fn type_distribution(conn: &rusqlite::Connection) -> Result<HashMap<String, usize>> {
    let mut stmt = conn.prepare(
        "SELECT json_extract(metadata, '$.type') as mtype, COUNT(*) as cnt
         FROM memories WHERE mtype IS NOT NULL GROUP BY mtype",
    )?;

    let mut map = HashMap::new();
    let mut rows = stmt.query([])?;
    while let Some(row) = rows.next()? {
        let mtype: String = row.get(0)?;
        let cnt: i64 = row.get(1)?;
        map.insert(mtype, cnt as usize);
    }

    Ok(map)
}

pub fn delete_before(conn: &rusqlite::Connection, before_timestamp: f64) -> Result<usize> {
    let affected = conn.execute(
        "DELETE FROM memories WHERE created_at < ?1",
        params![before_timestamp],
    )?;
    Ok(affected)
}

pub fn delete_by_type(conn: &rusqlite::Connection, type_value: &str) -> Result<usize> {
    let affected = conn.execute(
        "DELETE FROM memories WHERE json_extract(metadata, '$.type') = ?1",
        params![type_value],
    )?;
    Ok(affected)
}

pub fn row_to_memory(row: &rusqlite::Row) -> rusqlite::Result<Memory> {
    let vector_blob: Option<Vec<u8>> = row.get(2)?;
    let metadata_str: Option<String> = row.get(3)?;

    Ok(Memory {
        id: row.get(0)?,
        content: row.get(1)?,
        vector: vector_blob.map(|b| blob_to_vec(&b)),
        metadata: metadata_str.and_then(|s| serde_json::from_str(&s).ok()),
        created_at: row.get(4)?,
        updated_at: row.get(5)?,
        score: None,
    })
}
