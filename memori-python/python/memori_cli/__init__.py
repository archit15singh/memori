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
from datetime import datetime, timezone
from pathlib import Path

from memori import PyMemori

__version__ = "0.3.0"

DEFAULT_DB = os.path.expanduser("~/.claude/memori.db")
DEFAULT_DEDUP_THRESHOLD = 0.92

SNIPPET_START = "<!-- memori:start -->"
SNIPPET_END = "<!-- memori:end -->"


def _get_db(path=None):
  return PyMemori(path or DEFAULT_DB)


def _parse_json(value, flag_name):
  """Parse a JSON string from a CLI flag, exiting with a clean message on failure."""
  try:
    return json.loads(value)
  except json.JSONDecodeError as e:
    print(f"Invalid JSON for {flag_name}: {e}", file=sys.stderr)
    sys.exit(2)


def _snippet_text():
  """Load the CLAUDE.md snippet from bundled data."""
  data_dir = Path(__file__).parent / "data"
  snippet_file = data_dir / "claude_snippet.md"
  return snippet_file.read_text()


# -- Commands --


def cmd_store(args):
  db = _get_db(args.db)
  meta = _parse_json(args.meta, "--meta") if args.meta else None
  vector = _parse_json(args.vector, "--vector") if args.vector else None

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
  vector = _parse_json(args.vector, "--vector") if args.vector else None
  filt = _parse_json(args.filter, "--filter") if args.filter else None
  results = db.search(vector=vector, text=args.text, filter=filt, limit=args.limit)

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
      out.append(entry)
    print(json.dumps(out, indent=2, default=str))
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
    print(json.dumps(mem, indent=2, default=str))
  else:
    if args.json:
      print(json.dumps({"error": "not_found", "id": args.id}), file=sys.stderr)
    else:
      print(f"Not found: {args.id}", file=sys.stderr)
    sys.exit(1)


def cmd_update(args):
  db = _get_db(args.db)
  content = args.content
  meta = _parse_json(args.meta, "--meta") if args.meta else None
  vector = _parse_json(args.vector, "--vector") if args.vector else None

  if content is None and meta is None and vector is None:
    print("At least one of --content, --meta, or --vector is required.", file=sys.stderr)
    sys.exit(2)

  try:
    db.update(args.id, content=content, vector=vector, metadata=meta)
  except RuntimeError:
    if args.json:
      print(json.dumps({"error": "not_found", "id": args.id}), file=sys.stderr)
    else:
      print(f"Not found: {args.id}", file=sys.stderr)
    sys.exit(1)

  if args.json:
    print(json.dumps({"id": args.id, "status": "updated"}))
  else:
    print(f"Updated {args.id}")


def cmd_tag(args):
  db = _get_db(args.db)

  # Parse key=value pairs
  tags = {}
  for pair in args.tags:
    if "=" not in pair:
      print(f"Invalid tag format (expected key=value): {pair}", file=sys.stderr)
      sys.exit(2)
    k, v = pair.split("=", 1)
    tags[k] = v

  mem = db.get(args.id)
  if not mem:
    if args.json:
      print(json.dumps({"error": "not_found", "id": args.id}), file=sys.stderr)
    else:
      print(f"Not found: {args.id}", file=sys.stderr)
    sys.exit(1)

  existing = mem.get("metadata") or {}
  merged = {**existing, **tags}
  db.update(args.id, metadata=merged)

  if args.json:
    print(json.dumps(merged, indent=2))
  else:
    print(f"Tagged {args.id}: {merged}")


