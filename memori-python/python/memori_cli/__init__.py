"""memori CLI -- store and search AI agent memories from the command line.

Usage:
  memori store "User prefers dark mode" --meta '{"type": "preference"}'
  memori search --text "dark mode" --limit 5
  memori search --text "preferences" --filter '{"type": "preference"}'
  memori get <id>
  memori update <id> --content "updated text" --meta '{"type": "fact"}'
  memori tag <id> topic=testing verified=true
  memori delete <id>
  memori count
  memori stats
  memori context "kafka architecture"
  memori embed               # backfill embeddings on old memories
  memori export > backup.jsonl
  memori import < backup.jsonl
  memori purge --type temporary --confirm
  memori setup          # auto-configure Claude Code
  memori setup --show   # preview the CLAUDE.md snippet
  memori setup --undo   # remove the snippet
"""
import argparse
import json
import os
import sys
import threading
import webbrowser
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from memori import PyMemori

__version__ = "0.6.0"

DEFAULT_DB = os.path.expanduser("~/.claude/memori.db")
DEFAULT_DEDUP_THRESHOLD = 0.92

KNOWN_TYPES = frozenset([
  "debugging", "decision", "architecture", "pattern",
  "preference", "fact", "roadmap", "temporary",
])

SNIPPET_START_PREFIX = "<!-- memori:start"
SNIPPET_END_PREFIX = "<!-- memori:end"
SNIPPET_START = f"<!-- memori:start v{__version__} -->"
SNIPPET_END = f"<!-- memori:end v{__version__} -->"


def _get_db(path=None):
  return PyMemori(path or DEFAULT_DB)


def _err(error_type, message, exit_code=1, use_json=False, input_id=None):
  """Print an error and exit. When use_json is True, emit structured JSON to stderr."""
  if use_json:
    obj = {"error": error_type, "message": message}
    if input_id is not None:
      obj["id"] = input_id
    print(json.dumps(obj), file=sys.stderr)
  else:
    print(f"{message}", file=sys.stderr)
  sys.exit(exit_code)


def _parse_json(value, flag_name, use_json=False):
  """Parse a JSON string from a CLI flag, exiting with a clean message on failure."""
  try:
    return json.loads(value)
  except json.JSONDecodeError as e:
    _err("invalid_json", f"Invalid JSON for {flag_name}: {e}", exit_code=2, use_json=use_json)


def _snippet_text():
  """Load the CLAUDE.md snippet from bundled data."""
  data_dir = Path(__file__).parent / "data"
  snippet_file = data_dir / "claude_snippet.md"
  return snippet_file.read_text()


def _json_indent(args):
  """Return indent level for JSON output: None for --raw, 2 otherwise."""
  return None if getattr(args, "raw", False) else 2


def _parse_date_arg(value, use_json=False):
  """Parse an ISO date string to a Unix timestamp (float)."""
  try:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
      dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()
  except ValueError:
    _err("invalid_date", f"Invalid date: '{value}'. Expected ISO format like 2025-01-01 or 2025-01-01T12:00:00",
         exit_code=2, use_json=use_json)


def _resolve_id(db, prefix):
  """Resolve a prefix to full UUID via get_readonly(). Returns the full ID or the prefix if unresolvable."""
  mem = db.get_readonly(prefix)
  return mem["id"] if mem else prefix


# -- Commands --


def _warn_unknown_type(meta):
  """Warn if metadata has an unrecognized type value (never reject)."""
  if meta and isinstance(meta, dict) and "type" in meta:
    t = meta["type"]
    if isinstance(t, str) and t not in KNOWN_TYPES:
      known = ", ".join(sorted(KNOWN_TYPES))
      print(f"Warning: unknown type '{t}'. Known types: {known}", file=sys.stderr)


def cmd_store(args):
  db = _get_db(args.db)
  meta = _parse_json(args.meta, "--meta", use_json=args.json) if args.meta else None
  _warn_unknown_type(meta)
  vector = _parse_json(args.vector, "--vector", use_json=args.json) if args.vector else None

  # Determine dedup threshold
  dedup_threshold = None
  if not args.no_dedup:
    dedup_threshold = args.dedup_threshold

  result = db.insert(
    args.content,
    vector=vector,
    metadata=meta,
    dedup_threshold=dedup_threshold,
    no_embed=args.no_embed,
  )

  mid = result["id"]
  action = result["action"]

  if args.json:
    print(json.dumps({"id": mid, "status": action}))
  else:
    if action == "deduplicated":
      print(f"Deduplicated: {mid} (updated existing memory)")
    else:
      print(f"Stored: {mid}")


