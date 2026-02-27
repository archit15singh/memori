use serde::{Deserialize, Serialize};
use thiserror::Error;

#[derive(Error, Debug)]
pub enum MemoriError {
    #[error("database error: {0}")]
    Sqlite(#[from] rusqlite::Error),

    #[error("json error: {0}")]
    Json(#[from] serde_json::Error),

    #[error("invalid vector: {0}")]
    InvalidVector(String),

    #[error("not found: {0}")]
    NotFound(String),
}

pub type Result<T> = std::result::Result<T, MemoriError>;

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Memory {
    pub id: String,
    pub content: String,
    pub vector: Option<Vec<f32>>,
    pub metadata: Option<serde_json::Value>,
    pub created_at: f64,
    pub updated_at: f64,
    pub last_accessed: f64,
    pub access_count: i64,
    pub score: Option<f32>,
}

#[derive(Clone, Debug)]
pub struct SearchQuery {
    pub vector: Option<Vec<f32>>,
    pub text: Option<String>,
    pub filter: Option<serde_json::Value>,
    pub limit: usize,
    /// When true, skip auto-vectorization and use FTS5 only for text queries.
    pub text_only: bool,
}

impl Default for SearchQuery {
    fn default() -> Self {
        Self {
            vector: None,
            text: None,
            filter: None,
            limit: 10,
            text_only: false,
        }
    }
}

/// Result of an insert operation -- either a new memory was created or
/// an existing one was updated via deduplication.
#[derive(Clone, Debug)]
pub enum InsertResult {
    Created(String),
    Deduplicated(String),
}

impl InsertResult {
    pub fn id(&self) -> &str {
        match self {
            InsertResult::Created(id) | InsertResult::Deduplicated(id) => id,
        }
    }

    pub fn is_deduplicated(&self) -> bool {
        matches!(self, InsertResult::Deduplicated(_))
    }
}
