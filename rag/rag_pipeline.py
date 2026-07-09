"""End-to-end RAG pipeline: load -> chunk -> embed -> store -> retrieve.

Answers questions over documents WITH source citations.
Owner: Manan
"""
from __future__ import annotations

from rag.document_loader import chunk_text, load_document
from rag.embedding import Embedder
from rag.vector_db import VectorDB


class RAGPipeline:
    def __init__(self):
        self.embedder = Embedder()
        self.db = VectorDB()

    def ingest(self, path: str) -> None:
        """Load, chunk, embed, and store a document."""
        # TODO: wire load_document -> chunk_text -> embed -> db.add
        raise NotImplementedError("Manan: implement ingestion")

    def query(self, question: str, k: int = 5) -> dict:
        """Retrieve relevant chunks and return an answer + sources."""
        # TODO: embed question -> db.search -> build answer with citations
        raise NotImplementedError("Manan: implement retrieval + answering")
