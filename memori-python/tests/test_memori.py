import pytest

from memori import PyMemori


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "test.db")
    return PyMemori(path)


def test_insert_and_get(db):
    mid = db.insert("hello world", metadata={"tag": "test"})
    assert isinstance(mid, str)
    assert len(mid) == 36  # UUID format

    mem = db.get(mid)
    assert mem is not None
    assert mem["content"] == "hello world"
    assert mem["metadata"] == {"tag": "test"}
    assert mem["vector"] is None
    assert mem["created_at"] > 0


def test_insert_with_vector(db):
    vec = [1.0, 2.0, 3.0]
    mid = db.insert("with vector", vector=vec)

    mem = db.get(mid)
    assert mem["vector"] is not None
    assert len(mem["vector"]) == 3
    assert abs(mem["vector"][0] - 1.0) < 1e-6


def test_update_content(db):
    mid = db.insert("original")
    db.update(mid, content="updated")

    mem = db.get(mid)
    assert mem["content"] == "updated"


def test_update_metadata(db):
    mid = db.insert("test", metadata={"a": 1})
    db.update(mid, metadata={"b": 2})

    mem = db.get(mid)
    assert mem["metadata"] == {"b": 2}


def test_delete(db):
    mid = db.insert("to delete")
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
    db.insert("the quick brown fox jumps over the lazy dog")
    db.insert("a fast red car drives on the highway")
    db.insert("the brown bear sleeps in the forest")

    results = db.search(text="brown", limit=10)
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
    mid = db.insert("nested metadata test", metadata=meta)

    mem = db.get(mid)
    assert mem["metadata"]["tags"] == ["a", "b"]
    assert mem["metadata"]["nested"]["key"] == "value"
