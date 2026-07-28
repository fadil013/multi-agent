"""Ingest a single document into Pinecone (default namespace)."""
from pathlib import Path

from rag_pipeline import RAGPipeline


def main():
    file_path = Path(__file__).parent / "sales_report_q2_2026.pdf"

    if not file_path.exists():
        print(f"File not found: {file_path}")
        return

    pipeline = RAGPipeline()
    print(f"Ingesting {file_path.name}...")
    count = pipeline.ingest(str(file_path))
    print(f"Done. {count} chunks stored.")


if __name__ == "__main__":
    main()