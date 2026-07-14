"""Vector database interface (FAISS / ChromaDB / Pinecone).

Stores embeddings and runs semantic search with source tracking.
Owner: Manan
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec

from document_loader import Chunk

_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_env_path)


class VectorDB:
    def __init__(self, backend: str = "pinecone", dimension: int = 384):
        self.backend = backend
        self.dimension = dimension

        if backend == "pinecone":
            api_key = os.getenv("PINECONE_API_KEY")
            index_name = os.getenv("PINECONE_INDEX_NAME", "aura-knowledge")

            if not api_key:
                raise ValueError("PINECONE_API_KEY not found in .env")

            self._pc = Pinecone(api_key=api_key)

            existing = [i.name for i in self._pc.list_indexes()]
            if index_name not in existing:
                self._pc.create_index(
                    name=index_name,
                    dimension=dimension,
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region="us-east-1"),
                )
            self._index = self._pc.Index(index_name)
        else:
            raise NotImplementedError(f"Backend '{backend}' not implemented yet — only 'pinecone' is supported")

    def add(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        """Store chunks together with their vectors."""
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must be the same length")

        vectors = [
            {
                "id": self._make_id(chunks[i]),
                "values": embeddings[i],
                "metadata": {
                    "text": chunks[i].text,
                    "source": chunks[i].source,
                    "page": chunks[i].page if chunks[i].page is not None else -1,
                },
            }
            for i in range(len(chunks))
        ]

        batch_size = 100
        for start in range(0, len(vectors), batch_size):
            self._index.upsert(vectors=vectors[start:start + batch_size])

    def search(self, query_vector: list[float], k: int = 5) -> list[dict]:
        """Return the k most similar chunks (with their sources)."""
        results = self._index.query(vector=query_vector, top_k=k, include_metadata=True)

        return [
            {
                "text": match["metadata"]["text"],
                "source": match["metadata"]["source"],
                "page": match["metadata"]["page"] if match["metadata"]["page"] != -1 else None,
                "score": match["score"],
            }
            for match in results["matches"]
        ]

    @staticmethod
    def _make_id(chunk: Chunk) -> str:
        """Deterministic ID so re-ingesting the same chunk overwrites it
        instead of creating a duplicate vector."""
        raw = f"{chunk.source}|{chunk.page}|{chunk.text}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()