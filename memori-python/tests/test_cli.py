"""Comprehensive CLI integration tests for the memori command-line tool.

Runs the actual `memori` binary via subprocess against fresh temp databases.
Tests all 18+ subcommands and verifies exit codes, output formats, and
behavioral correctness (typed tags, no access inflation, purge AND logic).
"""

import json
import os
import subprocess
import shutil
import sys
import time

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _memori_bin():
    """Return the path to the memori binary."""
    path = shutil.which("memori")
    if path:
        return path
    # Fallback: look next to sys.executable (in same venv)
    venv_bin = os.path.join(os.path.dirname(sys.executable), "memori")
    if os.path.exists(venv_bin):
        return venv_bin
    raise RuntimeError("memori binary not found on PATH")


MEMORI_BIN = _memori_bin()


def run_memori(*args, db_path=None, stdin=None, env_extra=None):
    """Run memori CLI and return CompletedProcess."""
    cmd = [MEMORI_BIN]
    if db_path:
        cmd.extend(["--db", str(db_path)])
    cmd.extend(str(a) for a in args)
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        cmd, capture_output=True, text=True, input=stdin, timeout=120, env=env,
    )


def store_memory(db_path, content, meta=None, no_embed=False, no_dedup=False, extra_args=None):
    """Store a memory and return the parsed JSON result."""
    args = ["--json", "store", content]
    if meta:
        args.extend(["--meta", json.dumps(meta)])
    if no_embed:
        args.append("--no-embed")
    if no_dedup:
        args.append("--no-dedup")
    if extra_args:
        args.extend(extra_args)
    result = run_memori(*args, db_path=db_path)
    assert result.returncode == 0, f"store failed: {result.stderr}"
    return json.loads(result.stdout)


def get_memory_json(db_path, mem_id):
    """Get a memory by ID in JSON format."""
    result = run_memori("--json", "get", mem_id, db_path=db_path)
    if result.returncode != 0:
        return None
    return json.loads(result.stdout)


@pytest.fixture
def db(tmp_path):
    """Return a path to a fresh temp database."""
    return str(tmp_path / "test.db")


# ---------------------------------------------------------------------------
# STORE
# ---------------------------------------------------------------------------


class TestStore:
    def test_store_plain(self, db):
        r = run_memori("store", "hello world", "--no-embed", db_path=db)
        assert r.returncode == 0
        assert "Stored:" in r.stdout

    def test_store_json(self, db):
        r = run_memori("--json", "store", "hello", "--no-embed", db_path=db)
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert "id" in out
        assert out["status"] == "created"

    def test_store_raw(self, db):
        r = run_memori("--raw", "store", "hello", "--no-embed", db_path=db)
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert "id" in out
        # raw = single line
        assert "\n" not in r.stdout.strip()

    def test_store_with_meta(self, db):
        r = store_memory(db, "with meta", meta={"type": "fact", "topic": "test"}, no_embed=True)
        assert r["status"] == "created"
        mem = get_memory_json(db, r["id"])
        assert mem["metadata"]["type"] == "fact"
        assert mem["metadata"]["topic"] == "test"

    def test_store_unknown_type_warning(self, db):
        r = run_memori(
            "store", "unknown type test",
            "--meta", '{"type": "banana"}',
            "--no-embed", db_path=db,
        )
        assert r.returncode == 0
        assert "Warning: unknown type 'banana'" in r.stderr

    def test_store_dedup(self, db):
        # Store two similar memories (same vector, same type) -- should dedup
        r1 = run_memori(
            "--json", "store", "kafka architecture",
            "--vector", "[1.0, 0.0, 0.0]",
            "--meta", '{"type": "architecture"}',
            db_path=db,
        )
        assert r1.returncode == 0
        out1 = json.loads(r1.stdout)
        assert out1["status"] == "created"

        r2 = run_memori(
            "--json", "store", "kafka arch notes",
            "--vector", "[0.99, 0.01, 0.0]",
            "--meta", '{"type": "architecture"}',
            db_path=db,
        )
        assert r2.returncode == 0
        out2 = json.loads(r2.stdout)
        assert out2["status"] == "deduplicated"
        assert out2["id"] == out1["id"]

    def test_store_no_dedup(self, db):
        r1 = store_memory(db, "kafka architecture", no_embed=True)
        r2 = run_memori(
            "--json", "store", "kafka architecture",
            "--no-embed", "--no-dedup",
            db_path=db,
        )
        assert r2.returncode == 0
        out2 = json.loads(r2.stdout)
        assert out2["status"] == "created"
        assert out2["id"] != r1["id"]

    def test_store_no_embed(self, db):
        r = store_memory(db, "no embed test", no_embed=True)
        # get without --include-vectors strips vector key entirely; use it to verify null
        result = run_memori("get", r["id"], "--include-vectors", db_path=db)
        mem = json.loads(result.stdout)
        assert mem["vector"] is None

    def test_store_invalid_meta(self, db):
        r = run_memori(
            "--json", "store", "bad meta",
            "--meta", "{not valid json}",
            "--no-embed", db_path=db,
        )
        assert r.returncode == 2
        err = json.loads(r.stderr)
        assert err["error"] == "invalid_json"


