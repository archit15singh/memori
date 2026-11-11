//! Markdown is authoritative; SQLite stores only rebuildable retrieval data.
use std::collections::{BTreeMap, BTreeSet, HashSet};
use std::fs::{self, File, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::sync::OnceLock;
use std::time::{SystemTime, UNIX_EPOCH};

use fs2::FileExt;
use regex::Regex;
use rusqlite::{params, Transaction, TransactionBehavior};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};

use crate::{Lorevell, LorevellError, Result, SearchQuery};

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Note {
    pub id: String,
    pub path: String,
    pub content: String,
    pub metadata: Value,
    pub links: Vec<String>,
}

#[derive(Debug, Serialize)]
pub struct NoteView {
    pub note: Note,
    pub outgoing: Vec<Note>,
    pub backlinks: Vec<Note>,
    pub unresolved: Vec<String>,
}

#[derive(Debug, Default, Serialize)]
pub struct IndexReport {
    pub indexed: usize,
    pub unchanged: usize,
    pub removed: usize,
    pub links: usize,
    pub unresolved: Vec<String>,
}

#[derive(Debug, Serialize)]
pub struct VaultHit {
    pub note: Note,
    pub score: Option<f32>,
}

#[derive(Debug, Serialize)]
pub struct LinkedNote {
    pub note: Note,
    pub via: String,
}

#[derive(Debug, Serialize)]
pub struct VaultSearch {
    pub matches: Vec<VaultHit>,
    pub context: Vec<LinkedNote>,
}

pub struct Vault {
    root: PathBuf,
    index: Lorevell,
}

struct Source {
    note: Note,
    hash: String,
    modified: f64,
}

impl Vault {
    pub fn open(root: &Path) -> Result<Self> {
        fs::create_dir_all(root)?;
        let root = root.canonicalize()?;
        let cache = root.join(".lorevell");
        if cache
            .symlink_metadata()
            .is_ok_and(|m| m.file_type().is_symlink())
        {
            return Err(LorevellError::InvalidNote(
                ".lorevell must not be a symlink".into(),
            ));
        }
        fs::create_dir_all(&cache)?;
        let db_path = cache.join("index.sqlite");
        if db_path
            .symlink_metadata()
            .is_ok_and(|m| m.file_type().is_symlink())
        {
            return Err(LorevellError::InvalidNote(
                "index must not be a symlink".into(),
            ));
        }
        let index = Lorevell::open(&db_path.to_string_lossy())?;
        crate::schema::init_vault_index(&index.conn)?;
        Ok(Self { root, index })
    }

    pub fn root(&self) -> &Path {
        &self.root
    }

    /// Active Markdown notes, in source-path order; archives and symlinks stay excluded.
    pub fn notes(&self) -> Result<Vec<Note>> {
        Ok(self
            .sources()?
            .into_iter()
            .map(|source| source.note)
            .collect())
    }

    fn lock(&self) -> Result<File> {
        let path = self.root.join(".lorevell/vault.lock");
        if path
            .symlink_metadata()
            .is_ok_and(|m| m.file_type().is_symlink())
        {
            return Err(LorevellError::InvalidNote(
                "vault lock must not be a symlink".into(),
            ));
        }
        let file = OpenOptions::new()
            .create(true)
            .truncate(false)
            .read(true)
            .write(true)
            .open(path)?;
        file.try_lock_exclusive().map_err(|e| {
            if e.kind() == std::io::ErrorKind::WouldBlock {
                LorevellError::VaultBusy
            } else {
                e.into()
            }
        })?;
        Ok(file)
    }

    fn sources(&self) -> Result<Vec<Source>> {
        let mut paths = Vec::new();
        collect_markdown(&self.root, &self.root, &mut paths)?;
        paths.sort();
        let mut ids = HashSet::new();
        let mut sources = Vec::new();
        for path in paths {
            let raw = fs::read_to_string(&path)?;
            let relative = path
                .strip_prefix(&self.root)
                .unwrap()
                .to_string_lossy()
                .replace('\\', "/");
            let note = parse_note(&raw, &relative)?;
            if !ids.insert(note.id.clone()) {
                return Err(LorevellError::InvalidNote(format!(
                    "duplicate id '{}' at {}",
                    note.id, relative
                )));
            }
            let modified = fs::metadata(&path)?
                .modified()?
                .duration_since(UNIX_EPOCH)
                .unwrap_or_default()
                .as_secs_f64();
            sources.push(Source {
                note,
                hash: format!("{:x}", Sha256::digest(raw.as_bytes())),
                modified,
            });
        }
        Ok(sources)
    }

