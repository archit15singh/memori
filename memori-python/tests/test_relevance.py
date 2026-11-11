"""Relevance gating is on raw cosine, not popularity or fused RRF scores."""
import json
import threading
import subprocess
import sys
from http.server import HTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest
from memori import PyMemori


@pytest.fixture
def db(tmp_path):
    return PyMemori(str(tmp_path / 'relevance.db'))


def test_vector_threshold_precedes_access_boost_and_limit(db):
    best = db.insert('best', vector=[1., 0.])['id']
    weak = db.insert('weak', vector=[0.8, 0.6])['id']
    db.set_access_stats(weak, access_count=1000000, last_accessed=2000000000.)
    assert db.search(vector=[1., 0.], limit=1)[0]['id'] == weak
    assert [m['id'] for m in db.search(vector=[1., 0.], min_similarity=0.9, limit=1)] == [best]


def test_hybrid_keeps_literal_matches_but_rejects_weak_semantic_candidates(db):
    exact = db.insert('PostgreSQL architecture', vector=[0., 1.])['id']
    db.insert('unrelated item', vector=[0., 1.])
    results = db.search(text='PostgreSQL', vector=[1., 0.], min_similarity=0.9)
    assert [m['id'] for m in results] == [exact]
    assert db.search(text='bananas', vector=[1., 0.], min_similarity=0.9) == []


def test_threshold_boundary_and_related(db):
    source = db.insert('source', vector=[1., 0.])['id']
    other = db.insert('identical vector', vector=[1., 0.])['id']
    db.insert('orthogonal', vector=[0., 1.])
    assert len(db.search(vector=[1., 0.], min_similarity=1.)) == 2
    assert [m['id'] for m in db.related(source, min_similarity=1.)] == [other]


def test_filters_still_apply_and_zero_limit_is_empty(db):
    first = db.insert('first', vector=[1., 0.], metadata={'type': 'fact'})['id']
    db.insert('second', vector=[1., 0.], metadata={'type': 'decision'})
    assert [m['id'] for m in db.search(vector=[1., 0.], filter={'type': 'fact'}, min_similarity=0.9)] == [first]
    assert db.search(vector=[1., 0.], min_similarity=0.9, limit=0) == []


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -1.1, 1.1, -1.00000001, 1.00000001])
def test_invalid_threshold(db, value):
    with pytest.raises(RuntimeError, match='similarity'):
        db.search(vector=[1., 0.], min_similarity=value)
    source = db.insert('source', vector=[1., 0.])['id']
    with pytest.raises(RuntimeError, match='similarity'):
        db.related(source, min_similarity=value)


def test_threshold_requires_a_vector_search(db):
    with pytest.raises(RuntimeError, match='similarity'):
        db.search(min_similarity=0.5)
    with pytest.raises(RuntimeError, match='similarity'):
        db.search(text='hello', text_only=True, min_similarity=0.5)
