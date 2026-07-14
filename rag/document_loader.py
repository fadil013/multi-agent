"""Document loading & chunking for the RAG pipeline.

Loads PDFs, reports, and company documents, then splits them into chunks.
Owner: Manan
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader


@dataclass
class Chunk:
    text: str
    source: str
    page: int | None = None


def load_document(path: str) -> str:
    """Read a document (PDF, txt, docx) and return its raw text."""
    ext = Path(path).suffix.lower()

    if ext == ".pdf":
        reader = PdfReader(path)
        text = ""
        for page in reader.pages:
            text += (page.extract_text() or "") + "\n"
        return text

    if ext == ".txt":
        return Path(path).read_text(encoding="utf-8")

    raise NotImplementedError(f"Unsupported file type: {ext} (Manan: add docx support if needed)")


def load_document_by_page(path: str) -> list[tuple[int, str]]:
    """Read a PDF and return [(page_number, page_text), ...].

    Kept separate from load_document() so callers that need page-level
    citations (chunk_text below) can use this, while simple full-text
    use cases can stick with load_document().
    """
    ext = Path(path).suffix.lower()
    if ext != ".pdf":
        raise NotImplementedError("Page-level loading is only implemented for PDFs")

    reader = PdfReader(path)
    return [(i + 1, page.extract_text() or "") for i, page in enumerate(reader.pages)]


def chunk_text(text: str, source: str, size: int = 300, overlap: int = 50) -> list[Chunk]:
    """Split text into overlapping chunks for embedding.

    Word-based sliding window: `size` words per chunk, `overlap` words
    shared between consecutive chunks so context isn't lost at boundaries.
    """
    words = text.split()
    if not words:
        return []

    chunks: list[Chunk] = []
    start = 0
    while start < len(words):
        end = start + size
        chunk_words = words[start:end]
        chunks.append(Chunk(text=" ".join(chunk_words), source=source))
        if end >= len(words):
            break
        start += size - overlap

    return chunks


def chunk_pdf_with_pages(path: str, size: int = 300, overlap: int = 50) -> list[Chunk]:
    """Load a PDF and chunk it, preserving page numbers per chunk.

    Chunks per-page rather than across the whole document, so each
    Chunk.page stays accurate even if it means slightly uneven chunk sizes.
    """
    pages = load_document_by_page(path)
    all_chunks: list[Chunk] = []

    for page_num, page_text in pages:
        page_chunks = chunk_text(page_text, source=path, size=size, overlap=overlap)
        for c in page_chunks:
            c.page = page_num
        all_chunks.extend(page_chunks)

    return all_chunks