def cmd_search(args):
  db = _get_db(args.db)
  vector = _parse_json(args.vector, "--vector", use_json=args.json) if args.vector else None
  filt = _parse_json(args.filter, "--filter", use_json=args.json) if args.filter else None
  text_only = getattr(args, "text_only", False)
  include_vectors = getattr(args, "include_vectors", False)

  # Parse date range filters
  before_ts = _parse_date_arg(args.before, use_json=args.json) if getattr(args, "before", None) else None
  after_ts = _parse_date_arg(args.after, use_json=args.json) if getattr(args, "after", None) else None

  results = db.search(
    vector=vector, text=args.text, filter=filt, limit=args.limit,
    text_only=text_only, before=before_ts, after=after_ts,
  )

  if args.json:
    out = []
    for r in results:
      entry = {
        "id": r["id"],
        "content": r["content"],
        "score": r.get("score"),
        "metadata": r.get("metadata"),
        "created_at": r.get("created_at"),
        "access_count": r.get("access_count", 0),
      }
      if include_vectors:
        entry["vector"] = r.get("vector")
      out.append(entry)
    print(json.dumps(out, indent=_json_indent(args), default=str))
  else:
    if not results:
      print("No results.")
      return
    for r in results:
      score = f"[{r['score']:.4f}]" if r.get("score") is not None else ""
      meta = json.dumps(r.get("metadata") or {})
      access = r.get("access_count", 0)
      access_str = f" ({access} hits)" if access > 5 else ""
      print(f"{r['id'][:8]} {score} {r['content']}  meta={meta}{access_str}")


def cmd_get(args):
  db = _get_db(args.db)
  mem = db.get(args.id)
  if mem:
    if not getattr(args, "include_vectors", False):
      mem.pop("vector", None)
    print(json.dumps(mem, indent=_json_indent(args), default=str))
  else:
    _err("not_found", f"No memory matching '{args.id}' (try 'memori list' to see available memories)",
         exit_code=1, use_json=args.json, input_id=args.id)


def cmd_update(args):
  db = _get_db(args.db)
  content = args.content
  meta = _parse_json(args.meta, "--meta", use_json=args.json) if args.meta else None
  vector = _parse_json(args.vector, "--vector", use_json=args.json) if args.vector else None

  if content is None and meta is None and vector is None:
    _err("missing_argument", "At least one of --content, --meta, or --vector is required.",
         exit_code=2, use_json=args.json)

  # Default is merge; --replace switches to full replacement
  merge = not getattr(args, "replace", False)

  full_id = _resolve_id(db, args.id)

  try:
    db.update(args.id, content=content, vector=vector, metadata=meta, merge_metadata=merge)
  except RuntimeError:
    _err("not_found", f"No memory matching '{args.id}' (try 'memori list' to see available memories)",
         exit_code=1, use_json=args.json, input_id=args.id)

  if args.json:
    print(json.dumps({"id": full_id, "status": "updated"}))
  else:
    print(f"Updated {full_id}")


def _parse_tag_value(v):
  """Parse a tag value string into its natural type (bool, int, float, or str)."""
  if v.lower() == "true":
    return True
  if v.lower() == "false":
    return False
  try:
    return int(v)
  except ValueError:
    pass
  try:
    return float(v)
  except ValueError:
    pass
  return v


def cmd_tag(args):
  db = _get_db(args.db)

  # Parse key=value pairs with type coercion
  tags = {}
  for pair in args.tags:
    if "=" not in pair:
      _err("invalid_format", f"Invalid tag format (expected key=value): {pair}",
           exit_code=2, use_json=args.json)
    k, v = pair.split("=", 1)
    tags[k] = _parse_tag_value(v)

  full_id = _resolve_id(db, args.id)

  try:
    # merge_metadata=True handles the read-modify-write in Rust
    db.update(args.id, metadata=tags, merge_metadata=True)
  except RuntimeError:
    _err("not_found", f"No memory matching '{args.id}' (try 'memori list' to see available memories)",
         exit_code=1, use_json=args.json, input_id=args.id)

  # Fetch merged result for display (readonly to avoid inflating access_count)
  mem = db.get_readonly(args.id)
  merged = mem.get("metadata") or {} if mem else tags

  if args.json:
    print(json.dumps(merged, indent=_json_indent(args)))
  else:
    print(f"Tagged {full_id}: {merged}")


def cmd_list(args):
  db = _get_db(args.db)
  include_vectors = getattr(args, "include_vectors", False)

  # Parse date range filters
  before_ts = _parse_date_arg(args.before, use_json=args.json) if getattr(args, "before", None) else None
  after_ts = _parse_date_arg(args.after, use_json=args.json) if getattr(args, "after", None) else None

  results = db.list(
    type_filter=args.type,
    sort=args.sort,
    limit=args.limit,
    offset=args.offset,
    before=before_ts,
    after=after_ts,
  )

  if args.json:
    out = []
    for r in results:
      entry = {
        "id": r["id"],
        "content": r["content"],
        "metadata": r.get("metadata"),
        "created_at": r.get("created_at"),
        "updated_at": r.get("updated_at"),
        "last_accessed": r.get("last_accessed"),
        "access_count": r.get("access_count", 0),
      }
      if include_vectors:
        entry["vector"] = r.get("vector")
      out.append(entry)
    print(json.dumps(out, indent=_json_indent(args), default=str))
  else:
    if not results:
      print("No memories found.")
      return
    for r in results:
      meta_type = ""
      meta = r.get("metadata")
      if meta and isinstance(meta, dict) and "type" in meta:
        meta_type = f" [{meta['type']}]"
      access = r.get("access_count", 0)
      access_str = f" ({access} hits)" if access > 0 else ""
      content = r["content"][:100] + ("..." if len(r["content"]) > 100 else "")
      print(f"{r['id'][:8]}{meta_type}{access_str} {content}")