# ---------------------------------------------------------------------------
# SEARCH
# ---------------------------------------------------------------------------


class TestSearch:
    def test_search_text_plain(self, db):
        store_memory(db, "the quick brown fox", no_embed=True)
        store_memory(db, "a red car", no_embed=True)
        r = run_memori("search", "--text", "brown", "--text-only", db_path=db)
        assert r.returncode == 0
        assert "brown fox" in r.stdout

    def test_search_text_json(self, db):
        store_memory(db, "the quick brown fox", no_embed=True)
        r = run_memori("--json", "search", "--text", "brown", "--text-only", db_path=db)
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert isinstance(out, list)
        assert len(out) > 0
        assert "brown" in out[0]["content"]

    def test_search_text_raw(self, db):
        store_memory(db, "the quick brown fox", no_embed=True)
        r = run_memori("--raw", "search", "--text", "brown", "--text-only", db_path=db)
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert isinstance(out, list)
        # raw = compact single line
        assert "\n" not in r.stdout.strip()

    def test_search_with_filter(self, db):
        store_memory(db, "a fact", meta={"type": "fact"}, no_embed=True)
        store_memory(db, "a preference", meta={"type": "preference"}, no_embed=True)
        r = run_memori(
            "--json", "search",
            "--filter", '{"type": "fact"}',
            db_path=db,
        )
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert len(out) == 1
        assert out[0]["metadata"]["type"] == "fact"

    def test_search_with_limit(self, db):
        for i in range(5):
            store_memory(db, f"memory {i}", no_embed=True)
        r = run_memori("--json", "search", "--limit", "2", db_path=db)
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert len(out) <= 2

    def test_search_text_only(self, db):
        store_memory(db, "kafka partitioned topics", no_embed=True)
        store_memory(db, "redis caching layer", no_embed=True)
        r = run_memori(
            "--json", "search", "--text", "kafka", "--text-only",
            db_path=db,
        )
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert len(out) == 1
        assert "kafka" in out[0]["content"]

    def test_search_before_after(self, db):
        # Store with auto timestamps (both will be "now")
        store_memory(db, "recent memory", no_embed=True)
        # Search --before tomorrow should find it, --after tomorrow should not
        tomorrow = "2099-01-01"
        yesterday = "2000-01-01"
        r = run_memori(
            "--json", "search", "--before", tomorrow,
            db_path=db,
        )
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert len(out) >= 1

        r2 = run_memori(
            "--json", "search", "--after", tomorrow,
            db_path=db,
        )
        assert r2.returncode == 0
        out2 = json.loads(r2.stdout)
        assert len(out2) == 0

    def test_search_include_vectors(self, db):
        store_memory(db, "vector test", extra_args=["--vector", "[1.0, 0.0, 0.0]"])
        r = run_memori(
            "--json", "search", "--include-vectors",
            db_path=db,
        )
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert len(out) > 0
        # vectors should be present
        assert out[0].get("vector") is not None

    def test_search_bad_date(self, db):
        r = run_memori(
            "--json", "search", "--before", "not-a-date",
            db_path=db,
        )
        assert r.returncode == 2

    def test_search_no_args_returns_all(self, db):
        for i in range(3):
            store_memory(db, f"item {i}", no_embed=True)
        r = run_memori("--json", "search", db_path=db)
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert len(out) == 3

    def test_search_default_limit_is_10(self, db):
        for i in range(15):
            store_memory(db, f"memory number {i}", no_embed=True)
        r = run_memori("--json", "search", db_path=db)
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert len(out) == 10


# ---------------------------------------------------------------------------
# GET
# ---------------------------------------------------------------------------