    /// Validate the complete file set before modifying any cached rows.
    pub fn index(&self, embeddings: bool) -> Result<IndexReport> {
        let _lock = self.lock()?;
        let sources = self.sources()?;
        let conn = &self.index.conn;
        let mut report = IndexReport::default();
        let mut cached = BTreeMap::new();
        {
            let mut stmt = conn.prepare("SELECT s.note_id, s.hash, s.path, m.vector IS NOT NULL FROM note_sources s JOIN memories m ON m.id=s.note_id")?;
            let rows = stmt.query_map([], |r| {
                Ok((
                    r.get::<_, String>(0)?,
                    (
                        r.get::<_, String>(1)?,
                        r.get::<_, String>(2)?,
                        r.get::<_, bool>(3)?,
                    ),
                ))
            })?;
            for row in rows {
                let (id, value) = row?;
                cached.insert(id, value);
            }
        }
        // Validation and hashing above still observe every file. When identity,
        // content, path and requested vectors match, derived links also match.
        if sources.len() == cached.len()
            && sources.iter().all(|source| {
                cached
                    .get(&source.note.id)
                    .is_some_and(|(hash, path, vector)| {
                        hash == &source.hash
                            && path == &source.note.path
                            && (!embeddings || *vector)
                    })
            })
        {
            report.unchanged = sources.len();
            let mut stmt = conn.prepare("SELECT s.path, l.target, l.target_id FROM note_links l JOIN note_sources s ON s.note_id=l.source_id ORDER BY s.path, l.target")?;
            let rows = stmt.query_map([], |r| {
                Ok((
                    r.get::<_, String>(0)?,
                    r.get::<_, String>(1)?,
                    r.get::<_, Option<String>>(2)?,
                ))
            })?;
            for row in rows {
                let (path, target, resolved) = row?;
                if resolved.is_some() {
                    report.links += 1;
                } else {
                    report
                        .unresolved
                        .push(format!("{}: [[{}]] is missing or ambiguous", path, target));
                }
            }
            return Ok(report);
        }
        let transaction = Transaction::new_unchecked(conn, TransactionBehavior::Immediate)?;
        for source in &sources {
            let note = &source.note;
            let unchanged = cached
                .get(&note.id)
                .is_some_and(|(hash, _, vector)| hash == &source.hash && (!embeddings || *vector));
            if unchanged {
                report.unchanged += 1;
            } else {
                // A changed file replaces its derived record, never another similar note.
                conn.execute("DELETE FROM memories WHERE id=?1", [&note.id])?;
                let created = note
                    .metadata
                    .get("created_at")
                    .and_then(Value::as_f64)
                    .unwrap_or(source.modified);
                let updated = note
                    .metadata
                    .get("updated_at")
                    .and_then(Value::as_f64)
                    .unwrap_or(source.modified);
                let vector: Option<Vec<f32>> = if embeddings {
                    #[cfg(feature = "embeddings")]
                    {
                        Some(crate::embed::embed_text(&note.content))
                    }
                    #[cfg(not(feature = "embeddings"))]
                    {
                        return Err(LorevellError::InvalidNote(
                            "embeddings are disabled in this build; use text-only indexing".into(),
                        ));
                    }
                } else {
                    None
                };
                conn.execute(
                    "INSERT INTO memories (id, content, vector, metadata, created_at, updated_at, content_updated_at) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?6)",
                    params![note.id, note.content, vector.as_deref().map(crate::util::vec_to_blob), note.metadata.to_string(), created, updated],
                )?;
                report.indexed += 1;
            }
            conn.execute("INSERT INTO note_sources(note_id, path, hash) VALUES(?1, ?2, ?3) ON CONFLICT(note_id) DO UPDATE SET path=excluded.path, hash=excluded.hash", params![note.id, note.path, source.hash])?;
            cached.remove(&note.id);
        }
        for id in cached.keys() {
            conn.execute("DELETE FROM memories WHERE id=?1", [id])?;
            conn.execute("DELETE FROM note_sources WHERE note_id=?1", [id])?;
            report.removed += 1;
        }
        conn.execute("DELETE FROM note_links", [])?;
        let notes: Vec<&Note> = sources.iter().map(|s| &s.note).collect();
        for note in &notes {
            for target in &note.links {
                let resolved = resolve_link(&notes, target);
                if let Some(id) = &resolved {
                    if id == &note.id {
                        continue;
                    }
                    report.links += 1;
                } else {
                    report.unresolved.push(format!(
                        "{}: [[{}]] is missing or ambiguous",
                        note.path, target
                    ));
                }
                conn.execute(
                    "INSERT INTO note_links(source_id, target, target_id) VALUES(?1, ?2, ?3)",
                    params![note.id, target, resolved],
                )?;
            }
        }
        transaction.commit()?;
        Ok(report)
    }

