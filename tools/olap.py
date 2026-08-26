"""OLAP analysis helpers for structured business data.

The module builds small, explainable OLAP cubes from CSV/Excel data frames:
slice/dice filtering, rollups, drill-downs, pivots, and automatic top insights.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from tools.data_agent import clean_data, load_file


SUPPORTED_AGGREGATIONS = {"sum", "mean", "min", "max", "count"}
DEFAULT_MAX_ROWS = 100


class OLAPError(ValueError):
    """Raised when an OLAP request is invalid or cannot be completed."""


@dataclass
class OLAPQuery:
    """Declarative OLAP request used by tools, agents, and the API."""

    dimensions: list[str] = field(default_factory=list)
    measures: list[str] = field(default_factory=list)
    aggregations: list[str] = field(default_factory=lambda: ["sum"])
    filters: dict[str, Any] = field(default_factory=dict)
    pivot: bool = False
    rows: list[str] = field(default_factory=list)
    columns: list[str] = field(default_factory=list)
    top_n: int | None = 10
    max_rows: int = DEFAULT_MAX_ROWS


def _normalize_name(name: str) -> str:
    return str(name).strip().lower().replace(" ", "_")


def _normalize_list(values: list[str] | tuple[str, ...] | None) -> list[str]:
    return [_normalize_name(value) for value in values or [] if str(value).strip()]


def _normalize_filters(filters: dict[str, Any] | None) -> dict[str, Any]:
    return {_normalize_name(key): value for key, value in (filters or {}).items()}


def _prepare_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    cleaned, structure = clean_data(df)
    return cleaned, structure


def _default_dimensions(structure: dict, limit: int = 2) -> list[str]:
    dimensions = list(structure.get("category_columns", []))
    if not dimensions and structure.get("date_columns"):
        dimensions = list(structure["date_columns"])
    return dimensions[:limit]


def _default_measures(structure: dict, limit: int = 2) -> list[str]:
    return list(structure.get("numeric_columns", []))[:limit]


def _validate_columns(df: pd.DataFrame, columns: list[str], label: str) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise OLAPError(f"Unknown {label}: {missing}. Available columns: {list(df.columns)}")


def _validate_query(df: pd.DataFrame, structure: dict, query: OLAPQuery) -> OLAPQuery:
    dimensions = _normalize_list(query.dimensions) or _default_dimensions(structure)
    measures = _normalize_list(query.measures) or _default_measures(structure)
    aggregations = [agg.lower().strip() for agg in query.aggregations or ["sum"]]
    rows = _normalize_list(query.rows)
    columns = _normalize_list(query.columns)

    invalid_aggs = [agg for agg in aggregations if agg not in SUPPORTED_AGGREGATIONS]
    if invalid_aggs:
        raise OLAPError(
            f"Unsupported aggregations: {invalid_aggs}. "
            f"Supported: {sorted(SUPPORTED_AGGREGATIONS)}"
        )

    if not measures:
        raise OLAPError("OLAP analysis requires at least one numeric measure.")
    if not dimensions and not rows and not columns:
        raise OLAPError("OLAP analysis requires at least one dimension.")

    _validate_columns(df, dimensions, "dimensions")
    _validate_columns(df, measures, "measures")
    _validate_columns(df, rows, "pivot rows")
    _validate_columns(df, columns, "pivot columns")
    _validate_columns(df, list(_normalize_filters(query.filters).keys()), "filters")

    return OLAPQuery(
        dimensions=dimensions,
        measures=measures,
        aggregations=aggregations,
        filters=_normalize_filters(query.filters),
        pivot=query.pivot,
        rows=rows,
        columns=columns,
        top_n=query.top_n,
        max_rows=max(1, int(query.max_rows or DEFAULT_MAX_ROWS)),
    )


def apply_filters(df: pd.DataFrame, filters: dict[str, Any] | None = None) -> pd.DataFrame:
    """Return rows matching equality, membership, or min/max range filters."""
    filtered = df.copy()
    for column, condition in _normalize_filters(filters).items():
        if column not in filtered.columns:
            raise OLAPError(f"Unknown filter column: {column}")

        if isinstance(condition, dict):
            if "eq" in condition:
                filtered = filtered[filtered[column] == condition["eq"]]
            if "in" in condition:
                filtered = filtered[filtered[column].isin(condition["in"])]
            if "min" in condition:
                filtered = filtered[filtered[column] >= condition["min"]]
            if "max" in condition:
                filtered = filtered[filtered[column] <= condition["max"]]
            if "contains" in condition:
                needle = str(condition["contains"])
                filtered = filtered[
                    filtered[column].astype(str).str.contains(needle, case=False, na=False)
                ]
        elif isinstance(condition, (list, tuple, set)):
            filtered = filtered[filtered[column].isin(list(condition))]
        else:
            filtered = filtered[filtered[column] == condition]

    return filtered


def build_cube(df: pd.DataFrame, query: OLAPQuery) -> pd.DataFrame:
    """Aggregate measures by dimensions and return a flat OLAP cube table."""
    if df.empty:
        return pd.DataFrame()

    agg_map = {measure: query.aggregations for measure in query.measures}
    grouped = df.groupby(query.dimensions, dropna=False).agg(agg_map).reset_index()

    if isinstance(grouped.columns, pd.MultiIndex):
        grouped.columns = [
            "_".join(str(part) for part in column if str(part))
            for column in grouped.columns.to_flat_index()
        ]

    measure_sort = f"{query.measures[0]}_{query.aggregations[0]}"
    if measure_sort in grouped.columns:
        grouped = grouped.sort_values(measure_sort, ascending=False)

    if query.top_n:
        grouped = grouped.head(int(query.top_n))

    return grouped.head(query.max_rows)


def build_pivot(df: pd.DataFrame, query: OLAPQuery) -> pd.DataFrame:
    """Build a pivot table for one primary measure and aggregation."""
    rows = query.rows or query.dimensions[:1]
    columns = query.columns or query.dimensions[1:2]
    if not rows:
        raise OLAPError("Pivot analysis requires at least one row dimension.")

    pivot = pd.pivot_table(
        df,
        index=rows,
        columns=columns or None,
        values=query.measures[0],
        aggfunc=query.aggregations[0],
        fill_value=0,
        dropna=False,
    )
    pivot = pivot.reset_index()
    pivot.columns = [str(column) for column in pivot.columns]
    return pivot.head(query.max_rows)


def rollup(df: pd.DataFrame, dimensions: list[str], measures: list[str]) -> list[dict]:
    """Return increasingly summarized totals from detailed dimensions to grand total."""
    frames = []
    for depth in range(len(dimensions), 0, -1):
        active_dims = dimensions[:depth]
        grouped = df.groupby(active_dims, dropna=False)[measures].sum().reset_index()
        grouped["_level"] = " > ".join(active_dims)
        frames.append(grouped)

    grand_total = df[measures].sum(numeric_only=True).to_frame().T
    grand_total["_level"] = "grand_total"
    frames.append(grand_total)

    return pd.concat(frames, ignore_index=True, sort=False).fillna("").to_dict("records")


def drill_down(
    df: pd.DataFrame,
    from_dimension: str,
    to_dimension: str,
    measures: list[str],
    value: Any | None = None,
    max_rows: int = DEFAULT_MAX_ROWS,
) -> list[dict]:
    """Break one dimension value down by a lower-level dimension."""
    from_dimension = _normalize_name(from_dimension)
    to_dimension = _normalize_name(to_dimension)
    measures = _normalize_list(measures)
    _validate_columns(df, [from_dimension, to_dimension, *measures], "drill-down columns")

    subset = df[df[from_dimension] == value] if value is not None else df
    grouped = subset.groupby([from_dimension, to_dimension], dropna=False)[measures].sum()
    return grouped.reset_index().head(max_rows).to_dict("records")


def generate_insights(cube: pd.DataFrame, query: OLAPQuery, row_count: int) -> list[str]:
    """Create short deterministic business insights from the cube output."""
    if cube.empty:
        return ["No rows matched the OLAP filters."]

    insights = [f"Analyzed {row_count} filtered rows across {len(query.dimensions)} dimension(s)."]
    primary_metric = f"{query.measures[0]}_{query.aggregations[0]}"
    if primary_metric not in cube.columns:
        return insights

    top_row = cube.iloc[0]
    dimension_label = ", ".join(str(top_row[dim]) for dim in query.dimensions)
    total = cube[primary_metric].sum()
    top_value = float(top_row[primary_metric])
    share = (top_value / total * 100) if total else 0.0
    insights.append(
        f"Top segment for {primary_metric} is {dimension_label} "
        f"with {top_value:.2f} ({share:.1f}% of displayed total)."
    )

    if len(cube) > 1:
        bottom_row = cube.iloc[-1]
        bottom_label = ", ".join(str(bottom_row[dim]) for dim in query.dimensions)
        insights.append(f"Lowest displayed segment is {bottom_label}.")

    return insights


def analyze_dataframe(df: pd.DataFrame, query: OLAPQuery | None = None) -> dict:
    """Run a full OLAP analysis against a dataframe."""
    cleaned, structure = _prepare_dataframe(df)
    query = _validate_query(cleaned, structure, query or OLAPQuery())
    filtered = apply_filters(cleaned, query.filters)
    cube = build_cube(filtered, query)
    pivot = build_pivot(filtered, query) if query.pivot else pd.DataFrame()

    return {
        "structure": structure,
        "query": {
            "dimensions": query.dimensions,
            "measures": query.measures,
            "aggregations": query.aggregations,
            "filters": query.filters,
            "pivot": query.pivot,
            "rows": query.rows,
            "columns": query.columns,
            "top_n": query.top_n,
            "max_rows": query.max_rows,
        },
        "row_count": int(len(cleaned)),
        "filtered_row_count": int(len(filtered)),
        "cube": cube.to_dict("records"),
        "pivot_table": pivot.to_dict("records") if query.pivot else [],
        "rollup": rollup(filtered, query.dimensions, query.measures),
        "insights": generate_insights(cube, query, int(len(filtered))),
    }


def analyze_file(file_path: str, query: OLAPQuery | None = None) -> dict:
    """Load a CSV/Excel file and run OLAP analysis."""
    return analyze_dataframe(load_file(file_path), query)