def cmd_context(args):
  import time
  db = _get_db(args.db)
  topic = args.topic
  limit = args.limit

  total = db.count()

  # Build search filter (optionally scoped to project)
  search_filter = None
  if getattr(args, "project", None):
    search_filter = {"project": args.project}

  # Relevant matches (always hybrid search -- let Rust handle efficiency)
  matches = db.search(text=topic, filter=search_filter, limit=limit)
  # Recent memories (by last update, not creation)
  recent = db.list(sort="updated", limit=5)
  # Frequently accessed (only show if any have been accessed)
  frequent = db.list(sort="count", limit=3)
  frequent = [r for r in frequent if r.get("access_count", 0) > 0]
  # Stale memories (created 30+ days ago, never accessed)
  thirty_days_ago = time.time() - 30 * 86400
  stale_candidates = db.list(sort="created", limit=20, before=thirty_days_ago)
  stale = [r for r in stale_candidates if r.get("access_count", 0) == 0][:5]
  # Type distribution
  type_dist = db.type_distribution()

  compact = getattr(args, "compact", False)

  if compact or (args.json and compact):
    # Minimal flat JSON for agent consumption
    def _compact_entry(r):
      entry = {"id": r["id"][:8], "content": r["content"]}
      if r.get("score") is not None:
        entry["score"] = round(r["score"], 4)
      meta = r.get("metadata")
      if meta and isinstance(meta, dict) and "type" in meta:
        entry["type"] = meta["type"]
      return entry

    out = {
      "topic": topic,
      "total": total,
      "matches": [_compact_entry(r) for r in matches],
      "recent": [r["content"][:100] for r in recent],
      "frequent": [r["content"][:100] for r in frequent],
      "stale": [r["content"][:100] for r in stale],
    }
    print(json.dumps(out, default=str))
  elif args.json:
    out = {
      "topic": topic,
      "matches": [
        {"id": r["id"], "content": r["content"], "score": r.get("score"),
         "metadata": r.get("metadata"), "created_at": r.get("created_at")}
        for r in matches
      ],
      "recent": [
        {"id": r["id"], "content": r["content"], "metadata": r.get("metadata"),
         "updated_at": r.get("updated_at")}
        for r in recent
      ],
      "frequent": [
        {"id": r["id"], "content": r["content"], "access_count": r.get("access_count", 0)}
        for r in frequent
      ],
      "stale": [
        {"id": r["id"], "content": r["content"], "created_at": r.get("created_at")}
        for r in stale
      ],
      "types": type_dist,
      "total": total,
    }
    print(json.dumps(out, indent=_json_indent(args), default=str))
  else:
    # Human-readable markdown sections
    print(f"## Relevant Memories: \"{topic}\"\n")
    if matches:
      for r in matches:
        score = f" [{r['score']:.4f}]" if r.get("score") is not None else ""
        content = r["content"][:120] + ("..." if len(r["content"]) > 120 else "")
        print(f"- {r['id'][:8]}{score} {content}")
    else:
      print("  (no matches)")

    print(f"\n## Recent Memories (by last update)\n")
    if recent:
      for r in recent:
        content = r["content"][:100] + ("..." if len(r["content"]) > 100 else "")
        meta_type = ""
        meta = r.get("metadata")
        if meta and isinstance(meta, dict) and "type" in meta:
          meta_type = f" [{meta['type']}]"
        print(f"- {r['id'][:8]}{meta_type} {content}")
    else:
      print("  (empty)")

    if frequent:
      print(f"\n## Frequently Accessed\n")
      for r in frequent:
        content = r["content"][:100] + ("..." if len(r["content"]) > 100 else "")
        hits = r.get("access_count", 0)
        print(f"- {r['id'][:8]} ({hits} hits) {content}")

    if stale:
      print(f"\n## Stale Memories (30+ days, never accessed)\n")
      for r in stale:
        content = r["content"][:100] + ("..." if len(r["content"]) > 100 else "")
        print(f"- {r['id'][:8]} {content}")

    print(f"\n## Stats\n")
    print(f"Total: {total} memories")
    if type_dist:
      parts = [f"{t}: {c}" for t, c in sorted(type_dist.items(), key=lambda x: -x[1])]
      print(f"Types: {', '.join(parts)}")


def cmd_embed(args):
  db = _get_db(args.db)
  stats = db.embedding_stats()
  total = stats["total"]
  already_embedded = stats["embedded"]
  to_embed = total - already_embedded

  if to_embed == 0:
    if args.json:
      print(json.dumps({"embedded": 0, "total": total, "skipped": total}))
    else:
      print(f"All {total} memories already have embeddings.")
    return

  if not args.json:
    print(f"Backfilling embeddings for {to_embed} memories (batch size: {args.batch_size})...")

  processed = db.backfill_embeddings(args.batch_size)

  if args.json:
    print(json.dumps({
      "embedded": processed,
      "total": total,
      "skipped": already_embedded,
    }))
  else:
    print(f"Embedded {processed}/{total} memories ({already_embedded} already had embeddings)")


