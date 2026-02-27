use rusqlite::params;
use serde_json::Value;
use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};

use crate::storage::{get_raw, row_to_memory};
use crate::types::{Memory, MemoriError, Result, SearchQuery};
use crate::util::{blob_to_vec, cosine_similarity};

const RRF_K: f32 = 60.0;

fn now_secs() -> f64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs_f64()
}

pub fn search(conn: &rusqlite::Connection, query: SearchQuery) -> Result<Vec<Memory>> {
    let now = now_secs();

    // Build combined filter: metadata filter AND date range filters
    let mut conditions = Vec::new();

    if let Some(ref filter) = query.filter {
        let meta_clause = build_filter_clause(filter)?;
        if meta_clause != "1=1" {
            conditions.push(meta_clause);
        }
    }
    if let Some(before) = query.before {
        conditions.push(format!("created_at < {}", before));
    }
    if let Some(after) = query.after {
        conditions.push(format!("created_at > {}", after));
    }

    let combined_filter = if conditions.is_empty() {
        None
    } else {
        Some(conditions.join(" AND "))
    };

    let results = match (&query.vector, &query.text) {
        (Some(vec), Some(text)) => {
            hybrid_search(conn, vec, text, combined_filter.as_deref(), query.limit, now)?
        }
        (Some(vec), None) => {
            vector_search(conn, vec, combined_filter.as_deref(), query.limit, now)?
        }
        (None, Some(text)) => {
            #[cfg(feature = "embeddings")]
            {
                if query.text_only {
                    text_search(conn, text, combined_filter.as_deref(), query.limit, now)?
                } else {
                    let query_vec = crate::embed::embed_text(text);
                    hybrid_search(conn, &query_vec, text, combined_filter.as_deref(), query.limit, now)?
                }
            }
            #[cfg(not(feature = "embeddings"))]
            {
                text_search(conn, text, combined_filter.as_deref(), query.limit, now)?
            }
        }
        (None, None) => {
            recent_search(conn, combined_filter.as_deref(), query.limit)?
        }
    };

    Ok(results)
}

/// Apply access frequency boost with recency decay.
/// - boost: logarithmic amplification of access count (monotonic but sublinear)
/// - decay: exponential time decay with ~69 day half-life
/// - access_count==0 guard: never-accessed memories get no decay penalty
fn apply_access_boost(base_score: f32, access_count: i64, last_accessed: f64, now: f64) -> f32 {
    let boost = 1.0 + 0.1 * (1.0 + access_count as f32).ln();
    let decay = if access_count == 0 || last_accessed <= 0.0 {
        1.0f32 // never accessed: no decay penalty
    } else {
        let days_since = ((now - last_accessed) / 86400.0) as f32;
        (-0.01 * days_since.max(0.0)).exp() // half-life ~69 days
    };
    base_score * boost * decay
}

fn vector_search(
    conn: &rusqlite::Connection,
    query_vec: &[f32],
    filter: Option<&str>,
    limit: usize,
    now: f64,
) -> Result<Vec<Memory>> {
    let where_clause = filter.map_or(String::new(), |f| format!("WHERE {}", f));
    let sql = format!(
        "SELECT id, content, vector, metadata, created_at, updated_at, last_accessed, access_count
         FROM memories {} ORDER BY rowid",
        where_clause
    );

    let mut stmt = conn.prepare(&sql)?;
    let mut scored: Vec<(Memory, f32)> = Vec::new();
    let mut rows = stmt.query([])?;

    while let Some(row) = rows.next()? {
        let mem = row_to_memory(row)?;
        if let Some(ref vec) = mem.vector {
            let sim = cosine_similarity(query_vec, vec);
            let boosted = apply_access_boost(sim, mem.access_count, mem.last_accessed, now);
            scored.push((mem, boosted));
        }
    }

    scored.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
    scored.truncate(limit);

    Ok(scored
        .into_iter()
        .map(|(mut m, s)| {
            m.score = Some(s);
            m
        })
        .collect())
}

/// Sanitize user input for FTS5 MATCH queries. FTS5 has its own query syntax
/// where `-` means NOT, `:` means column filter, `*` means prefix, etc.
/// Wrapping each token in double quotes forces literal matching.
fn sanitize_fts_query(query: &str) -> String {
    query
        .split_whitespace()
        .map(|term| format!("\"{}\"", term.replace('"', "\"\"")))
        .collect::<Vec<_>>()
        .join(" ")
}

fn text_search(
    conn: &rusqlite::Connection,
    query_text: &str,
    filter: Option<&str>,
    limit: usize,
    now: f64,
) -> Result<Vec<Memory>> {
    let safe_query = sanitize_fts_query(query_text);

    let sql = if let Some(f) = filter {
        format!(
            "SELECT m.id, m.content, m.vector, m.metadata, m.created_at, m.updated_at,
                    m.last_accessed, m.access_count, fts.rank
             FROM memories_fts fts
             JOIN memories m ON m.rowid = fts.rowid
             WHERE memories_fts MATCH ?1 AND {}
             ORDER BY fts.rank
             LIMIT ?2",
            f.replace("metadata", "m.metadata")
        )
    } else {
        "SELECT m.id, m.content, m.vector, m.metadata, m.created_at, m.updated_at,
                m.last_accessed, m.access_count, fts.rank
         FROM memories_fts fts
         JOIN memories m ON m.rowid = fts.rowid
         WHERE memories_fts MATCH ?1
         ORDER BY fts.rank
         LIMIT ?2"
            .to_string()
    };

    let mut stmt = conn.prepare(&sql)?;
    let mut rows = stmt.query(params![safe_query, limit as i64])?;
    let mut results = Vec::new();

    while let Some(row) = rows.next()? {
        let rank: f64 = row.get(8)?;
        let vector_blob: Option<Vec<u8>> = row.get(2)?;
        let metadata_str: Option<String> = row.get(3)?;
        let access_count: i64 = row.get(7)?;
        let last_accessed: f64 = row.get(6)?;

        let base_score = -rank as f32;
        let boosted = apply_access_boost(base_score, access_count, last_accessed, now);

        let mem = Memory {
            id: row.get(0)?,
            content: row.get(1)?,
            vector: vector_blob.map(|b| blob_to_vec(&b)),
            metadata: metadata_str.and_then(|s| serde_json::from_str(&s).ok()),
            created_at: row.get(4)?,
            updated_at: row.get(5)?,
            last_accessed,
            access_count,
            score: Some(boosted),
        };
        results.push(mem);
    }

    Ok(results)
}