def cmd_context(args):
  db = _get_db(args.db)
  topic = args.topic
  limit = args.limit

  # Relevant matches
  matches = db.search(text=topic, limit=limit)
  # Recent memories (no query = returns by recency)
  recent = db.search(limit=5)
  # Type distribution
  type_dist = db.type_distribution()
  total = db.count()

  if args.json:
    out = {
      "topic": topic,
      "matches": [
        {"id": r["id"], "content": r["content"], "score": r.get("score"),
         "metadata": r.get("metadata"), "created_at": r.get("created_at")}
        for r in matches
      ],
      "recent": [
        {"id": r["id"], "content": r["content"], "metadata": r.get("metadata"),
         "created_at": r.get("created_at")}
        for r in recent
      ],
      "types": type_dist,
      "total": total,
    }
    print(json.dumps(out, indent=2, default=str))
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

    print(f"\n## Recent Memories\n")
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
  results = db.search(limit=1_000_000)

  for r in results:
    entry = {
      "id": r["id"],
      "content": r["content"],
      "metadata": r.get("metadata"),
      "created_at": r.get("created_at"),
      "updated_at": r.get("updated_at"),
      "vector": r.get("vector") if include_vectors else None,
    }
    print(json.dumps(entry, default=str))


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

      if new_ids:
        db.insert(content, vector=vector, metadata=metadata, no_embed=False)
      else:
        db.insert_with_id(
          entry["id"], content,
          vector=vector, metadata=metadata,
          created_at=created_at, updated_at=updated_at,
        )
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
    print("At least one of --before or --type is required.", file=sys.stderr)
    sys.exit(2)

  before_ts = None
  if args.before:
    try:
      dt = datetime.fromisoformat(args.before)
      if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
      before_ts = dt.timestamp()
    except ValueError as e:
      print(f"Invalid date format for --before: {e}", file=sys.stderr)
      sys.exit(2)

  if args.confirm:
    # Actually delete
    total_deleted = 0
    if before_ts is not None:
      total_deleted += db.delete_before(before_ts)
    if args.type:
      total_deleted += db.delete_by_type(args.type)

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
    # Dry-run: preview what would be deleted
    # Count matches for each criterion
    preview_count = 0
    preview_items = []

    all_results = db.search(limit=1_000_000)
    for r in all_results:
      match = False
      if before_ts is not None and r.get("created_at", float("inf")) < before_ts:
        match = True
      if args.type:
        meta = r.get("metadata")
        if meta and isinstance(meta, dict) and meta.get("type") == args.type:
          match = True
      if match:
        preview_count += 1
        if len(preview_items) < 10:
          preview_items.append(r)

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
        for r in preview_items:
          content = r["content"][:80] + ("..." if len(r["content"]) > 80 else "")
          print(f"  {r['id'][:8]} {content}")
      print("\nRe-run with --confirm to delete.")


def cmd_delete(args):
  db = _get_db(args.db)
  try:
    db.delete(args.id)
  except RuntimeError:
    if args.json:
      print(json.dumps({"error": "not_found", "id": args.id}), file=sys.stderr)
    else:
      print(f"Not found: {args.id}", file=sys.stderr)
    sys.exit(1)
  if args.json:
    print(json.dumps({"id": args.id, "status": "deleted"}))
  else:
    print(f"Deleted {args.id}")


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
    }, indent=2))
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

  if args.undo:
    if SNIPPET_START not in content:
      print("No memori snippet found -- nothing to remove.")
      return
    # Remove everything between markers (inclusive)
    start_idx = content.index(SNIPPET_START)
    end_idx = content.index(SNIPPET_END) + len(SNIPPET_END)
    # Also remove trailing newline if present
    if end_idx < len(content) and content[end_idx] == "\n":
      end_idx += 1
    content = content[:start_idx] + content[end_idx:]
    target.write_text(content)
    print(f"Removed memori snippet from {target}")
    return

  if SNIPPET_START in content:
    print(f"Memori snippet already present in {target}")
    return

  snippet = _snippet_text()
  # Append with a blank line separator
  separator = "\n" if content and not content.endswith("\n") else ""
  separator += "\n" if content else ""
  content += separator + snippet
  target.write_text(content)
  print(f"Added memori snippet to {target}")


# -- Main --