class TestGet:
    def test_get_existing(self, db):
        stored = store_memory(db, "hello", no_embed=True)
        r = run_memori("get", stored["id"], db_path=db)
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert out["content"] == "hello"

    def test_get_prefix(self, db):
        stored = store_memory(db, "prefix test", no_embed=True)
        prefix = stored["id"][:8]
        r = run_memori("get", prefix, db_path=db)
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert out["content"] == "prefix test"
        assert out["id"] == stored["id"]

    def test_get_not_found(self, db):
        # need to create the DB file first
        store_memory(db, "seed", no_embed=True)
        r = run_memori("get", "nonexistent-id", db_path=db)
        assert r.returncode == 1
        assert "Not found" in r.stderr

    def test_get_not_found_json(self, db):
        store_memory(db, "seed", no_embed=True)
        r = run_memori("--json", "get", "nonexistent-id", db_path=db)
        assert r.returncode == 1
        err = json.loads(r.stderr)
        assert err["error"] == "not_found"

    def test_get_include_vectors(self, db):
        stored = store_memory(db, "with vec", extra_args=["--vector", "[1.0, 2.0, 3.0]"])
        r = run_memori("get", stored["id"], "--include-vectors", db_path=db)
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert out["vector"] is not None
        assert len(out["vector"]) == 3


# ---------------------------------------------------------------------------
# UPDATE
# ---------------------------------------------------------------------------


class TestUpdate:
    def test_update_content(self, db):
        stored = store_memory(db, "original", no_embed=True)
        r = run_memori(
            "--json", "update", stored["id"],
            "--content", "updated text",
            db_path=db,
        )
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert out["status"] == "updated"

        mem = get_memory_json(db, stored["id"])
        assert mem["content"] == "updated text"

    def test_update_meta_merge(self, db):
        stored = store_memory(db, "merge test", meta={"a": 1}, no_embed=True)
        r = run_memori(
            "--json", "update", stored["id"],
            "--meta", '{"b": 2}',
            db_path=db,
        )
        assert r.returncode == 0
        mem = get_memory_json(db, stored["id"])
        assert mem["metadata"]["a"] == 1
        assert mem["metadata"]["b"] == 2

    def test_update_meta_replace(self, db):
        stored = store_memory(db, "replace test", meta={"a": 1, "c": 3}, no_embed=True)
        r = run_memori(
            "--json", "update", stored["id"],
            "--meta", '{"b": 2}', "--replace",
            db_path=db,
        )
        assert r.returncode == 0
        mem = get_memory_json(db, stored["id"])
        assert mem["metadata"] == {"b": 2}
        assert "a" not in mem["metadata"]

    def test_update_not_found(self, db):
        store_memory(db, "seed", no_embed=True)
        r = run_memori(
            "--json", "update", "nonexistent-id",
            "--content", "fail",
            db_path=db,
        )
        assert r.returncode == 1

    def test_update_no_args_error(self, db):
        stored = store_memory(db, "nothing to update", no_embed=True)
        r = run_memori(
            "--json", "update", stored["id"],
            db_path=db,
        )
        assert r.returncode == 2

    def test_update_no_access_inflation(self, db):
        """Updating a memory should not inflate its access_count."""
        stored = store_memory(db, "inflation test", no_embed=True)
        mid = stored["id"]

        # Update content
        run_memori("update", mid, "--content", "new content", db_path=db)

        # get_readonly check via CLI (--json get bumps access, so we check
        # the value _returned_ by get, which shows the pre-bump snapshot)
        r = run_memori("--json", "get", mid, db_path=db)
        out = json.loads(r.stdout)
        # The first get() sees access_count=0 because the update used get_readonly
        assert out["access_count"] == 0


# ---------------------------------------------------------------------------
# TAG
# ---------------------------------------------------------------------------


