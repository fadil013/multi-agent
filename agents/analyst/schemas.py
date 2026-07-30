"""Pydantic schemas for structured LLM output.

Owner: Danish
"""
from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class ChartConfig(BaseModel):
    chart_type: Literal["scatter", "histogram", "bar", "line", "box", "heatmap", "countplot"]

    x_column: Optional[str] = Field(
        default=None,
        description=(
            "X-axis column. Required for scatter/bar. Optional for line "
            "(only used if no datetime column exists in the data) and for "
            "box (only needed for a grouped box plot alongside y_column)."
        )
    )
    y_column: Optional[str] = Field(
        default=None,
        description=(
            "Y-axis column. Required for scatter/bar/line. Optional for box "
            "(only needed for a grouped box plot alongside x_column)."
        )
    )
    column: Optional[str] = Field(
        default=None,
        description=(
            "Single column. Required for histogram and countplot. "
            "For box, use this instead of x_column/y_column for a simple "
            "single-column distribution plot."
        )
    )
    hue: Optional[str] = Field(
        default=None,
        description="Optional grouping column for scatter, box, or countplot."
    )
    aggregation: Literal["mean", "sum", "median", "count", "min", "max"] = Field(
    default="mean", description="Aggregation method for bar charts."
    )
    title: str


class AnalystOutput(BaseModel):
    """The single structured object the LLM must return."""
    executive_summary: str = Field(
        description="Plain prose business analysis. No markdown, no bullet points, no JSON."
    )
    charts: List[ChartConfig] = Field(
        default_factory=list,
        description="Up to 3 chart configurations that best visualize the key findings."
    )