def main():
  parser = argparse.ArgumentParser(
    prog="memori",
    description="Memori -- embedded AI agent memory (SQLite + vector search + FTS5)",
  )
  parser.add_argument("--db", help=f"Database path (default: {DEFAULT_DB})")
  parser.add_argument("--json", action="store_true", help="Machine-readable JSON output")
  parser.add_argument(
    "--version", action="version",
    version=f"memori {__version__}",
  )

  sub = parser.add_subparsers(dest="command", required=True)

  # store
  p_store = sub.add_parser("store", help="Store a memory")
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
  p_search = sub.add_parser("search", help="Search memories")
  p_search.add_argument("--text", help="Text query (FTS5)")
  p_search.add_argument("--vector", help="Vector query (JSON float array)")
  p_search.add_argument("--filter", help="Metadata filter (JSON object)")
  p_search.add_argument("--limit", type=int, default=5)
  p_search.set_defaults(func=cmd_search)

  # get
  p_get = sub.add_parser("get", help="Get memory by ID")
  p_get.add_argument("id")
  p_get.set_defaults(func=cmd_get)

  # update
  p_update = sub.add_parser("update", help="Update an existing memory")
  p_update.add_argument("id", help="Memory ID to update")
  p_update.add_argument("--content", help="New text content")
  p_update.add_argument("--meta", help="New metadata (JSON object, replaces existing)")
  p_update.add_argument("--vector", help="New vector (JSON float array)")
  p_update.set_defaults(func=cmd_update)

  # tag
  p_tag = sub.add_parser("tag", help="Add key=value tags to memory metadata")
  p_tag.add_argument("id", help="Memory ID to tag")
  p_tag.add_argument("tags", nargs="+", help="Tags as key=value pairs")
  p_tag.set_defaults(func=cmd_tag)

  # delete
  p_del = sub.add_parser("delete", help="Delete memory by ID")
  p_del.add_argument("id")
  p_del.set_defaults(func=cmd_delete)

  # count
  p_count = sub.add_parser("count", help="Count memories")
  p_count.set_defaults(func=cmd_count)

  # stats
  p_stats = sub.add_parser("stats", help="Show database stats")
  p_stats.set_defaults(func=cmd_stats)

  # context
  p_context = sub.add_parser("context", help="Load relevant context for a topic")
  p_context.add_argument("topic", help="Topic to search for")
  p_context.add_argument("--limit", type=int, default=10, help="Max relevant matches")
  p_context.set_defaults(func=cmd_context)

  # embed
  p_embed = sub.add_parser("embed", help="Backfill embeddings for memories without vectors")
  p_embed.add_argument("--batch-size", type=int, default=50,
                        help="Number of memories to embed per batch (default: 50)")
  p_embed.set_defaults(func=cmd_embed)

  # export
  p_export = sub.add_parser("export", help="Export all memories as JSONL to stdout")
  p_export.add_argument("--include-vectors", action="store_true",
                         help="Include vectors in export (large, re-derivable)")
  p_export.set_defaults(func=cmd_export)

  # import
  p_import = sub.add_parser("import", help="Import memories from JSONL on stdin")
  p_import.add_argument("--new-ids", action="store_true",
                         help="Generate fresh IDs instead of preserving originals")
  p_import.set_defaults(func=cmd_import)

  # purge
  p_purge = sub.add_parser("purge", help="Bulk delete memories (dry-run by default)")
  p_purge.add_argument("--before", help="Delete memories created before this ISO date")
  p_purge.add_argument("--type", help="Delete memories with this metadata type")
  p_purge.add_argument("--confirm", action="store_true",
                        help="Actually delete (default is dry-run preview)")
  p_purge.set_defaults(func=cmd_purge)

  # setup
  p_setup = sub.add_parser("setup", help="Configure Claude Code integration")
  p_setup.add_argument("--show", action="store_true", help="Print snippet without writing")
  p_setup.add_argument("--undo", action="store_true", help="Remove the snippet")
  p_setup.set_defaults(func=cmd_setup)

  args = parser.parse_args()
  args.func(args)


if __name__ == "__main__":
  main()
