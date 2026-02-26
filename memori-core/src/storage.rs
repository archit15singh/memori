use rusqlite::params;
use serde_json::Value;
use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};

use crate::types::{InsertResult, Memory, MemoriError, Result};

fn now() -> f64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs_f64()
}

pub fn vec_to_blob(v: &[f32]) -> &[u8] {
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

fn cosine_similarity(a: &[f32], b: &[f32]) -> f32 {
    if a.len() != b.len() || a.is_empty() {
        return 0.0;
    }

    let mut dot = 0.0f32;
    let mut norm_a = 0.0f32;
    let mut norm_b = 0.0f32;

    for i in 0..a.len() {
        dot += a[i] * b[i];
        norm_a += a[i] * a[i];
        norm_b += b[i] * b[i];
    }

    let denom = norm_a.sqrt() * norm_b.sqrt();
    if denom == 0.0 {
        0.0
    } else {
        dot / denom
    }
}

/// Auto-generate an embedding for content if no explicit vector is provided.
/// Returns the vector to use (either the explicit one or the auto-generated one).
fn auto_embed(content: &str, vector: Option<&[f32]>) -> Option<Vec<f32>> {
    if vector.is_some() {
        return None; // caller already has a vector, use it directly
    }

    #[cfg(feature = "embeddings")]
    {
        Some(crate::embed::embed_text(content))
    }

    #[cfg(not(feature = "embeddings"))]
    {
        let _ = content;
        None
    }
}

/// Find a duplicate memory by cosine similarity against existing memories of the same type.
/// Returns the ID of the best match if similarity exceeds the threshold.
pub fn find_duplicate(
    conn: &rusqlite::Connection,
    content_vector: &[f32],
    type_filter: Option<&str>,
    threshold: f32,
) -> Result<Option<String>> {
    let (sql, has_param) = match type_filter {
        Some(_) => (
            "SELECT id, vector FROM memories WHERE json_extract(metadata, '$.type') = ?1 AND vector IS NOT NULL",
            true,
        ),
        None => (
            "SELECT id, vector FROM memories WHERE vector IS NOT NULL",
            false,
        ),
    };

    let mut stmt = conn.prepare(sql)?;
    let mut rows = if has_param {
        stmt.query(params![type_filter.unwrap()])?
    } else {
        stmt.query([])?
    };

    let mut best_id: Option<String> = None;
    let mut best_sim: f32 = threshold;

    while let Some(row) = rows.next()? {
        let id: String = row.get(0)?;
        let blob: Vec<u8> = row.get(1)?;
        let vec = blob_to_vec(&blob);
        let sim = cosine_similarity(content_vector, &vec);
        if sim > best_sim {
            best_sim = sim;
            best_id = Some(id);
        }
    }

    Ok(best_id)
}

pub fn insert(
    conn: &rusqlite::Connection,
    content: &str,
    vector: Option<&[f32]>,
    metadata: Option<Value>,
    dedup_threshold: Option<f32>,
) -> Result<InsertResult> {
    let id = uuid::Uuid::new_v4().to_string();
    let ts = now();

    // Auto-embed if no explicit vector
    let auto_vec = auto_embed(content, vector);
    let effective_vec = vector.or(auto_vec.as_deref());

    // Dedup check: if we have a vector and dedup is enabled, look for duplicates
    if let (Some(threshold), Some(vec)) = (dedup_threshold, effective_vec) {
        let type_filter = metadata
            .as_ref()
            .and_then(|m| m.get("type"))
            .and_then(|t| t.as_str());

        if let Some(dup_id) = find_duplicate(conn, vec, type_filter, threshold)? {
            // Update the existing memory instead of creating a new one
            update(conn, &dup_id, Some(content), Some(vec), metadata)?;
            return Ok(InsertResult::Deduplicated(dup_id));
        }
    }

    let vector_blob = effective_vec.map(vec_to_blob);
    let metadata_str = metadata.map(|m| m.to_string());

    conn.execute(
        "INSERT INTO memories (id, content, vector, metadata, created_at, updated_at)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
        params![id, content, vector_blob, metadata_str, ts, ts],
    )?;

    Ok(InsertResult::Created(id))
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
    // Auto-embed if no explicit vector
    let auto_vec = auto_embed(content, vector);
    let effective_vec = vector.or(auto_vec.as_deref());

    let vector_blob = effective_vec.map(vec_to_blob);
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
        "SELECT id, content, vector, metadata, created_at, updated_at, last_accessed, access_count
         FROM memories WHERE id = ?1",
    )?;

    let mut rows = stmt.query(params![id])?;
    match rows.next()? {
        Some(row) => {
            let mem = row_to_memory(row)?;
            // Touch on access
            let _ = touch(conn, id);
            Ok(Some(mem))
        }
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
    let existing = get_raw(conn, id)?;
    if existing.is_none() {
        return Err(MemoriError::NotFound(id.to_string()));
    }

    let ts = now();

    if let Some(content) = content {
        conn.execute(
            "UPDATE memories SET content = ?1, updated_at = ?2 WHERE id = ?3",
            params![content, ts, id],
        )?;

        // Re-embed if content changes and no explicit vector provided
        if vector.is_none() {
            let auto_vec = auto_embed(content, None);
            if let Some(v) = auto_vec {
                let blob = vec_to_blob(&v);
                conn.execute(
                    "UPDATE memories SET vector = ?1 WHERE id = ?2",
                    params![blob, id],
                )?;
            }
        }
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

/// Raw get without touching access count (avoids infinite recursion in update path)
fn get_raw(conn: &rusqlite::Connection, id: &str) -> Result<Option<Memory>> {
    let mut stmt = conn.prepare(
        "SELECT id, content, vector, metadata, created_at, updated_at, last_accessed, access_count
         FROM memories WHERE id = ?1",
    )?;

    let mut rows = stmt.query(params![id])?;
    match rows.next()? {
        Some(row) => Ok(Some(row_to_memory(row)?)),
        None => Ok(None),
    }
}

pub fn touch(conn: &rusqlite::Connection, id: &str) -> Result<()> {
    let ts = now();
    conn.execute(
        "UPDATE memories SET last_accessed = ?1, access_count = access_count + 1 WHERE id = ?2",
        params![ts, id],
    )?;
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

/// Return (embedded_count, total_count) for embedding coverage stats
pub fn embedding_stats(conn: &rusqlite::Connection) -> Result<(usize, usize)> {
    let total: i64 = conn.query_row("SELECT COUNT(*) FROM memories", [], |row| row.get(0))?;
    let embedded: i64 = conn.query_row(
        "SELECT COUNT(*) FROM memories WHERE vector IS NOT NULL",
        [],
        |row| row.get(0),
    )?;
    Ok((embedded as usize, total as usize))
}

/// Backfill embeddings for memories that have vector = NULL.
/// Returns the number of memories processed.
pub fn backfill_embeddings(conn: &rusqlite::Connection, batch_size: usize) -> Result<usize> {
    #[cfg(not(feature = "embeddings"))]
    {
        let _ = (conn, batch_size);
        return Ok(0);
    }

    #[cfg(feature = "embeddings")]
    {
        let mut total_processed = 0usize;

        loop {
            let mut stmt = conn.prepare(
                "SELECT id, content FROM memories WHERE vector IS NULL LIMIT ?1",
            )?;
            let mut rows = stmt.query(params![batch_size as i64])?;

            let mut batch: Vec<(String, String)> = Vec::new();
            while let Some(row) = rows.next()? {
                let id: String = row.get(0)?;
                let content: String = row.get(1)?;
                batch.push((id, content));
            }

            if batch.is_empty() {
                break;
            }

            let texts: Vec<&str> = batch.iter().map(|(_, c)| c.as_str()).collect();
            let embeddings = crate::embed::embed_batch(&texts);

            for ((id, _), embedding) in batch.iter().zip(embeddings.iter()) {
                let blob = vec_to_blob(embedding);
                conn.execute(
                    "UPDATE memories SET vector = ?1 WHERE id = ?2",
                    params![blob, id],
                )?;
            }

            total_processed += batch.len();
        }

        Ok(total_processed)
    }
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
        last_accessed: row.get(6)?,
        access_count: row.get(7)?,
        score: None,
    })
}
