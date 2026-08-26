"""OLAP Agent - multidimensional business analysis over structured data."""
from __future__ import annotations

from agents.base import AgentResult, BaseAgent
from tools.olap import OLAPError, OLAPQuery, analyze_dataframe, analyze_file


class OLAPAgent(BaseAgent):
    """Run cube, rollup, drill-down, slice/dice, and pivot analysis."""

    name = "olap"

    def run(self, task: str, context: dict | None = None) -> AgentResult:
        context = context or {}
        query = OLAPQuery(
            dimensions=context.get("dimensions", []),
            measures=context.get("measures", []),
            aggregations=context.get("aggregations", ["sum"]),
            filters=context.get("filters", {}),
            pivot=bool(context.get("pivot", False)),
            rows=context.get("rows", []),
            columns=context.get("columns", []),
            top_n=context.get("top_n", 10),
            max_rows=context.get("max_rows", 100),
        )

        try:
            if "dataframe" in context:
                output = analyze_dataframe(context["dataframe"], query)
            elif "file_path" in context:
                output = analyze_file(context["file_path"], query)
            else:
                raise OLAPError("OLAPAgent requires context['file_path'] or context['dataframe'].")
        except Exception as error:  # noqa: BLE001 - keep agent failures structured
            return AgentResult(agent=self.name, output={"task": task, "error": str(error)}, ok=False)

        output["task"] = task
        return AgentResult(agent=self.name, output=output, sources=[context.get("file_path", "dataframe")])
