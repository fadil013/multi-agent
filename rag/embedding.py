"""Embedding pipeline - turns text chunks into vectors.

Owner: Manan
"""
from __future__ import annotations


class Embedder:
    def __init__(self, model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model = model

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return an embedding vector for each input text."""
        # TODO: load the model once and encode the texts
        raise NotImplementedError("Manan: implement embeddings")
