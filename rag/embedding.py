"""Embedding pipeline - turns text chunks into vectors.

Owner: Manan
"""
from __future__ import annotations

from sentence_transformers import SentenceTransformer

QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


class Embedder:
    def __init__(self, model: str = "BAAI/bge-small-en-v1.5"):
        self.model_name = model
        self._model = SentenceTransformer(model)

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return an embedding vector for each input text (documents/chunks)."""
        return self._model.encode(texts).tolist()

    def embed_query(self, text: str) -> list[float]:
        """Return an embedding vector for a search query.

        BGE models recommend prefixing queries (not documents) with an
        instruction string to improve retrieval quality.
        """
        return self._model.encode(QUERY_PREFIX + text).tolist()