class TestTag:
    def test_tag_string(self, db):
        stored = store_memory(db, "tag test", no_embed=True)
        r = run_memori("tag", stored["id"], "topic=kafka", db_path=db)
        assert r.returncode == 0
        assert "kafka" in r.stdout

    def test_tag_integer(self, db):
        """Tag values should be typed -- int stays int, not string."""
        stored = store_memory(db, "typed tag test", no_embed=True)
        r = run_memori("--json", "tag", stored["id"], "count=42", db_path=db)
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert out["count"] == 42
        assert isinstance(out["count"], int)

    def test_tag_float(self, db):
        stored = store_memory(db, "float tag test", no_embed=True)
        r = run_memori("--json", "tag", stored["id"], "score=3.14", db_path=db)
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert abs(out["score"] - 3.14) < 0.001
        assert isinstance(out["score"], float)

    def test_tag_boolean(self, db):
        stored = store_memory(db, "bool tag test", no_embed=True)
        r = run_memori("--json", "tag", stored["id"], "verified=true", "active=false", db_path=db)
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert out["verified"] is True
        assert out["active"] is False

    def test_tag_json_output(self, db):
        stored = store_memory(db, "json tag", meta={"existing": "yes"}, no_embed=True)
        r = run_memori("--json", "tag", stored["id"], "new=value", db_path=db)
        assert r.returncode == 0
        out = json.loads(r.stdout)
        # Merged result should have both old and new
        assert out["existing"] == "yes"
        assert out["new"] == "value"

    def test_tag_not_found(self, db):
        store_memory(db, "seed", no_embed=True)
        r = run_memori("--json", "tag", "nonexistent-id", "key=val", db_path=db)
        assert r.returncode == 1

    def test_tag_bad_format(self, db):
        stored = store_memory(db, "bad tag", no_embed=True)
        r = run_memori("--json", "tag", stored["id"], "noequals", db_path=db)
        assert r.returncode == 2

    def test_tag_no_access_inflation(self, db):
        """Tagging should not inflate access_count."""
        stored = store_memory(db, "tag inflation test", no_embed=True)
        mid = stored["id"]

        # Tag multiple times
        run_memori("tag", mid, "a=1", db_path=db)
        run_memori("tag", mid, "b=2", db_path=db)

        # First get sees pre-bump value
        r = run_memori("--json", "get", mid, db_path=db)
        out = json.loads(r.stdout)
        assert out["access_count"] == 0, (
            f"access_count should be 0 after tag operations, got {out['access_count']}"
        )


# ---------------------------------------------------------------------------
# LIST
# ---------------------------------------------------------------------------


class TestList:
    def test_list_plain(self, db):
        store_memory(db, "item one", no_embed=True)
        store_memory(db, "item two", no_embed=True)
        r = run_memori("list", db_path=db)
        assert r.returncode == 0
        assert "item one" in r.stdout
        assert "item two" in r.stdout

    def test_list_json(self, db):
        store_memory(db, "listed item", meta={"type": "fact"}, no_embed=True)
        r = run_memori("--json", "list", db_path=db)
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert isinstance(out, list)
        assert len(out) == 1
        assert out[0]["metadata"]["type"] == "fact"

    def test_list_raw(self, db):
        store_memory(db, "raw item", no_embed=True)
        r = run_memori("--raw", "list", db_path=db)
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert isinstance(out, list)
        assert "\n" not in r.stdout.strip()

    def test_list_type_filter(self, db):
        store_memory(db, "a fact", meta={"type": "fact"}, no_embed=True)
        store_memory(db, "a pref", meta={"type": "preference"}, no_embed=True)
        r = run_memori("--json", "list", "--type", "fact", db_path=db)
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert len(out) == 1
        assert out[0]["metadata"]["type"] == "fact"

    def test_list_sort_options(self, db):
        s1 = store_memory(db, "first", no_embed=True)
        s2 = store_memory(db, "second", no_embed=True)

        # Sort by created (DESC) -- second should come first
        r = run_memori("--json", "list", "--sort", "created", db_path=db)
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert out[0]["id"] == s2["id"]
        assert out[1]["id"] == s1["id"]

    def test_list_limit_offset(self, db):
        ids = []
        for i in range(5):
            ids.append(store_memory(db, f"item {i}", no_embed=True)["id"])

        r = run_memori("--json", "list", "--limit", "2", "--offset", "0", db_path=db)
        assert r.returncode == 0
        page1 = json.loads(r.stdout)
        assert len(page1) == 2

        r2 = run_memori("--json", "list", "--limit", "2", "--offset", "2", db_path=db)
        assert r2.returncode == 0
        page2 = json.loads(r2.stdout)
        assert len(page2) == 2

        page1_ids = {m["id"] for m in page1}
        page2_ids = {m["id"] for m in page2}
        assert page1_ids.isdisjoint(page2_ids)

    def test_list_before_after(self, db):
        store_memory(db, "now memory", no_embed=True)
        r = run_memori(
            "--json", "list", "--before", "2099-01-01",
            db_path=db,
        )
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert len(out) >= 1

        r2 = run_memori(
            "--json", "list", "--after", "2099-01-01",
            db_path=db,
        )
        assert r2.returncode == 0
        out2 = json.loads(r2.stdout)
        assert len(out2) == 0

    def test_list_include_vectors(self, db):
        store_memory(db, "vec item", extra_args=["--vector", "[1.0, 2.0]"])
        r = run_memori("--json", "list", "--include-vectors", db_path=db)
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert out[0].get("vector") is not None

    def test_list_empty(self, db):
        r = run_memori("list", db_path=db)
        assert r.returncode == 0
        assert "No memories found" in r.stdout


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------