def cmd_export(args):
  db = _get_db(args.db)
  include_vectors = args.include_vectors
  batch_size = 100
  offset = 0

  while True:
    batch = db.list(sort="created", limit=batch_size, offset=offset)
    if not batch:
      break
    for r in batch:
      entry = {
        "id": r["id"],
        "content": r["content"],
        "metadata": r.get("metadata"),
        "created_at": r.get("created_at"),
        "updated_at": r.get("updated_at"),
        "last_accessed": r.get("last_accessed"),
        "access_count": r.get("access_count", 0),
        "vector": r.get("vector") if include_vectors else None,
      }
      print(json.dumps(entry, default=str))
    offset += len(batch)
    if len(batch) < batch_size:
      break


def cmd_import(args):
  db = _get_db(args.db)
  new_ids = args.new_ids
  imported = 0
  errors = 0

  for line in sys.stdin:
    line = line.strip()
    if not line:
      continue
    try:
      entry = json.loads(line)
      content = entry["content"]
      metadata = entry.get("metadata")
      vector = entry.get("vector")
      created_at = entry.get("created_at")
      updated_at = entry.get("updated_at")

      last_accessed = entry.get("last_accessed")
      access_count = entry.get("access_count", 0)

      if new_ids:
        result = db.insert(content, vector=vector, metadata=metadata, no_embed=False)
        mem_id = result["id"]
      else:
        mem_id = db.insert_with_id(
          entry["id"], content,
          vector=vector, metadata=metadata,
          created_at=created_at, updated_at=updated_at,
        )

      # Restore access stats if present in export
      if last_accessed is not None or access_count > 0:
        db.set_access_stats(mem_id, last_accessed=last_accessed, access_count=access_count)

      imported += 1
    except Exception as e:
      errors += 1
      if not args.json:
        print(f"Error on line {imported + errors}: {e}", file=sys.stderr)

  if args.json:
    print(json.dumps({"imported": imported, "errors": errors}))
  else:
    print(f"Imported {imported} memories ({errors} errors)")


def cmd_purge(args):
  db = _get_db(args.db)

  if not args.before and not args.type:
    _err("missing_argument", "At least one of --before or --type is required.",
         exit_code=2, use_json=args.json)

  before_ts = _parse_date_arg(args.before, use_json=args.json) if args.before else None

  if args.confirm:
    # Actually delete (AND logic when both flags present, matching preview)
    if before_ts is not None and args.type:
      to_delete = db.list(type_filter=args.type, sort="created", limit=1_000_000, before=before_ts)
      for mem in to_delete:
        db.delete(mem["id"])
      total_deleted = len(to_delete)
    elif before_ts is not None:
      total_deleted = db.delete_before(before_ts)
    elif args.type:
      total_deleted = db.delete_by_type(args.type)
    else:
      total_deleted = 0

    criteria = {}
    if args.before:
      criteria["before"] = args.before
    if args.type:
      criteria["type"] = args.type

    if args.json:
      print(json.dumps({"action": "deleted", "count": total_deleted, "criteria": criteria}))
    else:
      print(f"Deleted {total_deleted} memories")
  else:
    # Dry-run: preview what would be deleted (uses list, not search -- no vector overhead)
    preview_items = db.list(
      type_filter=args.type,
      sort="created",
      limit=1_000_000,
      before=before_ts,
    )
    preview_count = len(preview_items)

    criteria = {}
    if args.before:
      criteria["before"] = args.before
    if args.type:
      criteria["type"] = args.type

    if args.json:
      print(json.dumps({"action": "preview", "count": preview_count, "criteria": criteria}))
    else:
      print(f"Would delete {preview_count} memories (dry-run)")
      if preview_items:
        print("Preview (first 10):")
        for r in preview_items[:10]:
          content = r["content"][:80] + ("..." if len(r["content"]) > 80 else "")
          print(f"  {r['id'][:8]} {content}")
      print("\nRe-run with --confirm to delete.")


def cmd_related(args):
  db = _get_db(args.db)
  include_vectors = getattr(args, "include_vectors", False)
  try:
    results = db.related(args.id, limit=args.limit)
  except RuntimeError as e:
    err_msg = str(e)
    if "no embedding" in err_msg:
      error_type = "no_embedding"
      hint = " (run 'memori embed' to generate embeddings)"
    elif "ambiguous" in err_msg:
      error_type = "ambiguous_prefix"
      hint = " (use a longer prefix to disambiguate)"
    else:
      error_type = "not_found"
      hint = " (try 'memori list' to see available memories)"
    _err(error_type, err_msg + hint, exit_code=1, use_json=args.json, input_id=args.id)

  if args.json:
    out = []
    for r in results:
      entry = {
        "id": r["id"],
        "content": r["content"],
        "score": r.get("score"),
        "metadata": r.get("metadata"),
        "created_at": r.get("created_at"),
        "access_count": r.get("access_count", 0),
      }
      if include_vectors:
        entry["vector"] = r.get("vector")
      out.append(entry)
    print(json.dumps(out, indent=_json_indent(args), default=str))
  else:
    if not results:
      print("No related memories found.")
      return
    for r in results:
      score = f"[{r['score']:.4f}]" if r.get("score") is not None else ""
      meta = json.dumps(r.get("metadata") or {})
      content = r["content"][:100] + ("..." if len(r["content"]) > 100 else "")
      print(f"{r['id'][:8]} {score} {content}  meta={meta}")


