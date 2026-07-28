"""Manager Agent - the brain of AURA.

Understands the user's goal, breaks it into subtasks, assigns them to the
right specialist agents, monitors progress, and merges the results.

Owner: Danish (Agent Architecture)
"""
from __future__ import annotations

from agents.base import AgentResult
from agents.manager.planner import Planner, Task


class ManagerAgent:
    def __init__(self, agents: dict | None = None, verifier=None):
        # agents: mapping of name -> agent instance (researcher, analyst, document, ...)
        # verifier: optional VerifierAgent instance, run after all tasks complete
        self.agents = agents or {}
        self.verifier = verifier
        self.planner = Planner()

    def run(self, goal: str) -> AgentResult:
        """Plan -> delegate -> verify -> report."""
        tasks = self.planner.decompose(goal)
        ordered = self._topological_order(tasks)

        task_results: dict[int, AgentResult] = {}

        for task in ordered:
            agent = self.agents.get(task.agent)

            if agent is None:
                task_results[task.id] = AgentResult(
                    agent=task.agent,
                    output=f"Agent '{task.agent}' is not registered with the Manager.",
                    ok=False,
                )
                continue

            dep_context = {
                "depends_on_results": [
                    task_results[dep_id].output for dep_id in task.depends_on
                    if dep_id in task_results
                ]
            }

            result = agent.run(task.description, context=dep_context)
            task_results[task.id] = result

        merged = self._merge_results(goal, ordered, task_results)

        if self.verifier is not None:
            verifiable_results = [
                r for r in task_results.values()
                if r.agent in ("document", "researcher") and r.sources
            ]
            if verifiable_results:
                verification = self.verifier.run(
                    "verify", context={"results_to_verify": verifiable_results}
                )
                merged.output += f"\n\n{'=' * 40}\n{verification.output}"
                merged.ok = merged.ok and verification.ok

        return merged

    @staticmethod
    def _topological_order(tasks: list[Task]) -> list[Task]:
        by_id = {t.id: t for t in tasks}
        visited: set[int] = set()
        ordered: list[Task] = []

        def visit(task: Task, stack: set[int]):
            if task.id in visited:
                return
            if task.id in stack:
                raise ValueError(f"Circular dependency detected at task {task.id}")
            stack.add(task.id)
            for dep_id in task.depends_on:
                visit(by_id[dep_id], stack)
            stack.remove(task.id)
            visited.add(task.id)
            ordered.append(task)

        for t in tasks:
            visit(t, set())
        return ordered

    @staticmethod
    def _merge_results(goal: str, tasks: list[Task], results: dict[int, AgentResult]) -> AgentResult:
        combined_output = "\n\n".join(
            f"Task {t.id} ({t.agent}): {t.description}\n{results[t.id].output}"
            for t in tasks
        )
        all_sources = [src for t in tasks for src in results[t.id].sources]
        all_ok = all(results[t.id].ok for t in tasks)

        return AgentResult(
            agent="manager",
            output=combined_output,
            sources=all_sources,
            ok=all_ok,
        )


if __name__ == "__main__":
    from agents.document.document_agent import DocumentAgent
    from agents.researcher.research_agent import ResearchAgent
    from agents.verifier.verifier_agent import VerifierAgent

    manager = ManagerAgent(
        agents={
            "document": DocumentAgent(),
            "research": ResearchAgent(),
        },
        verifier=VerifierAgent(),
    )

    goal = "Our Karachi region sales declined 25% this quarter. Explain the internal causes from our sales report, find any external market factors that may have contributed, and summarize what our marketing strategy is doing to address it."

    result = manager.run(goal)

    print(f"Goal: {goal}\n")
    print(f"Ok: {result.ok}\n")
    print("Output:\n", result.output)