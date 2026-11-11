"""Memori 2: Markdown knowledge, explicit links, and existing agent intelligence."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from memori import PyVault

__version__ = "2.0.0"


def _positive(value):
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("must be zero or greater")
    return number


def _emit(value, as_json):
    if as_json:
        print(json.dumps(value, ensure_ascii=False, indent=2))
    elif isinstance(value, dict) and "note" in value:
        note = value["note"]
        print(f"{note['id']}  {note['path']}\n\n{note['content']}")
        for label in ("outgoing", "backlinks"):
            if value.get(label):
                print(f"\n{label.title()}:")
                for neighbor in value[label]:
                    print(f"  {neighbor['id']}  {neighbor['path']}")
        for target in value.get("unresolved", []):
            print(f"  Unresolved: [[{target}]]")
    elif isinstance(value, dict) and "matches" in value:
        if not value["matches"]:
            print("No matches.")
        for hit in value["matches"]:
            note = hit["note"]
            score = f" [{hit['score']:.4f}]" if hit.get("score") is not None else ""
            print(f"{note['id']}{score}  {note['path']}\n  {note['content'][:240].replace(chr(10), ' ')}")
        if value["context"]:
            print("\nLinked context (one hop):")
            for hit in value["context"]:
                print(f"  {hit['note']['id']}  {hit['note']['path']}  via {hit['via']}")
    else:
        print(json.dumps(value, ensure_ascii=False, indent=2))


def _metadata(args):
    value = json.loads(args.meta) if getattr(args, "meta", None) else {}
    if not isinstance(value, dict):
        raise ValueError("--meta must be a JSON object")
    if getattr(args, "type", None):
        value["type"] = args.type
    if getattr(args, "tag", None):
        value["tags"] = args.tag
    return value


def _content(args):
    if args.file:
        return Path(args.file).read_text(encoding="utf-8")
    if args.content is None:
        return None
    return sys.stdin.read() if args.content == "-" else args.content


def cmd_init(args):
    root = Path(args.vault).expanduser().resolve()
    PyVault(str(root))
    ignore = root / ".gitignore"
    if ignore.is_symlink():
        raise ValueError("vault .gitignore must not be a symlink")
    existing = ignore.read_text() if ignore.exists() else ""
    additions = [line for line in (".memori/", ".fastembed_cache/") if line not in existing.splitlines()]
    if additions:
        ignore.write_text(existing + ("\n" if existing and not existing.endswith("\n") else "") + "\n".join(additions) + "\n")
    if not args.no_git:
        subprocess.run(["git", "init", "--quiet", str(root)], check=True)
    _emit({"vault": str(root), "git": not args.no_git}, args.json)


def _index_after_write(vault, args, path):
    try:
        return vault.index(embeddings=not args.text_only)
    except RuntimeError as error:
        raise RuntimeError(f"Markdown was saved at {path}, but indexing failed: {error}. Repair the vault and run memori index; the file write is retained.") from None


def cmd_add(args):
    vault = PyVault(str(Path(args.vault).expanduser()))
    note = vault.add(_content(args), metadata=_metadata(args))
    report = _index_after_write(vault, args, note["path"])
    _emit({"note": note, "index": report}, args.json)


def cmd_update(args):
    vault = PyVault(str(Path(args.vault).expanduser()))
    content = _content(args)
    meta = _metadata(args)
    if content is None and not meta:
        raise ValueError("provide --content, --file, --meta, --type or --tag")
    note = vault.update(args.id, content=content, metadata=meta or None)
    report = _index_after_write(vault, args, note["path"])
    _emit({"note": note, "index": report}, args.json)


def cmd_archive(args):
    vault = PyVault(str(Path(args.vault).expanduser()))
    path = vault.archive(args.id)
    report = _index_after_write(vault, args, path)
    _emit({"archived": path, "index": report}, args.json)


def cmd_index(args):
    report = PyVault(str(Path(args.vault).expanduser())).index(embeddings=not args.text_only)
    _emit(report, args.json)


def cmd_search(args):
    vault = PyVault(str(Path(args.vault).expanduser()))
    vault.index(embeddings=not args.text_only)
    result = vault.search(args.query, limit=args.limit, graph_limit=args.graph_limit,
                          text_only=args.text_only, filter={"type": args.type} if args.type else None,
                          min_similarity=args.min_similarity)
    _emit(result, args.json)


def cmd_show(args):
    vault = PyVault(str(Path(args.vault).expanduser()))
    vault.index(embeddings=False)
    _emit(vault.show(args.id, neighbor_limit=args.limit), args.json)


def _skill_text(name):
    return (Path(__file__).parent / "data" / name / "SKILL.md").read_text(encoding="utf-8")


def cmd_setup(args):
    root = Path(args.project).expanduser().resolve()
    base = root / (".agents" if args.agent == "codex" else ".claude") / "skills"
    paths = []
    for name in ("memori", "dream"):
        target = base / ("memori-dream" if name == "dream" else "memori") / "SKILL.md"
        if not target.resolve().is_relative_to(root):
            raise ValueError(f"skill installation would leave the project: {target}")
        content = _skill_text(name)
        if target.exists() and target.read_text() != content and not args.force:
            raise ValueError(f"{target} differs; inspect it or use --force to replace")
        paths.append((target, content))
    for target, content in paths:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    _emit({"agent": args.agent, "installed": [str(p) for p, _ in paths]}, args.json)


def cmd_dream(args):
    from .dream import run_dream
    result = run_dream(Path(args.vault).expanduser(), args.agent,
                       timeout=args.timeout, max_notes=args.max_notes, dry_run=args.dry_run)
    _emit(result, args.json)


def main():
    parser = argparse.ArgumentParser(description="Memori 2 — Markdown knowledge vault + hybrid search")
    parser.add_argument("--vault", default=os.environ.get("MEMORI_VAULT", "memory"), help="Vault directory (default: MEMORI_VAULT or ./memory)")
    parser.add_argument("--version", action="version", version=f"memori {__version__}")
    parser.add_argument("--json", action="store_true", help="JSON output; errors go to stderr")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("init", parents=[common], help="Create a vault, ignore its caches and initialize Git")
    p.add_argument("--no-git", action="store_true"); p.set_defaults(func=cmd_init)
    for name, function in (("add", cmd_add), ("update", cmd_update)):
        p = sub.add_parser(name, parents=[common], help="Write an atomic Markdown note" if name == "add" else "Edit a note by stable ID or unique prefix")
        if name == "update":
            p.add_argument("id")
        content = p.add_mutually_exclusive_group(required=name == "add")
        content.add_argument("content" if name == "add" else "--content", **({"nargs": "?"} if name == "add" else {}), help="Markdown body, or '-' for stdin")
        content.add_argument("--file", help="Read the Markdown body from a file")
        p.add_argument("--meta", help="JSON frontmatter fields")
        p.add_argument("--type", help="Note type, e.g. procedure, decision, fact")
        p.add_argument("--tag", action="append", help="Tag; repeat for multiple tags")
        p.add_argument("--text-only", action="store_true", help="Index without generating embeddings")
        p.set_defaults(func=function)
    p = sub.add_parser("archive", aliases=["delete"], parents=[common], help="Move the original note to archive/; preserve evidence")
    p.add_argument("id"); p.add_argument("--text-only", action="store_true"); p.set_defaults(func=cmd_archive)
    p = sub.add_parser("index", parents=[common], help="Rebuild/synchronize the disposable index from Markdown")
    p.add_argument("--text-only", action="store_true"); p.set_defaults(func=cmd_index)
    p = sub.add_parser("search", parents=[common], help="Hybrid recall with optional bounded linked context")
    p.add_argument("query"); p.add_argument("--limit", type=_positive, default=5)
    p.add_argument("--graph-limit", type=_positive, default=3, help="Total extra one-hop notes; 0 disables expansion")
    p.add_argument("--text-only", action="store_true"); p.add_argument("--type")
    p.add_argument("--min-similarity", type=float, help="Raw cosine floor; literal matches remain eligible")
    p.set_defaults(func=cmd_search)
    p = sub.add_parser("show", parents=[common], help="Read Markdown with links and derived backlinks")
    p.add_argument("id"); p.add_argument("--limit", type=_positive, default=5); p.set_defaults(func=cmd_show)
    p = sub.add_parser("setup", parents=[common], help="Install shared learning/dream skills for an agent in a project")
    p.add_argument("--agent", choices=["codex", "claude"], required=True)
    p.add_argument("--project", default="."); p.add_argument("--force", action="store_true"); p.set_defaults(func=cmd_setup)
    p = sub.add_parser("dream", parents=[common], help="Run bounded consolidation using an existing headless agent")
    p.add_argument("--agent", choices=["codex", "claude"], required=True)
    p.add_argument("--timeout", type=int, default=300, help="Maximum agent runtime in seconds")
    p.add_argument("--max-notes", type=int, default=20, help="Changed-note batch size")
    p.add_argument("--dry-run", action="store_true", help="Show candidates and the launcher command without starting an agent")
    p.set_defaults(func=cmd_dream)
    args = parser.parse_args()
    try:
        args.func(args)
    except (RuntimeError, ValueError, OSError, subprocess.SubprocessError) as error:
        if args.json:
            print(json.dumps({"error": type(error).__name__, "message": str(error)}), file=sys.stderr)
        else:
            print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