def cmd_delete(args):
  db = _get_db(args.db)
  full_id = _resolve_id(db, args.id)
  try:
    db.delete(args.id)
  except RuntimeError:
    _err("not_found", f"No memory matching '{args.id}' (try 'memori list' to see available memories)",
         exit_code=1, use_json=args.json, input_id=args.id)
  if args.json:
    print(json.dumps({"id": full_id, "status": "deleted"}))
  else:
    print(f"Deleted {full_id}")


def cmd_count(args):
  db = _get_db(args.db)
  count = db.count()
  if args.json:
    print(json.dumps({"count": count}))
  else:
    print(count)


def cmd_stats(args):
  db_path = args.db or DEFAULT_DB
  db = _get_db(db_path)
  count = db.count()

  # DB file size
  try:
    size_bytes = os.path.getsize(db_path)
    if size_bytes < 1024:
      size_str = f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
      size_str = f"{size_bytes / 1024:.1f} KB"
    else:
      size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
  except OSError:
    size_str = "unknown"

  # Metadata type distribution via SQL (O(1) vs old O(N) Python loop)
  type_counts = db.type_distribution()

  # Embedding coverage
  embed_stats = db.embedding_stats()
  embedded = embed_stats["embedded"]
  total = embed_stats["total"]

  if args.json:
    print(json.dumps({
      "db_path": db_path,
      "count": count,
      "file_size": size_str,
      "types": type_counts,
      "embedded": embedded,
      "embedding_coverage": f"{embedded}/{total}" if total > 0 else "0/0",
    }, indent=_json_indent(args)))
  else:
    print(f"Database:  {db_path}")
    print(f"Memories:  {count}")
    print(f"File size: {size_str}")
    if total > 0:
      pct = embedded * 100 // total
      print(f"Embedded:  {embedded}/{total} ({pct}%)")
    if type_counts:
      print("Types:")
      for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {t}: {c}")


def cmd_gc(args):
  db_path = args.db or DEFAULT_DB
  try:
    size_before = os.path.getsize(db_path)
  except OSError:
    size_before = 0

  db = _get_db(db_path)
  db.vacuum()

  try:
    size_after = os.path.getsize(db_path)
  except OSError:
    size_after = 0

  saved = size_before - size_after
  if args.json:
    print(json.dumps({
      "before_bytes": size_before,
      "after_bytes": size_after,
      "saved_bytes": saved,
    }, indent=_json_indent(args)))
  else:
    def fmt(b):
      if b < 1024:
        return f"{b} B"
      elif b < 1024 * 1024:
        return f"{b / 1024:.1f} KB"
      return f"{b / (1024 * 1024):.1f} MB"
    print(f"Compacted: {fmt(size_before)} -> {fmt(size_after)} (saved {fmt(saved)})")


def cmd_setup(args):
  if args.show:
    print(_snippet_text())
    return

  # Find CLAUDE.md
  candidates = [
    Path.cwd() / "CLAUDE.md",
    Path.home() / ".claude" / "CLAUDE.md",
  ]
  target = None
  for c in candidates:
    if c.exists():
      target = c
      break

  if target is None:
    # Default to ~/.claude/CLAUDE.md (create it)
    target = Path.home() / ".claude" / "CLAUDE.md"
    target.parent.mkdir(parents=True, exist_ok=True)

  content = target.read_text() if target.exists() else ""

  def _find_markers(text):
    """Find start/end marker positions and extract version if present."""
    start_idx = text.find(SNIPPET_START_PREFIX)
    if start_idx == -1:
      return None
    # Find end of start marker line
    start_line_end = text.index("-->", start_idx) + 3
    # Extract version from start marker
    marker_line = text[start_idx:start_line_end]
    old_version = None
    if " v" in marker_line:
      old_version = marker_line.split(" v")[1].rstrip(" ->")
    # Find end marker
    end_idx = text.find(SNIPPET_END_PREFIX, start_line_end)
    if end_idx == -1:
      return None
    end_line_end = text.index("-->", end_idx) + 3
    if end_line_end < len(text) and text[end_line_end] == "\n":
      end_line_end += 1
    return start_idx, end_line_end, old_version

  if args.undo:
    markers = _find_markers(content)
    if markers is None:
      print("No memori snippet found -- nothing to remove.")
      return
    start_idx, end_idx, _ = markers
    content = content[:start_idx] + content[end_idx:]
    target.write_text(content)
    print(f"Removed memori snippet from {target}")
    return

  markers = _find_markers(content)
  if markers is not None:
    _, _, old_version = markers
    if old_version == __version__:
      print(f"Memori snippet already present in {target}")
      return
    # Stale version -- re-inject
    start_idx, end_idx, _ = markers
    old_v = old_version or "unknown"
    content = content[:start_idx] + content[end_idx:]
    snippet = _snippet_text()
    separator = "\n" if content and not content.endswith("\n") else ""
    separator += "\n" if content else ""
    content += separator + snippet
    target.write_text(content)
    print(f"Updated memori snippet in {target} (v{old_v} -> v{__version__})")
    return

  snippet = _snippet_text()
  # Append with a blank line separator
  separator = "\n" if content and not content.endswith("\n") else ""
  separator += "\n" if content else ""
  content += separator + snippet
  target.write_text(content)
  print(f"Added memori snippet to {target}")


