"""Research Agent - gathers live external facts and tracks sources.

Uses the web search tool (tools/search_tool.py - owned by Ahmad).
Owner: Danish (agent) + Ahmad (tool)
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from agents.base import AgentResult, BaseAgent
from tools.search_tool import web_search

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent / ".env")

SYSTEM_PROMPT = """You are a research assistant that summarizes live web search results.

STRICT RULES:
1. Only use information from the provided SEARCH RESULTS below. Do not use any outside knowledge.
2. Every factual claim must be followed by a citation like [1], [2], matching the numbered sources.
3. If the search results do not contain enough information to answer the question, respond exactly with: "I could not find enough information from web search to answer this."
4. Do not speculate or fill gaps with general knowledge, even if you think you know the answer.
5. Keep the summary concise and directly grounded in the search result content.
"""


class ResearchAgent(BaseAgent):
    name = "researcher"

    def __init__(self, max_results: int = 5):
        self.max_results = max_results
        self.client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=os.getenv("GROQ_API_KEY"),
        )

    def run(self, task: str, context: dict | None = None) -> AgentResult:
        """Search the web for `task`, then summarize findings with citations."""
        try:
            results = web_search(task, max_results=self.max_results)
        except (ValueError, RuntimeError) as e:
            return AgentResult(
                agent=self.name,
                output=f"Research agent failed: {e}",
                sources=[],
                ok=False,
            )

        if not results:
            return AgentResult(
                agent=self.name,
                output="I could not find enough information from web search to answer this.",
                sources=[],
                ok=True,
            )

        search_context = "\n\n".join(
            f"[{i+1}] (source: {r.url})\nTitle: {r.title}\n{r.content}"
            for i, r in enumerate(results)
        )

        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                temperature=0.1,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"SEARCH RESULTS:\n{search_context}\n\nQUESTION/TASK: {task}"},
                ],
            )
        except Exception as e:
            return AgentResult(
                agent=self.name,
                output=f"Research agent failed to generate a summary due to an API error: {e}",
                sources=[{"label": r.url, "text": r.content} for r in results],
                ok=False,
            )

        answer = response.choices[0].message.content
        flagged = self._check_citations(answer, len(results))

        return AgentResult(
            agent=self.name,
            output=answer,
            sources=[{"label": r.url, "text": r.content} for r in results],
            ok=len(flagged) == 0,
        )

    @staticmethod
    def _check_citations(answer: str, num_sources: int) -> list[int]:
        """Flag citation numbers that don't correspond to a real search result."""
        cited = {int(n) for n in re.findall(r"\[(\d+)\]", answer)}
        valid_range = set(range(1, num_sources + 1))
        return sorted(cited - valid_range)


if __name__ == "__main__":
    agent = ResearchAgent()

    tasks = [
        "Tell me about AXI Technologies, a software based company in pakistan.",
        "What is the current stock price of a fictional company called ZorpTech Inc?",
    ]

    for t in tasks:
        print("=" * 80)
        print(f"Task: {t}")
        result = agent.run(t)
        print(f"\nOutput:\n{result.output}")
        print(f"\nOk: {result.ok}")
        print("Sources:")
        for s in result.sources:
            print(f"  - {s['label']}")
        print()