class TestDelete:
    def test_delete_existing(self, db):
        stored = store_memory(db, "to delete", no_embed=True)
        r = run_memori("delete", stored["id"], db_path=db)
        assert r.returncode == 0
        assert "Deleted" in r.stdout

    def test_delete_json(self, db):
        stored = store_memory(db, "to delete", no_embed=True)
        r = run_memori("--json", "delete", stored["id"], db_path=db)
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert out["status"] == "deleted"
        assert out["id"] == stored["id"]

    def test_delete_not_found(self, db):
        store_memory(db, "seed", no_embed=True)
        r = run_memori("delete", "nonexistent-id", db_path=db)
        assert r.returncode == 1
        assert "Not found" in r.stderr


# ---------------------------------------------------------------------------
# COUNT
# ---------------------------------------------------------------------------


class TestCount:
    def test_count_plain(self, db):
        store_memory(db, "one", no_embed=True)
        store_memory(db, "two", no_embed=True)
        r = run_memori("count", db_path=db)
        assert r.returncode == 0
        assert r.stdout.strip() == "2"

    def test_count_json(self, db):
        store_memory(db, "one", no_embed=True)
        r = run_memori("--json", "count", db_path=db)
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert out["count"] == 1

    def test_count_empty_db(self, db):
        r = run_memori("count", db_path=db)
        assert r.returncode == 0
        assert r.stdout.strip() == "0"

    def test_count_empty_db_json(self, db):
        r = run_memori("--json", "count", db_path=db)
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert out["count"] == 0


# ---------------------------------------------------------------------------
# STATS
# ---------------------------------------------------------------------------


class TestStats:
    def test_stats_plain(self, db):
        store_memory(db, "a fact", meta={"type": "fact"}, no_embed=True)
        r = run_memori("stats", db_path=db)
        assert r.returncode == 0
        assert "Memories:" in r.stdout
        assert "File size:" in r.stdout
        assert "fact:" in r.stdout

    def test_stats_json(self, db):
        store_memory(db, "a fact", meta={"type": "fact"}, no_embed=True)
        r = run_memori("--json", "stats", db_path=db)
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert out["count"] == 1
        assert "file_size" in out
        assert out["types"]["fact"] == 1
        assert "embedded" in out


# ---------------------------------------------------------------------------
# CONTEXT
# ---------------------------------------------------------------------------


class TestContext:
    def test_context_plain(self, db):
        store_memory(db, "kafka architecture notes", meta={"type": "architecture"}, no_embed=True)
        r = run_memori("context", "kafka", db_path=db)
        assert r.returncode == 0
        assert "Relevant Memories" in r.stdout

    def test_context_json(self, db):
        store_memory(db, "kafka arch", meta={"type": "architecture"}, no_embed=True)
        r = run_memori("--json", "context", "kafka", db_path=db)
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert "matches" in out
        assert "recent" in out
        assert "total" in out
        assert out["total"] >= 1

    def test_context_raw(self, db):
        store_memory(db, "test context raw", no_embed=True)
        r = run_memori("--raw", "context", "test", db_path=db)
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert "matches" in out

    def test_context_compact(self, db):
        store_memory(db, "compact mode test", meta={"type": "fact"}, no_embed=True)
        r = run_memori("context", "compact", "--compact", db_path=db)
        assert r.returncode == 0
        out = json.loads(r.stdout)
        # Compact returns flat JSON with truncated IDs and minimal fields
        assert "matches" in out
        assert "total" in out
        assert "recent" in out
        # Compact entries should have short IDs
        if out["matches"]:
            assert len(out["matches"][0]["id"]) == 8

    def test_context_with_limit(self, db):
        for i in range(5):
            store_memory(db, f"context item {i}", no_embed=True)
        r = run_memori("--json", "context", "item", "--limit", "2", db_path=db)
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert len(out["matches"]) <= 2


