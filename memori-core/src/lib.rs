pub mod embed;
pub mod schema;
pub mod search;
pub mod storage;
pub mod types;

use std::collections::HashMap;

pub use types::{InsertResult, Memory, MemoriError, Result, SearchQuery};

pub struct Memori {
    conn: rusqlite::Connection,
}

impl Memori {
    pub fn open(path: &str) -> Result<Self> {
        let conn = if path == ":memory:" {
            rusqlite::Connection::open_in_memory()?
        } else {
            rusqlite::Connection::open(path)?
        };
        schema::init_db(&conn)?;
        Ok(Self { conn })
    }

    pub fn insert(
        &self,
        content: &str,
        vector: Option<&[f32]>,
        metadata: Option<serde_json::Value>,
        dedup_threshold: Option<f32>,
    ) -> Result<InsertResult> {
        storage::insert(&self.conn, content, vector, metadata, dedup_threshold)
    }

    pub fn insert_with_id(
        &self,
        id: &str,
        content: &str,
        vector: Option<&[f32]>,
        metadata: Option<serde_json::Value>,
        created_at: f64,
        updated_at: f64,
    ) -> Result<String> {
        storage::insert_with_id(&self.conn, id, content, vector, metadata, created_at, updated_at)
    }

    pub fn get(&self, id: &str) -> Result<Option<Memory>> {
        storage::get(&self.conn, id)
    }

    pub fn update(
        &self,
        id: &str,
        content: Option<&str>,
        vector: Option<&[f32]>,
        metadata: Option<serde_json::Value>,
    ) -> Result<()> {
        storage::update(&self.conn, id, content, vector, metadata)
    }

    pub fn delete(&self, id: &str) -> Result<()> {
        storage::delete(&self.conn, id)
    }

    pub fn search(&self, query: SearchQuery) -> Result<Vec<Memory>> {
        search::search(&self.conn, query)
    }

    pub fn count(&self) -> Result<usize> {
        storage::count(&self.conn)
    }

    pub fn type_distribution(&self) -> Result<HashMap<String, usize>> {
        storage::type_distribution(&self.conn)
    }

    pub fn delete_before(&self, before_timestamp: f64) -> Result<usize> {
        storage::delete_before(&self.conn, before_timestamp)
    }

    pub fn delete_by_type(&self, type_value: &str) -> Result<usize> {
        storage::delete_by_type(&self.conn, type_value)
    }

    pub fn touch(&self, id: &str) -> Result<()> {
        storage::touch(&self.conn, id)
    }

    pub fn backfill_embeddings(&self, batch_size: usize) -> Result<usize> {
        storage::backfill_embeddings(&self.conn, batch_size)
    }

    pub fn embedding_stats(&self) -> Result<(usize, usize)> {
        storage::embedding_stats(&self.conn)
    }
}
