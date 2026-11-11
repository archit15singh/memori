use rusqlite::params;
use serde_json::Value;
use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};

use crate::storage::{get_raw, row_to_memory};
use crate::types::{LorevellError, Memory, Result, SearchQuery};
use crate::util::cosine_similarity;

const RRF_K: f32 = 60.0;

fn now_secs() -> f64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs_f64()
}

pub fn search(conn: &rusqlite::Connection, query: SearchQuery) -> Result<Vec<Memory>> {
    validate_min_similarity(query.min_similarity)?;
    if query.min_similarity.is_some()
        && (query.text_only
            || (query.vector.is_none() && (query.text.is_none() || !cfg!(feature = "embeddings"))))
    {
        return Err(LorevellError::InvalidSimilarity(
                "requires a vector query or text search with embeddings; not text_only or recent browsing".into(),
            ));
    }
    let now = now_secs();

    // Build combined filter: metadata filter AND date range filters
    let mut conditions = Vec::new();

    if let Some(ref filter) = query.filter {
        let meta_clause = build_filter_clause(filter)?;
        if !meta_clause.is_empty() && meta_clause != "1=1" {
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
        (Some(vec), Some(text)) => hybrid_search(
            conn,
            vec,
            text,
            combined_filter.as_deref(),
            query.limit,
            now,
            query.min_similarity,
        )?,
        (Some(vec), None) => vector_search(
            conn,
            vec,
            combined_filter.as_deref(),
            query.limit,
            now,
            query.min_similarity,
        )?,
        (None, Some(text)) => {
            #[cfg(feature = "embeddings")]
            {
                if query.text_only || query.limit == 0 || text.trim().is_empty() {
                    text_search(conn, text, combined_filter.as_deref(), query.limit, now)?
                } else {
                    let query_vec = crate::embed::embed_text(text);
                    hybrid_search(
                        conn,
                        &query_vec,
                        text,
                        combined_filter.as_deref(),
                        query.limit,
                        now,
                        query.min_similarity,
                    )?
                }
            }
            #[cfg(not(feature = "embeddings"))]
            {
                text_search(conn, text, combined_filter.as_deref(), query.limit, now)?
            }
        }
        (None, None) => recent_search(conn, combined_filter.as_deref(), query.limit)?,
    };

    Ok(results)
}

/// Bounded popularity plus factual age, independently of reads and tag changes.
fn apply_access_boost(base_score: f32, access_count: i64, freshness_at: f64, now: f64) -> f32 {
    let boost = 1.0 + (0.1 * (1.0 + access_count.max(0) as f32).ln()).min(0.5);
    let days_since = ((now - freshness_at) / 86400.0).max(0.0) as f32;
    let decay = (-0.01 * days_since).exp(); // half-life ~69 days
    let adjustment = boost * decay;
    if base_score >= 0.0 {
        base_score * adjustment
    } else {
        // Multiplying a negative cosine by decay would improve an old match.
        base_score / adjustment.max(f32::MIN_POSITIVE)
    }
}

fn vector_search(
    conn: &rusqlite::Connection,
    query_vec: &[f32],
    filter: Option<&str>,
    limit: usize,
    now: f64,
    min_similarity: Option<f32>,
) -> Result<Vec<Memory>> {
    if min_similarity.is_some() && checked_cosine(query_vec, query_vec).is_none() {
        return Err(LorevellError::InvalidVector(
            "similarity filtering requires a finite, nonzero query vector".into(),
        ));
    }
    let where_clause = filter.map_or(String::new(), |f| format!("WHERE {}", f));
    let sql = format!(
        "SELECT id, content, vector, metadata, created_at, updated_at, last_accessed, access_count, content_updated_at, validated_at
         FROM memories AS m {} ORDER BY rowid",
        where_clause
    );

    let mut stmt = conn.prepare(&sql)?;
    let mut scored: Vec<(Memory, f32)> = Vec::new();
    let mut rows = stmt.query([])?;

    while let Some(row) = rows.next()? {
        let mem = row_to_memory(row)?;
        if let Some(ref vec) = mem.vector {
            let sim = if let Some(threshold) = min_similarity {
                match checked_cosine(query_vec, vec) {
                    Some(sim) if sim >= threshold => sim,
                    _ => continue,
                }
            } else {
                cosine_similarity(query_vec, vec)
            };
            let boosted = apply_access_boost(sim, mem.access_count, mem.freshness_at(), now);
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
fn sanitize_fts_query(query: &str, separator: &str) -> String {
    query
        .split_whitespace()
        .map(|term| format!("\"{}\"", term.replace('"', "\"\"")))
        .collect::<Vec<_>>()
        .join(separator)
}

fn text_search(
    conn: &rusqlite::Connection,
    query_text: &str,
    filter: Option<&str>,
    limit: usize,
    now: f64,
) -> Result<Vec<Memory>> {
    let strict = text_search_terms(conn, query_text, filter, limit, now, false)?;
    if !strict.is_empty() || query_text.split_whitespace().count() < 2 {
        return Ok(strict);
    }
    text_search_terms(conn, query_text, filter, limit, now, true)
}

fn text_search_terms(
    conn: &rusqlite::Connection,
    query_text: &str,
    filter: Option<&str>,
    limit: usize,
    now: f64,
    any_term: bool,
) -> Result<Vec<Memory>> {
    let safe_query = sanitize_fts_query(query_text, if any_term { " OR " } else { " " });

    // Empty query (whitespace-only or blank input) produces no tokens -- return
    // early instead of passing an empty string to FTS5 MATCH which would error.
    if safe_query.is_empty() || limit == 0 {
        return Ok(Vec::new());
    }

    let sql = if let Some(f) = filter {
        format!(
            "SELECT m.id, m.content, m.vector, m.metadata, m.created_at, m.updated_at,
                    m.last_accessed, m.access_count, m.content_updated_at, m.validated_at, fts.rank
             FROM memories_fts fts
             JOIN memories m ON m.rowid = fts.rowid
             WHERE memories_fts MATCH ?1 AND {}
             ORDER BY fts.rank",
            f
        )
    } else {
        "SELECT m.id, m.content, m.vector, m.metadata, m.created_at, m.updated_at,
                m.last_accessed, m.access_count, m.content_updated_at, m.validated_at, fts.rank
         FROM memories_fts fts
         JOIN memories m ON m.rowid = fts.rowid
         WHERE memories_fts MATCH ?1
         ORDER BY fts.rank"
            .to_string()
    };

    let mut stmt = conn.prepare(&sql)?;
    let mut rows = stmt.query(params![safe_query])?;
    let mut results = Vec::new();

    while let Some(row) = rows.next()? {
        let rank: f64 = row.get(10)?;
        let mut memory = row_to_memory(row)?;
        memory.score = Some(apply_access_boost(
            -rank as f32,
            memory.access_count,
            memory.freshness_at(),
            now,
        ));
        results.push(memory);
    }
    // Age and popularity must affect membership before truncation, including FTS-only.
    results.sort_by(|a, b| {
        b.score
            .partial_cmp(&a.score)
            .unwrap_or(std::cmp::Ordering::Equal)
    });
    results.truncate(limit);

    Ok(results)
}

fn hybrid_search(
    conn: &rusqlite::Connection,
    query_vec: &[f32],
    query_text: &str,
    filter: Option<&str>,
    limit: usize,
    now: f64,
    min_similarity: Option<f32>,
) -> Result<Vec<Memory>> {
    // Get more candidates from each source for better fusion
    let candidate_limit = limit * 3;

    let vec_results = vector_search(
        conn,
        query_vec,
        filter,
        candidate_limit,
        now,
        min_similarity,
    )?;
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
            let text_rank = text_ranks
                .get(&m.id)
                .copied()
                .unwrap_or(candidate_limit + 1);
            let rrf = 1.0 / (RRF_K + vec_rank as f32) + 1.0 / (RRF_K + text_rank as f32);
            (m, rrf)
        })
        .collect();

    scored.sort_by(|a, b| {
        b.1.partial_cmp(&a.1)
            .unwrap_or(std::cmp::Ordering::Equal)
            .then_with(|| {
                vec_ranks
                    .get(&a.0.id)
                    .unwrap_or(&usize::MAX)
                    .cmp(vec_ranks.get(&b.0.id).unwrap_or(&usize::MAX))
            })
            .then_with(|| a.0.id.cmp(&b.0.id))
    });
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
        "SELECT id, content, vector, metadata, created_at, updated_at, last_accessed, access_count, content_updated_at, validated_at
         FROM memories AS m {} ORDER BY updated_at DESC LIMIT ?1",
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
    related_with_min_similarity(conn, id, limit, None)
}

pub fn related_with_min_similarity(
    conn: &rusqlite::Connection,
    id: &str,
    limit: usize,
    min_similarity: Option<f32>,
) -> Result<Vec<Memory>> {
    validate_min_similarity(min_similarity)?;
    let source = get_raw(conn, id)?.ok_or_else(|| LorevellError::NotFound(id.to_string()))?;

    let source_vec = source
        .vector
        .ok_or_else(|| LorevellError::InvalidVector("memory has no embedding".to_string()))?;

    let now = now_secs();
    let exclude_filter = format!("id != '{}'", id.replace('\'', "''"));
    vector_search(
        conn,
        &source_vec,
        Some(&exclude_filter),
        limit,
        now,
        min_similarity,
    )
}

fn validate_min_similarity(threshold: Option<f32>) -> Result<()> {
    if let Some(value) = threshold {
        if !value.is_finite() || !(-1.0..=1.0).contains(&value) {
            return Err(LorevellError::InvalidSimilarity(
                "must be finite and between -1 and 1".into(),
            ));
        }
    }
    Ok(())
}

// Invalid vectors must not become zero-similarity matches at a permissive floor.
// Accumulate in f64 to avoid overflow for finite f32 inputs and clamp rounding.
fn checked_cosine(a: &[f32], b: &[f32]) -> Option<f32> {
    if a.is_empty() || a.len() != b.len() {
        return None;
    }
    let (mut dot, mut norm_a, mut norm_b) = (0.0_f64, 0.0_f64, 0.0_f64);
    for (&x, &y) in a.iter().zip(b) {
        if !x.is_finite() || !y.is_finite() {
            return None;
        }
        let (x, y) = (f64::from(x), f64::from(y));
        dot += x * y;
        norm_a += x * x;
        norm_b += y * y;
    }
    if norm_a == 0.0 || norm_b == 0.0 {
        return None;
    }
    Some((dot / (norm_a.sqrt() * norm_b.sqrt())).clamp(-1.0, 1.0) as f32)
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
                    return Err(LorevellError::InvalidFilter(format!(
                        "key '{}' must match [a-zA-Z_][a-zA-Z0-9_]*",
                        key
                    )));
                }
                if val.is_null() {
                    conditions.push(format!("json_type(m.metadata, '$.{}') = 'null'", key));
                    continue;
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
                conditions.push(format!(
                    "json_extract(m.metadata, '$.{}') = {}",
                    key, json_val
                ));
            }
            Ok(conditions.join(" AND "))
        }
        _ => Ok("1=1".to_string()),
    }
}