# ---------------------------------------------------------------------------
# RELATED
# ---------------------------------------------------------------------------


class TestRelated:
    def test_related_existing(self, db):
        """Related requires vectors -- store with auto-embed."""
        s1 = store_memory(db, "kafka message queue architecture")
        s2 = store_memory(db, "rabbitmq message broker design")
        s3 = store_memory(db, "python unittest framework")

        r = run_memori("--json", "related", s1["id"], db_path=db)
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert isinstance(out, list)
        # Should find related memories (self excluded)
        result_ids = [m["id"] for m in out]
        assert s1["id"] not in result_ids

    def test_related_json(self, db):
        s1 = store_memory(db, "kubernetes deployment patterns")
        store_memory(db, "docker container orchestration")
        r = run_memori("--json", "related", s1["id"], db_path=db)
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert isinstance(out, list)
        if out:
            assert "score" in out[0]
            assert "content" in out[0]

    def test_related_not_found(self, db):
        store_memory(db, "seed", no_embed=True)
        r = run_memori("related", "nonexistent-id", db_path=db)
        assert r.returncode == 1

    def test_related_with_limit(self, db):
        s1 = store_memory(db, "main topic here")
        for i in range(4):
            store_memory(db, f"related topic number {i}")
        r = run_memori("--json", "related", s1["id"], "--limit", "2", db_path=db)
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert len(out) <= 2


# ---------------------------------------------------------------------------
# EMBED
# ---------------------------------------------------------------------------


class TestEmbed:
    def test_embed_when_needed(self, db):
        """Store with --no-embed, then backfill."""
        store_memory(db, "needs embedding", no_embed=True)
        r = run_memori("--json", "embed", db_path=db)
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert out["embedded"] >= 1

    def test_embed_already_done(self, db):
        """Store with auto-embed, then embed should skip."""
        store_memory(db, "already embedded")
        r = run_memori("--json", "embed", db_path=db)
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert out["embedded"] == 0
        assert out["skipped"] >= 1

    def test_embed_json(self, db):
        store_memory(db, "embed test", no_embed=True)
        r = run_memori("--json", "embed", db_path=db)
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert "embedded" in out
        assert "total" in out
        assert "skipped" in out


# ---------------------------------------------------------------------------
# EXPORT
# ---------------------------------------------------------------------------


class TestExport:
    def test_export_basic(self, db):
        store_memory(db, "export item 1", meta={"type": "fact"}, no_embed=True)
        store_memory(db, "export item 2", no_embed=True)
        r = run_memori("export", db_path=db)
        assert r.returncode == 0
        lines = [l for l in r.stdout.strip().split("\n") if l]
        assert len(lines) == 2
        for line in lines:
            obj = json.loads(line)
            assert "id" in obj
            assert "content" in obj

    def test_export_include_vectors(self, db):
        store_memory(db, "with vector", extra_args=["--vector", "[1.0, 0.0]"])
        r = run_memori("export", "--include-vectors", db_path=db)
        assert r.returncode == 0
        obj = json.loads(r.stdout.strip())
        assert obj["vector"] is not None


# ---------------------------------------------------------------------------
# IMPORT
# ---------------------------------------------------------------------------


class TestImport:
    def test_import_basic(self, db):
        # Export from one DB, import to another
        store_memory(db, "importable", meta={"type": "fact"}, no_embed=True)
        export_r = run_memori("export", db_path=db)
        assert export_r.returncode == 0

        db2 = db.replace("test.db", "import-target.db")
        r = run_memori("--json", "import", db_path=db2, stdin=export_r.stdout)
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert out["imported"] == 1
        assert out["errors"] == 0

        # Verify it landed
        r2 = run_memori("--json", "count", db_path=db2)
        count = json.loads(r2.stdout)["count"]
        assert count == 1

    def test_import_new_ids(self, db):
        store_memory(db, "original id", no_embed=True)
        export_r = run_memori("export", db_path=db)
        original_id = json.loads(export_r.stdout.strip())["id"]

        db2 = db.replace("test.db", "import-new-ids.db")
        r = run_memori("--json", "import", "--new-ids", db_path=db2, stdin=export_r.stdout)
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert out["imported"] == 1

        # The imported memory should have a different ID
        r2 = run_memori("--json", "list", db_path=db2)
        items = json.loads(r2.stdout)
        assert len(items) == 1
        assert items[0]["id"] != original_id

    def test_import_bad_line(self, db):
        # Good line needs an "id" field for non --new-ids import
        good = json.dumps({"id": "aaaa1111-0000-0000-0000-000000000001", "content": "good line"})
        bad_input = good + "\nnot json at all\n"
        r = run_memori("--json", "import", db_path=db, stdin=bad_input)
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert out["imported"] == 1
        assert out["errors"] == 1


