pub mod embed;
pub mod schema;
pub mod search;
pub mod storage;
pub mod types;
pub mod util;

use std::collections::HashMap;

pub use types::{InsertResult, Memory, MemoriError, Result, SearchQuery, SortField};

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

    /// Resolve a short ID prefix to the full UUID.
    pub fn resolve_id(&self, id: &str) -> Result<String> {
        storage::resolve_prefix(&self.conn, id)
    }

    pub fn insert(
        &self,
        content: &str,
        vector: Option<&[f32]>,
        metadata: Option<serde_json::Value>,
        dedup_threshold: Option<f32>,
        no_embed: bool,
    ) -> Result<InsertResult> {
        storage::insert(&self.conn, content, vector, metadata, dedup_threshold, no_embed)
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
        // Resolve prefix; if not found, return None (backwards compat)
        let full_id = match storage::resolve_prefix(&self.conn, id) {
            Ok(fid) => fid,
            Err(MemoriError::NotFound(_)) => return Ok(None),
            Err(e) => return Err(e),
        };
        storage::get(&self.conn, &full_id)
    }

    pub fn update(
        &self,
        id: &str,
        content: Option<&str>,
        vector: Option<&[f32]>,
        metadata: Option<serde_json::Value>,
        merge_metadata: bool,
    ) -> Result<()> {
        let full_id = storage::resolve_prefix(&self.conn, id)?;
        storage::update(&self.conn, &full_id, content, vector, metadata, merge_metadata)
    }

    pub fn delete(&self, id: &str) -> Result<()> {
        let full_id = storage::resolve_prefix(&self.conn, id)?;
        storage::delete(&self.conn, &full_id)
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
        let full_id = storage::resolve_prefix(&self.conn, id)?;
        storage::touch(&self.conn, &full_id)
    }

    pub fn vacuum(&self) -> Result<()> {
        storage::vacuum(&self.conn)
    }

    pub fn set_access_stats(
        &self,
        id: &str,
        last_accessed: Option<f64>,
        access_count: i64,
    ) -> Result<()> {
        let full_id = storage::resolve_prefix(&self.conn, id)?;
        storage::set_access_stats(&self.conn, &full_id, last_accessed, access_count)
    }

    pub fn backfill_embeddings(&self, batch_size: usize) -> Result<usize> {
        storage::backfill_embeddings(&self.conn, batch_size)
    }

    pub fn list(
        &self,
        type_filter: Option<&str>,
        sort: &SortField,
        limit: usize,
        offset: usize,
        before: Option<f64>,
        after: Option<f64>,
    ) -> Result<Vec<Memory>> {
        storage::list(&self.conn, type_filter, sort, limit, offset, before, after)
    }

    pub fn embedding_stats(&self) -> Result<(usize, usize)> {
        storage::embedding_stats(&self.conn)
    }

    /// Get a memory by ID or prefix without bumping access_count.
    pub fn get_readonly(&self, id_or_prefix: &str) -> Result<Option<Memory>> {
        let full_id = match storage::resolve_prefix(&self.conn, id_or_prefix) {
            Ok(fid) => fid,
            Err(MemoriError::NotFound(_)) => return Ok(None),
            Err(e) => return Err(e),
        };
        storage::get_raw(&self.conn, &full_id)
    }

    pub fn related(&self, id: &str, limit: usize) -> Result<Vec<Memory>> {
        let full_id = storage::resolve_prefix(&self.conn, id)?;
        search::related(&self.conn, &full_id, limit)
    }
}