class DashboardHandler(BaseHTTPRequestHandler):
  db = None

  def log_message(self, format, *args):
    pass  # silence request logs

  def _json_response(self, data, status=200):
    body = json.dumps(data, default=str).encode()
    self.send_response(status)
    self.send_header("Content-Type", "application/json")
    self.send_header("Content-Length", str(len(body)))
    self.end_headers()
    self.wfile.write(body)

  def _html_response(self, html):
    body = html.encode()
    self.send_response(200)
    self.send_header("Content-Type", "text/html; charset=utf-8")
    self.send_header("Content-Length", str(len(body)))
    self.end_headers()
    self.wfile.write(body)

  def do_GET(self):
    parsed = urlparse(self.path)
    path = parsed.path
    qs = parse_qs(parsed.query)

    def qfirst(key, default=None):
      return qs.get(key, [default])[0]

    if path == "/":
      data_dir = Path(__file__).parent / "data"
      html = (data_dir / "dashboard.html").read_text()
      self._html_response(html)

    elif path == "/api/stats":
      db = self.db
      count = db.count()
      types = db.type_distribution()
      embed = db.embedding_stats()
      self._json_response({
        "count": count,
        "types": types,
        "embedding": embed,
      })

    elif path == "/api/memories" and not path.startswith("/api/memories/"):
      db = self.db
      type_filter = qfirst("type")
      sort = qfirst("sort", "created")
      limit = int(qfirst("limit", "20"))
      offset = int(qfirst("offset", "0"))
      before = float(qfirst("before")) if qfirst("before") else None
      after = float(qfirst("after")) if qfirst("after") else None
      results = db.list(
        type_filter=type_filter, sort=sort,
        limit=limit, offset=offset, before=before, after=after,
      )
      out = []
      for r in results:
        r.pop("vector", None)
        out.append(r)
      self._json_response(out)

    elif path.startswith("/api/memories/"):
      mem_id = path[len("/api/memories/"):]
      if not mem_id:
        self._json_response({"error": "missing id"}, 400)
        return
      mem = self.db.get_readonly(mem_id)
      if mem:
        mem.pop("vector", None)
        self._json_response(mem)
      else:
        self._json_response({"error": "not_found"}, 404)

    elif path == "/api/search":
      db = self.db
      text = qfirst("text")
      filt_str = qfirst("filter")
      filt = json.loads(filt_str) if filt_str else None
      limit = int(qfirst("limit", "10"))
      text_only = qfirst("text_only", "false") == "true"
      before = float(qfirst("before")) if qfirst("before") else None
      after = float(qfirst("after")) if qfirst("after") else None
      results = db.search(
        text=text, filter=filt, limit=limit,
        text_only=text_only, before=before, after=after,
      )
      out = []
      for r in results:
        r.pop("vector", None)
        out.append(r)
      self._json_response(out)

    elif path.startswith("/api/related/"):
      mem_id = path[len("/api/related/"):]
      limit = int(qfirst("limit", "5"))
      try:
        results = self.db.related(mem_id, limit=limit)
        out = []
        for r in results:
          r.pop("vector", None)
          out.append(r)
        self._json_response(out)
      except RuntimeError as e:
        self._json_response({"error": str(e)}, 404)

    else:
      self.send_response(404)
      self.end_headers()


def cmd_ui(args):
  db = _get_db(args.db)
  DashboardHandler.db = db
  port = args.port
  server = HTTPServer(("127.0.0.1", port), DashboardHandler)
  url = f"http://127.0.0.1:{port}"
  print(f"Memori dashboard: {url}")
  print("Press Ctrl+C to stop")
  if not args.no_open:
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()
  try:
    server.serve_forever()
  except KeyboardInterrupt:
    print("\nStopped.")
    server.server_close()


# -- Main --


