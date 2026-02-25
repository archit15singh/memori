"""Memori -- embedded AI agent memory (SQLite + vector search + FTS5).

This package re-exports the native Rust extension's PyMemori class.
"""
from .memori import PyMemori

__all__ = ["PyMemori"]
