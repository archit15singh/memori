use rusqlite::params;
use serde_json::Value;
use std::collections::HashMap;

use crate::storage::row_to_memory;
use crate::types::{Memory, Result, SearchQuery};

const RRF_K: f32 = 60.0;

pub fn search(conn: &rusqlite::Connection, query: SearchQuery) -> Result<Vec<Memory>> {
    let filter_clause = query.filter.as_ref().map(|f| build_filter_clause(f));

    let results = match (&query.vector, &query.text) {
        (Some(vec), Some(text)) => {
            hybrid_search(conn, vec, text, filter_clause.as_deref(), query.limit)?
        }
        (Some(vec), None) => {
            vector_search(conn, vec, filter_clause.as_deref(), query.limit)?
        }
        (None, Some(text)) => {
            #[cfg(feature = "embeddings")]
            {
                if query.text_only {
                    text_search(conn, text, filter_clause.as_deref(), query.limit)?
                } else {
                    let query_vec = crate::embed::embed_text(text);
                    hybrid_search(conn, &query_vec, text, filter_clause.as_deref(), query.limit)?
                }
            }
            #[cfg(not(feature = "embeddings"))]
            {
                text_search(conn, text, filter_clause.as_deref(), query.limit)?
            }
        }
        (None, None) => {
            recent_search(conn, filter_clause.as_deref(), query.limit)?
        }
    };

    Ok(results)
}

fn apply_access_boost(base_score: f32, access_count: i64) -> f32 {
    let boost = 1.0 + 0.1 * (1.0 + access_count as f32).ln();
    base_score * boost
}

fn vector_search(
    conn: &rusqlite::Connection,
    query_vec: &[f32],
    filter: Option<&str>,
    limit: usize,
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
            let boosted = apply_access_boost(sim, mem.access_count);
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

        let base_score = -rank as f32;
        let boosted = apply_access_boost(base_score, access_count);

        let mem = Memory {
            id: row.get(0)?,
            content: row.get(1)?,
            vector: vector_blob.map(|b| blob_to_vec(&b)),
            metadata: metadata_str.and_then(|s| serde_json::from_str(&s).ok()),
            created_at: row.get(4)?,
            updated_at: row.get(5)?,
            last_accessed: row.get(6)?,
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
) -> Result<Vec<Memory>> {
    // Get more candidates from each source for better fusion
    let candidate_limit = limit * 3;

    let vec_results = vector_search(conn, query_vec, filter, candidate_limit)?;
    let text_results = text_search(conn, query_text, filter, candidate_limit)?;

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

fn build_filter_clause(filter: &Value) -> String {
    match filter {
        Value::Object(map) => {
            let conditions: Vec<String> = map
                .iter()
                .map(|(key, val)| {
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
                    format!("json_extract(metadata, '$.{}') = {}", key, json_val)
                })
                .collect();
            conditions.join(" AND ")
        }
        _ => "1=1".to_string(),
    }
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

fn blob_to_vec(b: &[u8]) -> Vec<f32> {
    assert!(b.len() % 4 == 0);
    let mut v = vec![0.0f32; b.len() / 4];
    unsafe {
        std::ptr::copy_nonoverlapping(b.as_ptr(), v.as_mut_ptr() as *mut u8, b.len());
    }
    v
}
