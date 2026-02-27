use rusqlite::params;
use serde_json::Value;
use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};

use crate::types::{InsertResult, Memory, MemoriError, Result, SortField};
use crate::util::{blob_to_vec, cosine_similarity, vec_to_blob};

fn now() -> f64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs_f64()
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
    no_embed: bool,
) -> Result<InsertResult> {
    let id = uuid::Uuid::new_v4().to_string();
    let ts = now();

    // Auto-embed if no explicit vector and not suppressed
    let auto_vec = if no_embed {
        None
    } else {
        auto_embed(content, vector)
    };
    let effective_vec = vector.or(auto_vec.as_deref());

    // Dedup check: if we have a vector and dedup is enabled, look for duplicates
    if let (Some(threshold), Some(vec)) = (dedup_threshold, effective_vec) {
        let type_filter = metadata
            .as_ref()
            .and_then(|m| m.get("type"))
            .and_then(|t| t.as_str());

        if let Some(dup_id) = find_duplicate(conn, vec, type_filter, threshold)? {
            // Update the existing memory instead of creating a new one
            update(conn, &dup_id, Some(content), Some(vec), metadata, false)?;
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

/// Deep-merge two JSON values. For objects, recursively merge keys.
/// For other types, `overlay` replaces `base`.
fn merge_json(base: &Value, overlay: &Value) -> Value {
    match (base, overlay) {
        (Value::Object(base_map), Value::Object(overlay_map)) => {
            let mut merged = base_map.clone();
            for (key, val) in overlay_map {
                let merged_val = match merged.get(key) {
                    Some(existing) => merge_json(existing, val),
                    None => val.clone(),
                };
                merged.insert(key.clone(), merged_val);
            }
            Value::Object(merged)
        }
        _ => overlay.clone(),
    }
}

/// Extract metadata values as a space-joined string for embedding.
/// Only values are included (no JSON syntax or keys) to produce
/// a natural-language-like string for the embedding model.
fn metadata_values_text(metadata: &Value) -> String {
    match metadata {
        Value::Object(map) => map
            .values()
            .filter_map(|v| match v {
                Value::String(s) => Some(s.clone()),
                Value::Number(n) => Some(n.to_string()),
                Value::Bool(b) => Some(b.to_string()),
                _ => None,
            })
            .collect::<Vec<_>>()
            .join(" "),
        _ => String::new(),
    }
}

pub fn update(
    conn: &rusqlite::Connection,
    id: &str,
    content: Option<&str>,
    vector: Option<&[f32]>,
    metadata: Option<Value>,
    merge_metadata: bool,
) -> Result<()> {
    let existing = get_raw(conn, id)?;
    let existing = existing.ok_or_else(|| MemoriError::NotFound(id.to_string()))?;

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

    if let Some(new_meta) = metadata {
        let final_meta = if merge_metadata {
            match &existing.metadata {
                Some(existing_meta) => merge_json(existing_meta, &new_meta),
                None => new_meta,
            }
        } else {
            new_meta
        };

        let json_str = final_meta.to_string();
        conn.execute(
            "UPDATE memories SET metadata = ?1, updated_at = ?2 WHERE id = ?3",
            params![json_str, ts, id],
        )?;

        // Re-embed when metadata changes so vector search finds tagged content.
        // FTS5 triggers already handle text search via the update trigger, but
        // the vector embedding needs explicit regeneration.
        if vector.is_none() {
            // Use current content (possibly just updated above)
            let current_content = content.map(|s| s.to_string()).unwrap_or(existing.content);
            let meta_text = metadata_values_text(&final_meta);
            let embed_text = if meta_text.is_empty() {
                current_content
            } else {
                format!("{} {}", current_content, meta_text)
            };
            let auto_vec = auto_embed(&embed_text, None);
            if let Some(v) = auto_vec {
                let blob = vec_to_blob(&v);
                conn.execute(
                    "UPDATE memories SET vector = ?1 WHERE id = ?2",
                    params![blob, id],
                )?;
            }
        }
    }

    Ok(())
}

/// Raw get without touching access count (avoids infinite recursion in update path)
pub(crate) fn get_raw(conn: &rusqlite::Connection, id: &str) -> Result<Option<Memory>> {
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

pub fn list(
    conn: &rusqlite::Connection,
    type_filter: Option<&str>,
    sort: &SortField,
    limit: usize,
    offset: usize,
    before: Option<f64>,
    after: Option<f64>,
) -> Result<Vec<Memory>> {
    // Build WHERE conditions dynamically
    let mut conditions: Vec<String> = Vec::new();
    let mut param_values: Vec<Box<dyn rusqlite::types::ToSql>> = Vec::new();

    if let Some(tf) = type_filter {
        param_values.push(Box::new(tf.to_string()));
        conditions.push(format!("json_extract(metadata, '$.type') = ?{}", param_values.len()));
    }
    if let Some(b) = before {
        conditions.push(format!("created_at < {}", b));
    }
    if let Some(a) = after {
        conditions.push(format!("created_at > {}", a));
    }

    let where_clause = if conditions.is_empty() {
        String::new()
    } else {
        format!("WHERE {}", conditions.join(" AND "))
    };

    // Limit and offset are the next positional params
    let limit_idx = param_values.len() + 1;
    let offset_idx = param_values.len() + 2;
    param_values.push(Box::new(limit as i64));
    param_values.push(Box::new(offset as i64));

    let sql = format!(
        "SELECT id, content, vector, metadata, created_at, updated_at, last_accessed, access_count
         FROM memories {} ORDER BY {} DESC LIMIT ?{} OFFSET ?{}",
        where_clause, sort.sql_column(), limit_idx, offset_idx
    );

    let mut stmt = conn.prepare(&sql)?;
    let param_refs: Vec<&dyn rusqlite::types::ToSql> = param_values.iter().map(|p| p.as_ref()).collect();
    let mut rows = stmt.query(param_refs.as_slice())?;

    let mut results = Vec::new();
    while let Some(row) = rows.next()? {
        results.push(row_to_memory(row)?);
    }
    Ok(results)
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

/// Run SQLite VACUUM to compact the database file.
pub fn vacuum(conn: &rusqlite::Connection) -> Result<()> {
    conn.execute_batch("VACUUM")?;
    Ok(())
}

/// Set access stats (last_accessed, access_count) for a memory by ID.
/// Used to restore access stats during import.
pub fn set_access_stats(
    conn: &rusqlite::Connection,
    id: &str,
    last_accessed: Option<f64>,
    access_count: i64,
) -> Result<()> {
    let affected = conn.execute(
        "UPDATE memories SET last_accessed = ?1, access_count = ?2 WHERE id = ?3",
        params![last_accessed, access_count, id],
    )?;
    if affected == 0 {
        return Err(MemoriError::NotFound(id.to_string()));
    }
    Ok(())
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

/// Resolve a short ID prefix to the full 36-char UUID.
/// If the prefix is already 36+ chars, returns it as-is (full UUID passthrough).
/// Returns NotFound if no match, AmbiguousPrefix if 2+ matches.
pub fn resolve_prefix(conn: &rusqlite::Connection, prefix: &str) -> Result<String> {
    if prefix.len() >= 36 {
        return Ok(prefix.to_string());
    }

    let mut stmt = conn.prepare("SELECT id FROM memories WHERE id LIKE ?1 || '%' LIMIT 2")?;
    let mut rows = stmt.query(params![prefix])?;

    let first = match rows.next()? {
        Some(row) => {
            let id: String = row.get(0)?;
            id
        }
        None => return Err(MemoriError::NotFound(prefix.to_string())),
    };

    // Check if there's a second match
    if rows.next()?.is_some() {
        // Count total matches for the error message
        let count: i64 = conn.query_row(
            "SELECT COUNT(*) FROM memories WHERE id LIKE ?1 || '%'",
            params![prefix],
            |row| row.get(0),
        )?;
        return Err(MemoriError::AmbiguousPrefix(
            prefix.to_string(),
            count as usize,
        ));
    }

    Ok(first)
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
