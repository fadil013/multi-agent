"""Analytics tool - pattern detection and chart generation.

Owner: Ahmad
"""
from __future__ import annotations


def summarize(df) -> dict:
    """Return basic statistics and detected trends for a DataFrame."""
    # TODO: describe(), trend detection, outliers
    raise NotImplementedError("Ahmad: implement analytics")


def make_chart(df, kind: str = "line", path: str = "chart.png") -> str:
    """Generate a chart and return the saved file path."""
    # TODO: render with matplotlib / plotly and save to `path`
    raise NotImplementedError