def main():
  # Shared parent parser for output format flags (accepted on every subcommand).
  # SUPPRESS prevents subparser defaults from overriding main parser values,
  # so both `memori --json search` and `memori search --json` work.
  output_parser = argparse.ArgumentParser(add_help=False)
  output_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS,
                              help="Machine-readable JSON output")
  output_parser.add_argument("--raw", action="store_true", default=argparse.SUPPRESS,
                              help="Compact single-line JSON (no indent). Implies --json")

  parser = argparse.ArgumentParser(
    prog="memori",
    description="Memori -- embedded AI agent memory (SQLite + vector search + FTS5)",
    epilog="Quick start:\n"
           "  memori context \"<topic>\"                          # start of session\n"
           "  memori store \"<insight>\" --meta '{\"type\": \"debugging\"}'  # after fixing a bug\n"
           "  memori search --text \"<query>\"                    # before investigating\n"
           "  memori tag <id> verified=true priority=1           # enrich with typed tags\n"
           "  memori setup                                       # auto-configure Claude Code\n"
           "\nRun 'memori <command> --help' for details and examples on any command.\n"
           "Known memory types: debugging, decision, architecture, pattern, preference, fact, roadmap, temporary",
    formatter_class=argparse.RawDescriptionHelpFormatter,
  )
  parser.add_argument("--db", help=f"Database path (default: {DEFAULT_DB})")
  parser.add_argument("--json", action="store_true", help="Machine-readable JSON output")
  parser.add_argument("--raw", action="store_true",
                       help="Compact single-line JSON (no indent). Implies --json")
  parser.add_argument(
    "--version", action="version",
    version=f"memori {__version__}",
  )

  sub = parser.add_subparsers(dest="command", required=True)

  _F = argparse.RawDescriptionHelpFormatter

  # store
  p_store = sub.add_parser("store", help="Store a memory", parents=[output_parser],
      epilog="Examples:\n  memori store \"FTS5 hyphens crash MATCH\" --meta '{\"type\": \"debugging\"}'\n  memori store \"prefer dark mode\" --meta '{\"type\": \"preference\"}' --json\n\nKnown types: debugging, decision, architecture, pattern, preference, fact, roadmap, temporary",
      formatter_class=_F)
  p_store.add_argument("content", help="Text content to store")
  p_store.add_argument("--meta", help="JSON metadata object")
  p_store.add_argument("--vector", help="JSON array of floats")
  p_store.add_argument("--no-embed", action="store_true",
                        help="Skip auto-embedding (store without vector)")
  p_store.add_argument("--no-dedup", action="store_true",
                        help="Skip deduplication check")
  p_store.add_argument("--dedup-threshold", type=float, default=DEFAULT_DEDUP_THRESHOLD,
                        help=f"Cosine similarity threshold for dedup (default: {DEFAULT_DEDUP_THRESHOLD})")
  p_store.set_defaults(func=cmd_store)

  # search
  p_search = sub.add_parser("search", help="Search memories", parents=[output_parser],
      epilog="Examples:\n  memori search --text 'FTS5 crash' --filter '{\"type\": \"debugging\"}'\n  memori search --text 'dark mode' --limit 3 --json\n  memori search --text 'kafka' --text-only --before 2025-01-01",
      formatter_class=_F)
  p_search.add_argument("--text", help="Text query (FTS5)")
  p_search.add_argument("--vector", help="Vector query (JSON float array)")
  p_search.add_argument("--filter", help="Metadata filter (JSON object)")
  p_search.add_argument("--limit", type=int, default=10, help="Max results (default: 10)")
  p_search.add_argument("--text-only", action="store_true",
                         help="Force FTS5-only search (skip auto-vectorization)")
  p_search.add_argument("--include-vectors", action="store_true",
                         help="Include vector data in JSON output (omitted by default)")
  p_search.add_argument("--before", help="Only memories created before this ISO date")
  p_search.add_argument("--after", help="Only memories created after this ISO date")
  p_search.set_defaults(func=cmd_search)

  # get
  p_get = sub.add_parser("get", help="Get memory by ID", parents=[output_parser],
      epilog="Examples:\n  memori get a1b2c3d4\n  memori get a1b2 --json\n  memori get a1b2c3d4 --include-vectors --json",
      formatter_class=_F)
  p_get.add_argument("id")
  p_get.add_argument("--include-vectors", action="store_true",
                      help="Include vector data in output (omitted by default to save tokens)")
  p_get.set_defaults(func=cmd_get)

  # update
  p_update = sub.add_parser("update", help="Update an existing memory", parents=[output_parser],
      epilog="Examples:\n  memori update a1b2 --content 'corrected text'\n  memori update a1b2 --content 'corrected text' --json\n  memori update a1b2 --meta '{\"verified\": true}'\n  memori update a1b2 --meta '{\"type\": \"fact\"}' --replace",
      formatter_class=_F)
  p_update.add_argument("id", help="Memory ID to update")
  p_update.add_argument("--content", help="New text content")
  p_update.add_argument("--meta", help="New metadata (JSON object, merged by default)")
  p_update.add_argument("--vector", help="New vector (JSON float array)")
  p_update.add_argument("--replace", action="store_true",
                         help="Replace metadata entirely instead of merging")
  p_update.set_defaults(func=cmd_update)

  # tag
  p_tag = sub.add_parser("tag", help="Add key=value tags to memory metadata", parents=[output_parser],
      epilog="Examples:\n  memori tag a1b2 topic=kafka verified=true\n  memori tag a1b2 priority=1 status=active --json",
      formatter_class=_F)
  p_tag.add_argument("id", help="Memory ID to tag")
  p_tag.add_argument("tags", nargs="+", help="Tags as key=value pairs")
  p_tag.set_defaults(func=cmd_tag)

  # list
  p_list = sub.add_parser("list", help="Browse memories with sort and pagination", parents=[output_parser],
      epilog="Examples:\n  memori list --type debugging --sort count\n  memori list --limit 5 --before 2025-06-01 --json",
      formatter_class=_F)
  p_list.add_argument("--type", help="Filter by metadata type")
  p_list.add_argument("--sort", default="created",
                       choices=["created", "updated", "accessed", "count"],
                       help="Sort field (default: created)")
  p_list.add_argument("--limit", type=int, default=20, help="Max results (default: 20)")
  p_list.add_argument("--offset", type=int, default=0, help="Pagination offset (default: 0)")
  p_list.add_argument("--include-vectors", action="store_true",
                       help="Include vector data in JSON output")
  p_list.add_argument("--before", help="Only memories created before this ISO date")
  p_list.add_argument("--after", help="Only memories created after this ISO date")
  p_list.set_defaults(func=cmd_list)

  # related
  p_related = sub.add_parser("related", help="Find memories similar to a given memory", parents=[output_parser],
      epilog="Examples:\n  memori related a1b2c3d4 --limit 3\n  memori related a1b2 --json",
      formatter_class=_F)
  p_related.add_argument("id", help="Memory ID (or unique prefix)")
  p_related.add_argument("--limit", type=int, default=5, help="Max results (default: 5)")
  p_related.add_argument("--include-vectors", action="store_true",
                          help="Include vector data in JSON output")
  p_related.set_defaults(func=cmd_related)

  # delete
  p_del = sub.add_parser("delete", help="Delete memory by ID", parents=[output_parser],
      epilog="Examples:\n  memori delete a1b2c3d4\n  memori delete a1b2 --json",
      formatter_class=_F)
  p_del.add_argument("id")
  p_del.set_defaults(func=cmd_delete)

  # count
  p_count = sub.add_parser("count", help="Count memories", parents=[output_parser],
      epilog="Examples:\n  memori count\n  memori count --json",
      formatter_class=_F)
  p_count.set_defaults(func=cmd_count)

  # stats
  p_stats = sub.add_parser("stats", help="Show database stats", parents=[output_parser],
      epilog="Examples:\n  memori stats\n  memori stats --json",
      formatter_class=_F)
  p_stats.set_defaults(func=cmd_stats)

  # context
  p_context = sub.add_parser("context", help="Load relevant context for a topic", parents=[output_parser],
      epilog="Examples:\n  memori context 'kafka architecture'\n  memori context 'debugging tips' --compact\n  memori context 'auth' --project myapp --json",
      formatter_class=_F)
  p_context.add_argument("topic", help="Topic to search for")
  p_context.add_argument("--limit", type=int, default=10, help="Max relevant matches")
  p_context.add_argument("--project", help="Scope search to a project (filters by metadata.project)")
  p_context.add_argument("--compact", action="store_true",
                          help="Minimal flat JSON for agent consumption (implies --json)")
  p_context.set_defaults(func=cmd_context)

  # embed
  p_embed = sub.add_parser("embed", help="Backfill embeddings for memories without vectors", parents=[output_parser],
      epilog="Examples:\n  memori embed\n  memori embed --batch-size 100 --json",
      formatter_class=_F)
  p_embed.add_argument("--batch-size", type=int, default=50,
                        help="Number of memories to embed per batch (default: 50)")
  p_embed.set_defaults(func=cmd_embed)

  # export
  p_export = sub.add_parser("export", help="Export all memories as JSONL to stdout", parents=[output_parser],
      epilog="Examples:\n  memori export > backup.jsonl\n  memori export --include-vectors > full-backup.jsonl\n\nOutput is always JSONL (one JSON object per line), regardless of --json flag.",
      formatter_class=_F)
  p_export.add_argument("--include-vectors", action="store_true",
                         help="Include vectors in export (large, re-derivable)")
  p_export.set_defaults(func=cmd_export)

  # import
  p_import = sub.add_parser("import", help="Import memories from JSONL on stdin", parents=[output_parser],
      epilog="Examples:\n  memori import < backup.jsonl\n  memori import --new-ids < backup.jsonl\n  memori import --json < backup.jsonl",
      formatter_class=_F)
  p_import.add_argument("--new-ids", action="store_true",
                         help="Generate fresh IDs instead of preserving originals")
  p_import.set_defaults(func=cmd_import)

  # purge
  p_purge = sub.add_parser("purge", help="Bulk delete memories (dry-run by default)", parents=[output_parser],
      epilog="Examples:\n  memori purge --type temporary\n  memori purge --type scratch --json\n  memori purge --type temporary --confirm\n  memori purge --before 2025-01-01 --type debugging --confirm",
      formatter_class=_F)
  p_purge.add_argument("--before", help="Delete memories created before this ISO date")
  p_purge.add_argument("--type", help="Delete memories with this metadata type")
  p_purge.add_argument("--confirm", action="store_true",
                        help="Actually delete (default is dry-run preview)")
  p_purge.set_defaults(func=cmd_purge)

  # gc
  p_gc = sub.add_parser("gc", help="Compact database (SQLite VACUUM)", parents=[output_parser],
      epilog="Examples:\n  memori gc\n  memori gc --json",
      formatter_class=_F)
  p_gc.set_defaults(func=cmd_gc)

  # setup
  p_setup = sub.add_parser("setup", help="Configure Claude Code integration", parents=[output_parser],
      epilog="Examples:\n  memori setup\n  memori setup --show\n  memori setup --undo",
      formatter_class=_F)
  p_setup.add_argument("--show", action="store_true", help="Print snippet without writing")
  p_setup.add_argument("--undo", action="store_true", help="Remove the snippet")
  p_setup.set_defaults(func=cmd_setup)

  # ui
  p_ui = sub.add_parser("ui", help="Open web dashboard", parents=[output_parser],
      epilog="Examples:\n  memori ui\n  memori ui --port 9000 --no-open",
      formatter_class=_F)
  p_ui.add_argument("--port", type=int, default=8899, help="Server port (default: 8899)")
  p_ui.add_argument("--no-open", action="store_true", help="Don't auto-open browser")
  p_ui.set_defaults(func=cmd_ui)

  args = parser.parse_args()
  if args.raw:
    args.json = True
  args.func(args)


if __name__ == "__main__":
  main()
