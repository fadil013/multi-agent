"""End-to-end RAG pipeline: load -> chunk -> embed -> store -> retrieve.

Answers questions over documents WITH source citations.
Owner: Manan
"""
from __future__ import annotations

from pathlib import Path

from rag.document_loader import chunk_pdf_with_pages, chunk_text, load_document
from rag.embedding import Embedder
from rag.vector_db import VectorDB


class RAGPipeline:
    def __init__(self):
        self.embedder = Embedder()
        self.db = VectorDB()

    def ingest(self, path: str, namespace: str = "") -> int:
        """Load, chunk, embed, and store a document. Returns chunk count."""
        ext = Path(path).suffix.lower()

        if ext == ".pdf":
            chunks = chunk_pdf_with_pages(path)
        else:
            text = load_document(path)
            chunks = chunk_text(text, source=path)

        if not chunks:
            return 0

        vectors = self.embedder.embed([c.text for c in chunks])
        self.db.add(chunks, vectors, namespace=namespace)
        return len(chunks)

    def ingest_text(self, text: str, source: str, namespace: str = "") -> int:
        """Chunk, embed, and store raw text (e.g. Research Agent output)."""
        chunks = chunk_text(text, source=source)
        if not chunks:
            return 0

        vectors = self.embedder.embed([c.text for c in chunks])
        self.db.add(chunks, vectors, namespace=namespace)
        return len(chunks)

    def query(self, question: str, k: int = 5, namespace: str = "") -> dict:
        """Retrieve relevant chunks and return context + sources."""
        q_vector = self.embedder.embed_query(question)
        matches = self.db.search(q_vector, k=k, namespace=namespace)

        if not matches:
            return {"answer": None, "sources": [], "context": ""}

        context = "\n\n".join(
            f"[{i+1}] (source: {m['source']}, page: {m['page']})\n{m['text']}"
            for i, m in enumerate(matches)
        )
        sources = [
        {"source": m["source"], "page": m["page"], "score": m["score"], "text": m["text"]}
        for m in matches
        ]
        
        return {"answer": None, "sources": sources, "context": context}