# ---------------------------------------------------------------------------
# PURGE
# ---------------------------------------------------------------------------


class TestPurge:
    def test_purge_dry_run(self, db):
        store_memory(db, "temp item", meta={"type": "temporary"}, no_embed=True)
        r = run_memori("purge", "--type", "temporary", db_path=db)
        assert r.returncode == 0
        assert "Would delete" in r.stdout
        assert "1" in r.stdout
        # Dry run -- memory should still exist
        r2 = run_memori("--json", "count", db_path=db)
        assert json.loads(r2.stdout)["count"] == 1

    def test_purge_confirm(self, db):
        store_memory(db, "temp to purge", meta={"type": "temporary"}, no_embed=True)
        store_memory(db, "keep this", meta={"type": "fact"}, no_embed=True)
        r = run_memori(
            "--json", "purge", "--type", "temporary", "--confirm",
            db_path=db,
        )
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert out["action"] == "deleted"
        assert out["count"] == 1

        r2 = run_memori("--json", "count", db_path=db)
        assert json.loads(r2.stdout)["count"] == 1  # only fact remains

    def test_purge_before_and_type_and_logic(self, db):
        """Purge with both --before and --type uses AND logic (intersection).

        Create 4 memories:
        - old + temporary: should be purged
        - old + fact: should NOT be purged (wrong type)
        - new + temporary: should NOT be purged (too recent)
        - new + fact: should NOT be purged (wrong type + too recent)
        """
        from memori import PyMemori
        pydb = PyMemori(db)
        old_ts = time.time() - 86400 * 60  # 60 days ago
        now_ts = time.time()

        pydb.insert_with_id(
            "aaaa1111-0000-0000-0000-000000000001", "old temporary",
            metadata={"type": "temporary"}, created_at=old_ts, updated_at=old_ts,
        )
        pydb.insert_with_id(
            "aaaa2222-0000-0000-0000-000000000002", "old fact",
            metadata={"type": "fact"}, created_at=old_ts, updated_at=old_ts,
        )
        pydb.insert_with_id(
            "aaaa3333-0000-0000-0000-000000000003", "new temporary",
            metadata={"type": "temporary"}, created_at=now_ts, updated_at=now_ts,
        )
        pydb.insert_with_id(
            "aaaa4444-0000-0000-0000-000000000004", "new fact",
            metadata={"type": "fact"}, created_at=now_ts, updated_at=now_ts,
        )

        cutoff = "2020-01-01"  # Only old memories are before this...no
        # We need a cutoff between old and new
        # old_ts is ~60 days ago. Use a cutoff of 30 days ago
        from datetime import datetime, timezone, timedelta
        cutoff_dt = datetime.now(timezone.utc) - timedelta(days=30)
        cutoff_str = cutoff_dt.strftime("%Y-%m-%dT%H:%M:%S")

        # Dry run preview (should show only the intersection: old + temporary)
        r_preview = run_memori(
            "--json", "purge",
            "--before", cutoff_str,
            "--type", "temporary",
            db_path=db,
        )
        assert r_preview.returncode == 0
        preview = json.loads(r_preview.stdout)
        assert preview["action"] == "preview"
        assert preview["count"] == 1  # only old + temporary

        # Actual delete
        r = run_memori(
            "--json", "purge",
            "--before", cutoff_str,
            "--type", "temporary",
            "--confirm",
            db_path=db,
        )
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert out["action"] == "deleted"
        assert out["count"] == 1  # AND logic: only old + temporary

        # Verify 3 memories remain
        r2 = run_memori("--json", "count", db_path=db)
        assert json.loads(r2.stdout)["count"] == 3

    def test_purge_json_output(self, db):
        store_memory(db, "purge json", meta={"type": "temporary"}, no_embed=True)
        r = run_memori(
            "--json", "purge", "--type", "temporary",
            db_path=db,
        )
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert out["action"] == "preview"
        assert "criteria" in out
        assert out["criteria"]["type"] == "temporary"

    def test_purge_no_args_error(self, db):
        r = run_memori("purge", db_path=db)
        assert r.returncode == 2


