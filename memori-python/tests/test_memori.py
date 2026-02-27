import pytest

from memori import PyMemori


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "test.db")
    return PyMemori(path)


# -- insert returns dict --


def test_insert_returns_dict(db):
    result = db.insert("hello world", metadata={"tag": "test"})
    assert isinstance(result, dict)
    assert "id" in result
    assert "action" in result
    assert isinstance(result["id"], str)
    assert len(result["id"]) == 36  # UUID format
    assert result["action"] == "created"


def test_insert_and_get(db):
    result = db.insert("hello world", metadata={"tag": "test"})
    mid = result["id"]

    mem = db.get(mid)
    assert mem is not None
    assert mem["content"] == "hello world"
    assert mem["metadata"] == {"tag": "test"}
    # With embeddings feature enabled, vector is auto-generated
    assert mem["vector"] is not None
    assert mem["created_at"] > 0


def test_insert_with_vector(db):
    vec = [1.0, 2.0, 3.0]
    result = db.insert("with vector", vector=vec)
    mid = result["id"]

    mem = db.get(mid)
    assert mem["vector"] is not None
    assert len(mem["vector"]) == 3
    assert abs(mem["vector"][0] - 1.0) < 1e-6


def test_update_content(db):
    mid = db.insert("original")["id"]
    db.update(mid, content="updated")

    mem = db.get(mid)
    assert mem["content"] == "updated"


def test_update_metadata(db):
    mid = db.insert("test", metadata={"a": 1})["id"]
    db.update(mid, metadata={"b": 2})

    mem = db.get(mid)
    assert mem["metadata"] == {"b": 2}


def test_delete(db):
    mid = db.insert("to delete")["id"]
    assert db.count() == 1

    db.delete(mid)
    assert db.count() == 0
    assert db.get(mid) is None


def test_count(db):
    assert db.count() == 0
    for i in range(5):
        db.insert(f"memory {i}")
    assert db.count() == 5


def test_vector_search(db):
    db.insert("north", vector=[1.0, 0.0, 0.0])
    db.insert("east", vector=[0.0, 1.0, 0.0])
    db.insert("mostly north", vector=[0.9, 0.1, 0.0])

    results = db.search(vector=[1.0, 0.0, 0.0], limit=3)
    assert len(results) == 3
    assert results[0]["content"] == "north"
    assert results[1]["content"] == "mostly north"
    assert results[0]["score"] > results[1]["score"]


def test_text_search(db):
    db.insert("the quick brown fox jumps over the lazy dog", no_embed=True)
    db.insert("a fast red car drives on the highway", no_embed=True)
    db.insert("the brown bear sleeps in the forest", no_embed=True)

    # text_only=True to test pure FTS5 behavior (skip auto-vectorize)
    results = db.search(text="brown", limit=10, text_only=True)
    assert len(results) == 2
    assert all("brown" in r["content"] for r in results)


def test_hybrid_search(db):
    db.insert("machine learning models", vector=[1.0, 0.0, 0.0])
    db.insert("database optimization", vector=[0.0, 1.0, 0.0])
    db.insert("machine learning optimization", vector=[0.5, 0.5, 0.0])

    results = db.search(
        vector=[0.9, 0.1, 0.0],
        text="optimization",
        limit=3,
    )
    assert len(results) > 0
    contents = [r["content"] for r in results]
    assert "machine learning optimization" in contents


def test_metadata_filter(db):
    db.insert("pref: dark mode", metadata={"type": "preference"})
    db.insert("fact: earth is round", metadata={"type": "fact"})
    db.insert("pref: vim keys", metadata={"type": "preference"})

    results = db.search(filter={"type": "preference"}, limit=10)
    assert len(results) == 2
    assert all(r["metadata"]["type"] == "preference" for r in results)


def test_get_nonexistent(db):
    assert db.get("nonexistent-id") is None


def test_delete_nonexistent(db):
    with pytest.raises(RuntimeError):
        db.delete("nonexistent-id")


def test_empty_search(db):
    results = db.search(text="anything", limit=10)
    assert results == []


def test_search_default_limit(db):
    for i in range(20):
        db.insert(f"memory {i}")

    results = db.search()
    assert len(results) == 10  # default limit


def test_nested_metadata(db):
    meta = {"tags": ["a", "b"], "nested": {"key": "value"}}
    mid = db.insert("nested metadata test", metadata=meta)["id"]

    mem = db.get(mid)
    assert mem["metadata"]["tags"] == ["a", "b"]
    assert mem["metadata"]["nested"]["key"] == "value"


# -- v0.3 dedup tests --


def test_dedup_same_type(db):
    v1 = [1.0, 0.0, 0.0]
    v2 = [0.99, 0.01, 0.0]

    r1 = db.insert("kafka architecture", vector=v1, metadata={"type": "arch"}, dedup_threshold=0.92)
    assert r1["action"] == "created"

    r2 = db.insert("kafka arch notes", vector=v2, metadata={"type": "arch"}, dedup_threshold=0.92)
    assert r2["action"] == "deduplicated"
    assert r2["id"] == r1["id"]
    assert db.count() == 1


# -- v0.3.1 access tracking tests --


def test_access_count_on_get(db):
    mid = db.insert("access test")["id"]

    # First get: snapshot sees access_count=0
    mem1 = db.get(mid)
    assert mem1["access_count"] == 0

    # Second get: sees the touch from first get
    mem2 = db.get(mid)
    assert mem2["access_count"] == 1

    # Third get confirms steady increment
    mem3 = db.get(mid)
    assert mem3["access_count"] == 2


def test_search_does_not_bump_access_count(db):
    mid = db.insert("searchable item", vector=[1.0, 0.0, 0.0])["id"]

    # Search should NOT bump access count
    results = db.search(vector=[1.0, 0.0, 0.0], limit=1)
    assert len(results) == 1
    assert results[0]["access_count"] == 0

    # Search again -- still 0
    results2 = db.search(vector=[1.0, 0.0, 0.0], limit=1)
    assert results2[0]["access_count"] == 0

    # get() DOES bump it
    mem = db.get(mid)
    assert mem["access_count"] == 0  # snapshot before touch
    mem2 = db.get(mid)
    assert mem2["access_count"] == 1  # now it's bumped


# -- v0.3.1 embedding stats --


def test_embedding_stats(db):
    db.insert("with vec", vector=[1.0, 0.0, 0.0])
    db.insert("another", vector=[0.0, 1.0, 0.0])

    stats = db.embedding_stats()
    assert isinstance(stats, dict)
    assert "embedded" in stats
    assert "total" in stats
    assert stats["total"] >= 2
    assert stats["embedded"] >= 2


# -- v0.3.1 auto-vectorize search --


def test_auto_vectorize_search(db):
    """Text-only search with embeddings enabled returns hybrid results with scores."""
    db.insert("kafka architecture uses partitioned topics", metadata={"type": "architecture"})
    db.insert("redis caching layer for sessions", metadata={"type": "architecture"})

    # text_only=False (default) -- auto-vectorizes the query and does hybrid search
    results = db.search(text="message queue partitioning", limit=5)
    assert len(results) > 0
    # Hybrid search produces RRF scores
    assert all(r.get("score") is not None for r in results)


def test_text_only_flag(db):
    """--text-only forces pure FTS5 search even with embeddings enabled."""
    db.insert("kafka partitioned topics", no_embed=True)
    db.insert("redis caching layer", no_embed=True)

    # text_only=True -- pure FTS5, only exact text matches
    results = db.search(text="kafka", limit=5, text_only=True)
    assert len(results) == 1
    assert "kafka" in results[0]["content"]
