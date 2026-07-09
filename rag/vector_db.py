"""Vector database interface (FAISS / ChromaDB).

Stores embeddings and runs semantic search with source tracking.
Owner: Manan
"""
from __future__ import annotations


class VectorDB:
    def __init__(self, backend: str = "chroma"):
        self.backend = backend

    def add(self, chunks: list, embeddings: list[list[float]]) -> None:
        """Store chunks together with their vectors."""
        # TODO: persist to the chosen backend
        raise NotImplementedError

    def search(self, query_vector: list[float], k: int = 5) -> list:
        """Return the k most similar chunks (with their sources)."""
        # TODO: nearest-neighbour search
        raise NotImplementedError