    pub fn add(&self, content: &str, metadata: Value) -> Result<Note> {
        let _lock = self.lock()?;
        if content.trim().is_empty() {
            return Err(LorevellError::InvalidNote(
                "content must not be empty".into(),
            ));
        }
        let mut meta = metadata
            .as_object()
            .cloned()
            .ok_or_else(|| LorevellError::InvalidNote("metadata must be an object".into()))?;
        let id = uuid::Uuid::new_v4().to_string();
        meta.insert("id".into(), json!(id));
        let now = now();
        meta.entry("created_at").or_insert(json!(now));
        meta.entry("updated_at").or_insert(json!(now));
        let path = format!("{}.md", id);
        let raw = serialize_note(content, &Value::Object(meta))?;
        let note = parse_note(&raw, &path)?;
        atomic_write(&self.root.join(path), raw.as_bytes())?;
        Ok(note)
    }

    /// A fresh operation-local view: never retain parsed files across requests.
    fn note_map(&self) -> Result<BTreeMap<String, Note>> {
        Ok(self
            .notes()?
            .into_iter()
            .map(|note| (note.id.clone(), note))
            .collect())
    }

    /// Read from Markdown, so a stale or deleted cache never changes the source.
    pub fn get(&self, id: &str) -> Result<Note> {
        if id.trim().is_empty() {
            return Err(LorevellError::InvalidNote("id must not be empty".into()));
        }
        Ok(find_note(&self.note_map()?, id)?.clone())
    }

    pub fn update(&self, id: &str, content: Option<&str>, metadata: Option<Value>) -> Result<Note> {
        let _lock = self.lock()?;
        let note = self.get(id)?;
        let content = content.unwrap_or(&note.content);
        if content.trim().is_empty() {
            return Err(LorevellError::InvalidNote(
                "content must not be empty".into(),
            ));
        }
        let mut meta = note.metadata.as_object().cloned().unwrap();
        if let Some(value) = metadata {
            let object = value
                .as_object()
                .ok_or_else(|| LorevellError::InvalidNote("metadata must be an object".into()))?;
            if object
                .get("id")
                .is_some_and(|value| value != &json!(note.id))
            {
                return Err(LorevellError::InvalidNote(
                    "update cannot change the stable id".into(),
                ));
            }
            meta.extend(object.clone());
        }
        meta.insert("updated_at".into(), json!(now()));
        let raw = serialize_note(content, &Value::Object(meta))?;
        let updated = parse_note(&raw, &note.path)?;
        atomic_write(&self.root.join(&note.path), raw.as_bytes())?;
        Ok(updated)
    }

    /// Preserve the entire original note rather than silently discarding evidence.
    pub fn archive(&self, id: &str) -> Result<PathBuf> {
        let _lock = self.lock()?;
        let note = self.get(id)?;
        let dir = self.root.join("archive");
        if dir
            .symlink_metadata()
            .is_ok_and(|m| m.file_type().is_symlink())
        {
            return Err(LorevellError::InvalidNote(
                "archive must not be a symlink".into(),
            ));
        }
        fs::create_dir_all(&dir)?;
        let target = dir.join(format!("{}.md", note.id));
        if target.exists() {
            return Err(LorevellError::InvalidNote(format!(
                "archive already contains {}",
                note.id
            )));
        }
        fs::rename(self.root.join(note.path), &target)?;
        Ok(target)
    }

    pub fn show(&self, id: &str, neighbor_limit: usize) -> Result<NoteView> {
        if id.trim().is_empty() {
            return Err(LorevellError::InvalidNote("id must not be empty".into()));
        }
        let notes = self.note_map()?;
        let note = find_note(&notes, id)?;
        self.show_from(note, neighbor_limit, &notes)
    }

