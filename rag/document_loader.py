"""Document loading & chunking for the RAG pipeline.

Loads PDFs, reports, and company documents, then splits them into chunks.
Owner: Manan
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Chunk:
    text: str
    source: str
    page: int | None = None


def load_document(path: str) -> str:
    """Read a document (PDF, txt, docx) and return its raw text."""
    # TODO: support PDF (pypdf) first, then other formats
    raise NotImplementedError("Manan: implement document loading")


def chunk_text(text: str, source: str, size: int = 800, overlap: int = 100) -> list[Chunk]:
    """Split text into overlapping chunks for embedding."""
    # TODO: implement a sliding-window chunker
    raise NotImplementedError("Manan: implement chunking")
