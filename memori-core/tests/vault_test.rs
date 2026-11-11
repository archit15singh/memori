use memori_core::{SearchQuery, Vault};
use serde_json::json;
use std::fs;
use std::path::PathBuf;

struct Temp(PathBuf);
impl Temp {
    fn new() -> Self {
        let path = std::env::temp_dir().join(format!("memori-vault-test-{}", uuid::Uuid::new_v4()));
        fs::create_dir(&path).unwrap();
        Self(path)
    }
    fn note(&self, path: &str, id: &str, body: &str) {
        let target = self.0.join(path);
        fs::create_dir_all(target.parent().unwrap()).unwrap();
        fs::write(
            target,
            format!("---\nid: {id}\ntype: procedure\ntags: [testing]\n---\n\n{body}\n"),
        )
        .unwrap();
    }
    fn vault(&self) -> Vault {
        Vault::open(&self.0).unwrap()
    }
}
impl Drop for Temp {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}
fn query(text: &str) -> SearchQuery {
    SearchQuery {
        text: Some(text.into()),
        text_only: true,
        ..Default::default()
    }
}

#[test]
fn manual_edits_renames_removals_and_cache_loss_rebuild_from_markdown() {
    let t = Temp::new();
    t.note("first.md", "first", "# Diagnose\nUse canary tests.");
    let v = t.vault();
    assert_eq!(v.index(false).unwrap().indexed, 1);
    assert_eq!(v.index(false).unwrap().unchanged, 1);
    assert_eq!(
        v.search(query("canary"), 0).unwrap().matches[0].note.id,
        "first"
    );
    t.note("first.md", "first", "# Diagnose\nUse bisect commands.");
    assert_eq!(v.index(false).unwrap().indexed, 1);
    assert!(v.search(query("canary"), 0).unwrap().matches.is_empty());
    assert_eq!(v.search(query("bisect"), 0).unwrap().matches.len(), 1);
    fs::rename(t.0.join("first.md"), t.0.join("renamed.md")).unwrap();
    assert_eq!(v.index(false).unwrap().unchanged, 1);
    assert_eq!(v.get("first").unwrap().path, "renamed.md");
    drop(v);
    fs::remove_file(t.0.join(".memori/index.sqlite")).unwrap();
    let v = t.vault();
    assert_eq!(v.index(false).unwrap().indexed, 1);
    assert_eq!(v.search(query("bisect"), 0).unwrap().matches.len(), 1);
    fs::remove_file(t.0.join("renamed.md")).unwrap();
    assert_eq!(v.index(false).unwrap().removed, 1);
    assert!(v.search(query("bisect"), 0).unwrap().matches.is_empty());
}

#[test]
fn duplicate_or_malformed_notes_leave_previous_index_unchanged() {
    let t = Temp::new();
    t.note("a.md", "a", "retained evidence");
    let v = t.vault();
    v.index(false).unwrap();
    t.note("b.md", "a", "duplicate identity");
    assert!(v
        .index(false)
        .unwrap_err()
        .to_string()
        .contains("duplicate id"));
    // Query underlying row counts without reading invalid files through search.
    let conn = rusqlite::Connection::open(t.0.join(".memori/index.sqlite")).unwrap();
    let content: String = conn
        .query_row("SELECT content FROM memories", [], |r| r.get(0))
        .unwrap();
    assert_eq!(content, "retained evidence");
    fs::write(t.0.join("b.md"), "not a note").unwrap();
    assert!(v
        .index(false)
        .unwrap_err()
        .to_string()
        .contains("frontmatter"));
    assert_eq!(
        conn.query_row("SELECT count(*) FROM memories", [], |r| r.get::<_, i64>(0))
            .unwrap(),
        1
    );
}

#[test]
fn stable_links_backlinks_cycles_aliases_and_bounded_one_hop() {
    let t = Temp::new();
    t.note("a.md","alpha","quasar [[beta|Procedure]] [[c#details]] [[missing]]\n`[[ignored]]`\n```md\n[[ignored-too]]\n```");
    t.note("b.md", "beta", "linked procedure [[alpha]] [[delta]]");
    t.note("c.md", "gamma", "other context");
    t.note("d.md", "delta", "second hop only");
    let v = t.vault();
    let report = v.index(false).unwrap();
    assert_eq!(report.links, 4);
    assert_eq!(report.unresolved.len(), 1);
    let view = v.show("alpha", 10).unwrap();
    assert_eq!(view.outgoing.len(), 2);
    assert_eq!(view.backlinks.len(), 1);
    assert_eq!(view.unresolved, vec!["missing"]);
    let hits = v.search(query("quasar"), 1).unwrap();
    assert_eq!(hits.matches.len(), 1);
    assert_eq!(hits.context.len(), 1);
    assert_eq!(hits.context[0].via, "alpha");
    assert_ne!(hits.context[0].note.id, "delta");
    assert!(v.search(query("quasar"), 0).unwrap().context.is_empty());
}