# ---------------------------------------------------------------------------
# GC
# ---------------------------------------------------------------------------


class TestGC:
    def test_gc_plain(self, db):
        store_memory(db, "gc test", no_embed=True)
        r = run_memori("gc", db_path=db)
        assert r.returncode == 0
        assert "Compacted" in r.stdout

    def test_gc_json(self, db):
        store_memory(db, "gc json test", no_embed=True)
        r = run_memori("--json", "gc", db_path=db)
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert "before_bytes" in out
        assert "after_bytes" in out
        assert "saved_bytes" in out


# ---------------------------------------------------------------------------
# SETUP
# ---------------------------------------------------------------------------


class TestSetup:
    def test_setup_show(self, db):
        r = run_memori("setup", "--show", db_path=db)
        assert r.returncode == 0
        assert "memori:start" in r.stdout
        assert "memori:end" in r.stdout

    def test_setup_inject(self, tmp_path):
        """Setup injects snippet into CLAUDE.md found in cwd."""
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("# Existing Content\n")
        db_path = str(tmp_path / "test.db")

        # Run setup from cwd=tmp_path
        cmd = [MEMORI_BIN, "--db", db_path, "setup"]
        r = subprocess.run(
            cmd, capture_output=True, text=True, cwd=str(tmp_path), timeout=60,
        )
        assert r.returncode == 0
        assert "Added" in r.stdout

        content = claude_md.read_text()
        assert "memori:start" in content
        assert "# Existing Content" in content

    def test_setup_idempotent(self, tmp_path):
        """Running setup twice should not duplicate the snippet."""
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("# Test\n")
        db_path = str(tmp_path / "test.db")

        cmd = [MEMORI_BIN, "--db", db_path, "setup"]
        subprocess.run(cmd, capture_output=True, text=True, cwd=str(tmp_path), timeout=60)
        r2 = subprocess.run(cmd, capture_output=True, text=True, cwd=str(tmp_path), timeout=60)
        assert r2.returncode == 0
        assert "already present" in r2.stdout

        # Only one marker pair
        content = claude_md.read_text()
        assert content.count("memori:start") == 1

    def test_setup_undo(self, tmp_path):
        """Undo removes the injected snippet."""
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("# Before\n")
        db_path = str(tmp_path / "test.db")

        cmd_setup = [MEMORI_BIN, "--db", db_path, "setup"]
        cmd_undo = [MEMORI_BIN, "--db", db_path, "setup", "--undo"]

        subprocess.run(cmd_setup, capture_output=True, text=True, cwd=str(tmp_path), timeout=60)
        r = subprocess.run(cmd_undo, capture_output=True, text=True, cwd=str(tmp_path), timeout=60)
        assert r.returncode == 0
        assert "Removed" in r.stdout

        content = claude_md.read_text()
        assert "memori:start" not in content
        assert "# Before" in content


# ---------------------------------------------------------------------------
# VERSION
# ---------------------------------------------------------------------------


class TestVersion:
    def test_version_flag(self, db):
        r = run_memori("--version")
        assert r.returncode == 0
        assert "memori" in r.stdout
        # Should contain a version number
        assert "0." in r.stdout or "1." in r.stdout


# ---------------------------------------------------------------------------
# GLOBAL FLAGS
# ---------------------------------------------------------------------------


class TestGlobalFlags:
    def test_db_custom_path(self, tmp_path):
        custom_db = str(tmp_path / "custom.db")
        r = run_memori("--db", custom_db, "--json", "store", "custom path test", "--no-embed")
        assert r.returncode == 0
        assert os.path.exists(custom_db)

        r2 = run_memori("--db", custom_db, "--json", "count")
        assert json.loads(r2.stdout)["count"] == 1

    def test_json_before_subcommand(self, db):
        """--json flag works before the subcommand name."""
        store_memory(db, "global json test", no_embed=True)
        r = run_memori("--json", "count", db_path=db)
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert out["count"] == 1

    def test_json_after_subcommand(self, db):
        """--json flag also works after the subcommand name."""
        store_memory(db, "sub json test", no_embed=True)
        r = run_memori("count", "--json", db_path=db)
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert out["count"] == 1
