"""Document Intelligence Agent.

Answers user questions over ingested documents using RAG (RAGPipeline)
for retrieval and Groq (Llama 3.3 70B) for grounded answer generation.

Design principles:
- Never answer outside the retrieved context (grounding).
- If nothing relevant is retrieved, say so instead of guessing.
- Every claim must cite a source; citations are checked against what
  was actually retrieved to catch fabricated references.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from agents.base import AgentResult, BaseAgent
from rag.rag_pipeline import RAGPipeline

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent / ".env")

SYSTEM_PROMPT = """You are a document intelligence assistant for a business platform.

STRICT RULES:
1. Only answer using the provided CONTEXT below. Do not use any outside knowledge.
2. Every factual claim you make must be followed by a citation like [1], [2], matching the numbered sources in the context.
3. If you list multiple facts (e.g. as a numbered or bulleted list), you MUST cite each
   individual item separately - do not place a single citation only at the end of the list.
   For example, write:
     "1. Retention dropped 19 points [1]. 2. A competitor opened nearby [1]. 3. Delivery delays rose 22% [1]."
   NOT:
     "1. Retention dropped. 2. A competitor opened nearby. 3. Delivery delays rose [1]."
4. If the context does not contain enough information to answer the question, respond exactly with: "I don't have enough information in the available documents to answer this."
5. Do not speculate, assume, or fill in gaps with general knowledge, even if you think you know the answer.
6. Keep answers concise and directly grounded in the cited text.
"""


class DocumentAgent(BaseAgent):
    name = "document"

    def __init__(self, min_score: float = 0.6):
        self.pipeline = RAGPipeline()
        self.min_score = min_score
        self.client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=os.getenv("GROQ_API_KEY"),
        )

    def run(self, task: str, context: dict | None = None) -> AgentResult:
        """BaseAgent-conforming entry point, so ManagerAgent can call this
        uniformly alongside every other agent. Wraps ask()."""
        namespace = (context or {}).get("namespace", "")
        result = self.ask(task, namespace=namespace)

        return AgentResult(
            agent=self.name,
            output=result["answer"],
            sources=[
                {"label": f"{s['source']} (page {s['page']})", "text": s["text"]}
                for s in result["sources"]
            ],
            ok=result["grounded"],
        )

    def ask(self, question: str, k: int = 5, namespace: str = "") -> dict:
        """Answer a question, grounded strictly in retrieved document context."""
        result = self.pipeline.query(question, k=k, namespace=namespace)

        strong_sources = [s for s in result["sources"] if s["score"] >= self.min_score]

        if not strong_sources:
            return {
                "answer": "I don't have enough information in the available documents to answer this.",
                "sources": [],
                "grounded": True,
                "flagged_citations": [],
            }

        context = "\n\n".join(
            f"[{i+1}] (source: {s['source']}, page: {s['page']})\n"
            f"{self._chunk_text_for(s)}"
            for i, s in enumerate(strong_sources)
        )

        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                temperature=0.1,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"CONTEXT:\n{context}\n\nQUESTION: {question}"},
                ],
            )
        except Exception as e:
            return {
                "answer": f"Document agent failed to generate an answer due to an API error: {e}",
                "sources": strong_sources,
                "grounded": False,
                "flagged_citations": [],
            }

        answer = response.choices[0].message.content

        flagged = self._check_citations(answer, len(strong_sources))

        return {
            "answer": answer,
            "sources": strong_sources,
            "grounded": len(flagged) == 0,
            "flagged_citations": flagged,
        }

    @staticmethod
    def _chunk_text_for(source: dict) -> str:
        """Pull the chunk text out of a source dict returned by RAGPipeline."""
        return source.get("text", "")

    @staticmethod
    def _check_citations(answer: str, num_sources: int) -> list[int]:
        """Find citation numbers in the answer that don't correspond to
        any real retrieved source (i.e. the LLM invented a reference)."""
        cited = {int(n) for n in re.findall(r"\[(\d+)\]", answer)}
        valid_range = set(range(1, num_sources + 1))
        invalid = sorted(cited - valid_range)
        return invalid


if __name__ == "__main__":
    agent = DocumentAgent()

    questions = [
        "Why did sales decline in the Karachi region?",
        "What is the company's policy on cryptocurrency trading?",
    ]

    for q in questions:
        print("=" * 80)
        print(f"Q: {q}")
        result = agent.ask(q)
        print(f"\nA: {result['answer']}")
        print(f"\nGrounded: {result['grounded']}")
        if result["flagged_citations"]:
            print(f"WARNING - fabricated citations detected: {result['flagged_citations']}")
        print(f"\nSources used: {len(result['sources'])}")
        for s in result["sources"]:
            print(f"  - {s['source']} | page {s['page']} | score {s['score']:.4f}")
        print()