#[test]
fn basename_ambiguity_is_diagnostic_and_ids_survive_renames() {
    let t = Temp::new();
    t.note("source.md", "source", "[[same]] [[one/same]] [[id-two]]");
    t.note("one/same.md", "id-one", "one");
    t.note("two/same.md", "id-two", "two");
    let v = t.vault();
    let report = v.index(false).unwrap();
    assert_eq!(report.unresolved.len(), 1);
    assert_eq!(v.show("source", 10).unwrap().outgoing.len(), 2);
    fs::rename(t.0.join("two/same.md"), t.0.join("two/renamed.md")).unwrap();
    v.index(false).unwrap();
    assert_eq!(v.show("source", 10).unwrap().outgoing.len(), 2);
}

#[test]
fn mutations_persist_notes_metadata_and_original_archive_evidence() {
    let t = Temp::new();
    let v = t.vault();
    let first = v
        .add(
            "# Lesson\nUse transaction boundaries.",
            json!({"type":"procedure","tags":["sqlite"]}),
        )
        .unwrap();
    let second = v.add(&first.content, json!({"type":"procedure"})).unwrap();
    assert_ne!(first.id, second.id); // Intelligence, not a cosine cutoff, decides identity.
    let edited = v
        .update(
            &first.id[..12],
            Some("# Corrected\nUse immediate transactions."),
            Some(json!({"verified":true})),
        )
        .unwrap();
    assert_eq!(edited.metadata["tags"], json!(["sqlite"]));
    assert!(v
        .update(&first.id, None, Some(json!({"id":"different"})))
        .is_err());
    v.index(false).unwrap();
    let original = fs::read(t.0.join(&edited.path)).unwrap();
    let archived = v.archive(&first.id).unwrap();
    assert_eq!(fs::read(archived).unwrap(), original);
    assert!(v.get(&first.id).is_err());
    assert_eq!(v.index(false).unwrap().removed, 1);
    assert!(v.search(query("immediate"), 0).unwrap().matches.is_empty());
}

#[test]
fn invalid_metadata_and_empty_content_never_create_or_replace_notes() {
    let t = Temp::new();
    let v = t.vault();
    assert!(v.add("", json!({})).is_err());
    assert!(v.add("body", json!({"tags":"not-list"})).is_err());
    let note = v.add("original", json!({})).unwrap();
    let bytes = fs::read(t.0.join(&note.path)).unwrap();
    assert!(v.update(&note.id, Some(""), None).is_err());
    assert_eq!(fs::read(t.0.join(&note.path)).unwrap(), bytes);
}

#[test]
fn graph_expansion_respects_metadata_filter() {
    let t = Temp::new();
    t.note("a.md", "a", "needle [[b]]");
    fs::write(t.0.join("b.md"), "---\nid: b\ntype: fact\n---\nneighbor").unwrap();
    let v = t.vault();
    v.index(false).unwrap();
    let mut q = query("needle");
    q.filter = Some(json!({"type":"procedure"}));
    assert!(v.search(q, 3).unwrap().context.is_empty());
}

#[cfg(unix)]
#[test]
fn symlinks_cannot_extend_vault_reads_or_archive_writes() {
    use std::os::unix::fs::symlink;
    let t = Temp::new();
    let outside = Temp::new();
    outside.note("secret.md", "secret", "outside");
    symlink(&outside.0, t.0.join("linked")).unwrap();
    let v = t.vault();
    assert_eq!(v.index(false).unwrap().indexed, 0);
    let note = v.add("inside", json!({})).unwrap();
    symlink(&outside.0, t.0.join("archive")).unwrap();
    assert!(v.archive(&note.id).is_err());
    assert!(v.get(&note.id).is_ok());
}

#[test]
fn cooperating_writers_reject_a_held_vault_lock_without_modifying_notes() {
    use fs2::FileExt;
    let t = Temp::new();
    let v = t.vault();
    let note = v.add("original", json!({})).unwrap();
    let lock = fs::OpenOptions::new()
        .create(true)
        .truncate(false)
        .read(true)
        .write(true)
        .open(t.0.join(".memori/vault.lock"))
        .unwrap();
    lock.try_lock_exclusive().unwrap();
    assert!(v
        .update(&note.id, Some("changed"), None)
        .unwrap_err()
        .to_string()
        .contains("busy"));
    assert!(v.index(false).is_err());
    assert_eq!(v.get(&note.id).unwrap().content.trim(), "original");
    drop(lock);
    v.update(&note.id, Some("changed"), None).unwrap();
}

#[test]
fn exact_stable_ids_take_precedence_over_longer_id_prefixes() {
    let t = Temp::new();
    t.note("first.md", "a", "common first");
    t.note("second.md", "ab", "common second");
    let v = t.vault();
    v.index(false).unwrap();
    assert_eq!(v.get("a").unwrap().id, "a");
    assert_eq!(v.search(query("common"), 0).unwrap().matches.len(), 2);
    v.archive("a").unwrap();
    assert_eq!(v.get("ab").unwrap().id, "ab");
}

#[test]
fn markdown_code_indentation_survives_add_and_update() {
    let t = Temp::new();
    let v = t.vault();
    let note = v
        .add("    print('verified')", json!({"type":"procedure"}))
        .unwrap();
    assert_eq!(note.content, "    print('verified')");
    let updated = v
        .update(&note.id, None, Some(json!({"checked":true})))
        .unwrap();
    assert_eq!(updated.content, note.content);
}