    fn show_from(
        &self,
        note: &Note,
        neighbor_limit: usize,
        notes: &BTreeMap<String, Note>,
    ) -> Result<NoteView> {
        let mut outgoing = Vec::new();
        let mut backlinks = Vec::new();
        let mut unresolved = Vec::new();
        let mut stmt = self.index.conn.prepare("SELECT source_id, target, target_id FROM note_links WHERE source_id=?1 OR target_id=?1 ORDER BY source_id, target")?;
        let rows = stmt.query_map([&note.id], |r| {
            Ok((
                r.get::<_, String>(0)?,
                r.get::<_, String>(1)?,
                r.get::<_, Option<String>>(2)?,
            ))
        })?;
        let mut seen_out = HashSet::new();
        let mut seen_back = HashSet::new();
        for row in rows {
            let (source, target, resolved) = row?;
            if source == note.id {
                if let Some(target_id) = resolved {
                    if outgoing.len() < neighbor_limit && seen_out.insert(target_id.clone()) {
                        outgoing.push(find_note(notes, &target_id)?.clone());
                    }
                } else {
                    unresolved.push(target);
                }
            } else if backlinks.len() < neighbor_limit && seen_back.insert(source.clone()) {
                backlinks.push(find_note(notes, &source)?.clone());
            }
        }
        Ok(NoteView {
            note: note.clone(),
            outgoing,
            backlinks,
            unresolved,
        })
    }

    pub fn search(&self, query: SearchQuery, graph_limit: usize) -> Result<VaultSearch> {
        let filter = query.filter.clone();
        let mut matches = Vec::new();
        let mut context = Vec::new();
        let mut seen = HashSet::new();
        let memories = self.index.search(query)?;
        if memories.is_empty() {
            return Ok(VaultSearch { matches, context });
        }
        let notes = self.note_map()?;
        for memory in memories {
            seen.insert(memory.id.clone());
            matches.push(VaultHit {
                note: find_note(&notes, &memory.id)?.clone(),
                score: memory.score,
            });
        }
        if graph_limit > 0 {
            for hit in &matches {
                let view = self.show_from(&hit.note, graph_limit, &notes)?;
                for note in view.outgoing.into_iter().chain(view.backlinks) {
                    let eligible = filter
                        .as_ref()
                        .and_then(Value::as_object)
                        .is_none_or(|f| f.iter().all(|(k, v)| note.metadata.get(k) == Some(v)));
                    if context.len() < graph_limit && eligible && seen.insert(note.id.clone()) {
                        context.push(LinkedNote {
                            note,
                            via: hit.note.id.clone(),
                        });
                    }
                }
            }
        }
        Ok(VaultSearch { matches, context })
    }
}

fn find_note<'a>(notes: &'a BTreeMap<String, Note>, id: &str) -> Result<&'a Note> {
    if id.trim().is_empty() {
        return Err(LorevellError::InvalidNote("id must not be empty".into()));
    }
    if let Some(note) = notes.get(id) {
        return Ok(note);
    }
    if let Some(note) = notes
        .values()
        .find(|note| note.path.trim_end_matches(".md") == id)
    {
        return Ok(note);
    }
    let found: Vec<_> = notes
        .values()
        .filter(|note| note.id.starts_with(id))
        .collect();
    match found.as_slice() {
        [note] => Ok(note),
        [] => Err(LorevellError::NotFound(id.into())),
        _ => Err(LorevellError::AmbiguousPrefix(id.into(), found.len())),
    }
}

fn collect_markdown(root: &Path, dir: &Path, paths: &mut Vec<PathBuf>) -> Result<()> {
    for entry in fs::read_dir(dir)? {
        let entry = entry?;
        let kind = entry.file_type()?;
        let path = entry.path();
        let name = entry.file_name();
        let name = name.to_string_lossy();
        // Symlinks never extend the vault's read/write scope.
        if kind.is_symlink() || name.starts_with('.') || (dir == root && name == "archive") {
            continue;
        }
        if kind.is_dir() {
            collect_markdown(root, &path, paths)?;
        } else if kind.is_file() && path.extension().is_some_and(|x| x == "md") {
            paths.push(path);
        }
    }
    Ok(())
}

