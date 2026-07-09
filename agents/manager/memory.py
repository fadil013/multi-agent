"""Memory - short-term (current run) and long-term (vector store) memory.

Owner: Danish  (long-term recall is backed by the RAG layer - coordinate with Manan)
"""
from __future__ import annotations


class Memory:
    def __init__(self):
        self._short_term: list[dict] = []

    def remember(self, item: dict) -> None:
        """Store an item in short-term memory."""
        self._short_term.append(item)

    def recall(self, query: str) -> list[dict]:
        """Retrieve relevant items."""
        # TODO: wire long-term recall to rag.vector_db.VectorDB.search
        return self._short_term
