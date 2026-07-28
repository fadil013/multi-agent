"""Task Planner - decomposes a business goal into ordered subtasks.

Owner: Danish
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent / ".env")

# Agents currently available in AURA. Update this as more agents are built —
# the planner will only assign tasks to agents listed here.
AVAILABLE_AGENTS = ["document", "research"]
# Once built, extend to:
# AVAILABLE_AGENTS = ["document", "research", "data", "verification", "report"]

SYSTEM_PROMPT = """You are the task planner for AURA, a multi-agent business automation system.

Given a high-level business goal, break it into a small number of concrete, ordered subtasks.

Available agents and what they do:
- "document": reads and answers questions over ingested documents (PDFs, reports) using RAG.
- "research": searches the web for external market/competitor information. (not available yet)
- "data": analyzes structured data like spreadsheets and CSVs. (not available yet)
- "verification": fact-checks and validates outputs from other agents. (not available yet)
- "report": compiles a final report from verified findings. (not available yet)

STRICT RULES:
1. Only assign tasks to agents from this list: {available_agents}
2. If the goal requires an agent that is not yet available, still include the task but assign it to
   the closest available agent, and note the limitation in the task description.
3. Each task must have a unique integer id starting at 1.
4. "depends_on" is a list of task ids that must complete before this task can start. Use an empty
   list if the task has no dependencies.
5. Respond with ONLY valid JSON, no preamble, no markdown code fences, no explanation.
6. Phrase each task's "description" as a natural question a person would actually ask, not an
   abstract instruction. This matters because task descriptions are used directly as search
   queries against a semantic retrieval system, and natural questions match much better than
   instructional phrasing.
   GOOD: "Why did sales decline in the Karachi region?"
   GOOD: "What external market factors could explain the Karachi sales decline?"
   BAD:  "Analyze sales report to identify internal causes of decline"
   BAD:  "Investigate external factors contributing to regional underperformance"
7. Do NOT name specific documents (e.g. "sales report", "marketing strategy doc") in task
   descriptions. You do not know what documents actually exist in the knowledge base - naming
   the wrong one biases retrieval toward irrelevant content. Ask about the topic itself, not
   about what a specific named document says.
   GOOD: "What is the marketing strategy addressing the Karachi sales decline?"
   BAD:  "What does our sales report say about the marketing strategy?"
8. Avoid generating two or more tasks that ask for substantially overlapping information. Each
   task must cover a distinct angle or sub-question. Before finalizing the plan, check whether
   any two tasks would likely retrieve the same underlying information, and merge or remove
   the redundant one if so.

Output format (a JSON array of task objects):
[
  {{"id": 1, "description": "...", "agent": "document", "depends_on": []}},
  {{"id": 2, "description": "...", "agent": "document", "depends_on": [1]}}
]
"""


@dataclass
class Task:
    id: int
    description: str
    agent: str                      # which agent should handle it
    depends_on: list[int] = field(default_factory=list)


class Planner:
    def __init__(self):
        self.client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=os.getenv("GROQ_API_KEY"),
        )

    def decompose(self, goal: str) -> list[Task]:
        """Turn a high-level goal into a list of assigned Tasks."""
        system_prompt = SYSTEM_PROMPT.format(available_agents=AVAILABLE_AGENTS)

        response = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            temperature=0.1,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Business goal: {goal}"},
            ],
        )

        raw = response.choices[0].message.content
        tasks_data = self._parse_json(raw)
        tasks = [self._to_task(t) for t in tasks_data]
        self._validate(tasks)
        return tasks

    @staticmethod
    def _parse_json(raw: str) -> list[dict]:
        """Strip markdown fences if present and parse JSON safely."""
        cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise ValueError(f"Planner LLM did not return valid JSON:\n{raw}") from e

    @staticmethod
    def _to_task(data: dict) -> Task:
        return Task(
            id=data["id"],
            description=data["description"],
            agent=data["agent"],
            depends_on=data.get("depends_on", []) or [],
        )

    @staticmethod
    def _validate(tasks: list[Task]) -> None:
        """Catch obviously broken plans early rather than failing deep in execution."""
        ids = {t.id for t in tasks}

        for t in tasks:
            if t.agent not in AVAILABLE_AGENTS:
                raise ValueError(
                    f"Task {t.id} assigned to unavailable agent '{t.agent}'. "
                    f"Available agents: {AVAILABLE_AGENTS}"
                )
            for dep in t.depends_on:
                if dep not in ids:
                    raise ValueError(f"Task {t.id} depends on non-existent task id {dep}")
                if dep == t.id:
                    raise ValueError(f"Task {t.id} cannot depend on itself")


if __name__ == "__main__":
    planner = Planner()

    goal = "Analyze our sales performance in the Karachi region and explain why it declined."
    tasks = planner.decompose(goal)

    print(f"Goal: {goal}\n")
    for t in tasks:
        deps = f" (depends on: {t.depends_on})" if t.depends_on else ""
        print(f"[{t.id}] agent={t.agent} | {t.description}{deps}")