fn parse_note(raw: &str, path: &str) -> Result<Note> {
    let normalized = raw.replace("\r\n", "\n");
    let rest = normalized
        .strip_prefix("---\n")
        .ok_or_else(|| LorevellError::InvalidNote(format!("{}: missing YAML frontmatter", path)))?;
    let (header, body) = rest.split_once("\n---\n").ok_or_else(|| {
        LorevellError::InvalidNote(format!("{}: unclosed YAML frontmatter", path))
    })?;
    let metadata: Value = serde_yaml_ng::from_str(header)
        .map_err(|e| LorevellError::InvalidNote(format!("{}: {}", path, e)))?;
    let object = metadata.as_object().ok_or_else(|| {
        LorevellError::InvalidNote(format!("{}: frontmatter must be a mapping", path))
    })?;
    let id = object
        .get("id")
        .and_then(Value::as_str)
        .filter(|id| {
            !id.is_empty()
                && id.len() <= 128
                && id
                    .bytes()
                    .all(|b| b.is_ascii_alphanumeric() || b == b'-' || b == b'_')
        })
        .ok_or_else(|| {
            LorevellError::InvalidNote(format!(
                "{}: id must be a string containing letters, digits, '-' or '_'",
                path
            ))
        })?
        .to_string();
    if object.get("type").is_some_and(|t| !t.is_string()) {
        return Err(LorevellError::InvalidNote(format!(
            "{}: type must be a string",
            path
        )));
    }
    if object
        .get("tags")
        .is_some_and(|t| !t.as_array().is_some_and(|a| a.iter().all(Value::is_string)))
    {
        return Err(LorevellError::InvalidNote(format!(
            "{}: tags must be a list of strings",
            path
        )));
    }
    for key in ["created_at", "updated_at"] {
        if object
            .get(key)
            .is_some_and(|v| !v.as_f64().is_some_and(f64::is_finite))
        {
            return Err(LorevellError::InvalidNote(format!(
                "{}: {} must be finite epoch seconds",
                path, key
            )));
        }
    }
    if body.trim().is_empty() {
        return Err(LorevellError::InvalidNote(format!(
            "{}: empty Markdown body",
            path
        )));
    }
    let body = body.strip_prefix('\n').unwrap_or(body);
    let links = wiki_links(body);
    Ok(Note {
        id,
        path: path.into(),
        content: body.trim_end().into(),
        metadata,
        links,
    })
}

fn wiki_links(body: &str) -> Vec<String> {
    static WIKI_LINKS: OnceLock<Regex> = OnceLock::new();
    let regex = WIKI_LINKS.get_or_init(|| Regex::new(r"\[\[([^\[\]\n]+)\]\]").unwrap());
    let mut fence: Option<char> = None;
    let mut links = BTreeSet::new();
    for line in body.lines() {
        let trimmed = line.trim_start();
        if trimmed.starts_with("```") || trimmed.starts_with("~~~") {
            let marker = trimmed.chars().next().unwrap();
            if fence == Some(marker) {
                fence = None;
            } else if fence.is_none() {
                fence = Some(marker);
            }
            continue;
        }
        if fence.is_some() {
            continue;
        }
        // Wiki syntax inside inline code is documentation, not a relationship.
        let mut code = false;
        let mut text = String::new();
        for piece in line.split('`') {
            if !code {
                text.push_str(piece);
                text.push(' ');
            }
            code = !code;
        }
        for capture in regex.captures_iter(&text) {
            let target = capture[1].split(['|', '#']).next().unwrap().trim();
            if !target.is_empty() {
                links.insert(target.trim_end_matches(".md").into());
            }
        }
    }
    links.into_iter().collect()
}

fn resolve_link(notes: &[&Note], target: &str) -> Option<String> {
    // Stable ID wins. Then an exact vault-relative path, then a unique basename.
    if let Some(note) = notes.iter().find(|n| n.id == target) {
        return Some(note.id.clone());
    }
    if let Some(note) = notes
        .iter()
        .find(|n| n.path.trim_end_matches(".md") == target)
    {
        return Some(note.id.clone());
    }
    let matches: Vec<_> = notes
        .iter()
        .filter(|n| Path::new(&n.path).file_stem().is_some_and(|s| s == target))
        .collect();
    match matches.as_slice() {
        [note] => Some(note.id.clone()),
        _ => None,
    }
}

fn serialize_note(content: &str, metadata: &Value) -> Result<String> {
    let yaml = serde_yaml_ng::to_string(metadata)
        .map_err(|e| LorevellError::InvalidNote(e.to_string()))?;
    Ok(format!("---\n{}---\n\n{}\n", yaml, content.trim_end()))
}

fn atomic_write(path: &Path, bytes: &[u8]) -> Result<()> {
    let temp = path.with_extension(format!("{}.tmp", uuid::Uuid::new_v4()));
    let result = (|| -> std::io::Result<()> {
        let mut file = OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(&temp)?;
        file.write_all(bytes)?;
        file.sync_all()?;
        fs::rename(&temp, path)?;
        Ok(())
    })();
    if result.is_err() {
        let _ = fs::remove_file(&temp);
    }
    result.map_err(Into::into)
}

fn now() -> f64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs_f64()
}