fn hybrid_search(
    conn: &rusqlite::Connection,
    query_vec: &[f32],
    query_text: &str,
    filter: Option<&str>,
    limit: usize,
    now: f64,
) -> Result<Vec<Memory>> {
    // Get more candidates from each source for better fusion
    let candidate_limit = limit * 3;

    let vec_results = vector_search(conn, query_vec, filter, candidate_limit, now)?;
    let text_results = text_search(conn, query_text, filter, candidate_limit, now)?;

    // Build rank maps (1-indexed)
    let mut vec_ranks: HashMap<String, usize> = HashMap::new();
    for (i, m) in vec_results.iter().enumerate() {
        vec_ranks.insert(m.id.clone(), i + 1);
    }

    let mut text_ranks: HashMap<String, usize> = HashMap::new();
    for (i, m) in text_results.iter().enumerate() {
        text_ranks.insert(m.id.clone(), i + 1);
    }

    // Collect all unique candidates
    let mut all_memories: HashMap<String, Memory> = HashMap::new();
    for m in vec_results {
        all_memories.insert(m.id.clone(), m);
    }
    for m in text_results {
        all_memories.entry(m.id.clone()).or_insert(m);
    }

    // Compute RRF scores (access boost already applied in sub-searches)
    let mut scored: Vec<(Memory, f32)> = all_memories
        .into_values()
        .map(|m| {
            let vec_rank = vec_ranks.get(&m.id).copied().unwrap_or(candidate_limit + 1);
            let text_rank = text_ranks.get(&m.id).copied().unwrap_or(candidate_limit + 1);
            let rrf = 1.0 / (RRF_K + vec_rank as f32) + 1.0 / (RRF_K + text_rank as f32);
            (m, rrf)
        })
        .collect();

    scored.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
    scored.truncate(limit);

    Ok(scored
        .into_iter()
        .map(|(mut m, s)| {
            m.score = Some(s);
            m
        })
        .collect())
}

fn recent_search(
    conn: &rusqlite::Connection,
    filter: Option<&str>,
    limit: usize,
) -> Result<Vec<Memory>> {
    let where_clause = filter.map_or(String::new(), |f| format!("WHERE {}", f));
    let sql = format!(
        "SELECT id, content, vector, metadata, created_at, updated_at, last_accessed, access_count
         FROM memories {} ORDER BY updated_at DESC LIMIT ?1",
        where_clause
    );

    let mut stmt = conn.prepare(&sql)?;
    let mut rows = stmt.query(params![limit as i64])?;
    let mut results = Vec::new();

    while let Some(row) = rows.next()? {
        results.push(row_to_memory(row)?);
    }

    Ok(results)
}

/// Find memories similar to a given memory by its ID.
/// Uses the source memory's vector to run a vector search, excluding itself.
pub fn related(conn: &rusqlite::Connection, id: &str, limit: usize) -> Result<Vec<Memory>> {
    let source = get_raw(conn, id)?
        .ok_or_else(|| MemoriError::NotFound(id.to_string()))?;

    let source_vec = source.vector
        .ok_or_else(|| MemoriError::InvalidVector("memory has no embedding".to_string()))?;

    let now = now_secs();
    let exclude_filter = format!("id != '{}'", id.replace('\'', "''"));
    vector_search(conn, &source_vec, Some(&exclude_filter), limit, now)
}

/// Validate that a metadata filter key is a safe identifier.
/// Keys must match `[a-zA-Z_][a-zA-Z0-9_]*` to prevent SQL injection
/// through the json_extract path expression.
fn is_valid_filter_key(key: &str) -> bool {
    if key.is_empty() {
        return false;
    }
    let mut chars = key.chars();
    let first = chars.next().unwrap();
    if !first.is_ascii_alphabetic() && first != '_' {
        return false;
    }
    chars.all(|c| c.is_ascii_alphanumeric() || c == '_')
}

fn build_filter_clause(filter: &Value) -> Result<String> {
    match filter {
        Value::Object(map) => {
            let mut conditions = Vec::with_capacity(map.len());
            for (key, val) in map {
                if !is_valid_filter_key(key) {
                    return Err(MemoriError::InvalidFilter(format!(
                        "key '{}' must match [a-zA-Z_][a-zA-Z0-9_]*",
                        key
                    )));
                }
                let json_val = match val {
                    Value::String(s) => format!("'{}'", s.replace('\'', "''")),
                    Value::Number(n) => n.to_string(),
                    Value::Bool(b) => {
                        if *b {
                            "1".to_string()
                        } else {
                            "0".to_string()
                        }
                    }
                    _ => format!("'{}'", val.to_string().replace('\'', "''")),
                };
                conditions.push(format!("json_extract(metadata, '$.{}') = {}", key, json_val));
            }
            Ok(conditions.join(" AND "))
        }
        _ => Ok("1=1".to_string()),
    }
}
