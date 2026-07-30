"""Data tool - reads Excel/CSV into DataFrames for the Analyst Agent.

Enhanced with advanced regex cleaning, KNN imputation, and anomaly detection.
Owner: Ahmad / Danish
"""
from __future__ import annotations
import pandas as pd
import numpy as np
import os
import re
from sklearn.impute import KNNImputer
from sklearn.ensemble import IsolationForest


def load_table(path: str) -> pd.DataFrame:
    """Load an Excel or CSV file into a pandas DataFrame."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Data Tool Error: Could not find file at '{path}'")

    _, ext = os.path.splitext(path.lower())

    if ext == '.csv':
        return pd.read_csv(path)
    elif ext in ['.xls', '.xlsx']:
        return pd.read_excel(path, engine='openpyxl')
    else:
        raise ValueError(f"Unsupported file format: {ext}. Please provide a .csv or .xlsx file.")


def impute_missing_knn(df: pd.DataFrame, n_neighbors: int = 5) -> pd.DataFrame:
    """
    Fill missing NUMERIC values using K-Nearest Neighbors instead of a naive
    constant fill. Skips entirely if there's nothing missing, to avoid
    wasted computation on already-clean datasets.
    """
    df_imputed = df.copy()
    numeric_cols = df_imputed.select_dtypes(include=['number']).columns.tolist()

    if not numeric_cols:
        return df_imputed

    if not df_imputed[numeric_cols].isnull().values.any():
        return df_imputed  # nothing to impute — skip the KNN fit entirely

    safe_k = min(n_neighbors, max(1, len(df_imputed) - 1))

    try:
        imputer = KNNImputer(n_neighbors=safe_k)
        df_imputed[numeric_cols] = imputer.fit_transform(df_imputed[numeric_cols])
    except Exception as e:
        print(f"[Warning] KNN imputation failed ({e}); falling back to 0-fill for numeric columns.")
        df_imputed[numeric_cols] = df_imputed[numeric_cols].fillna(0)

    return df_imputed


def clean(df: pd.DataFrame, use_knn_imputation: bool = True, n_neighbors: int = 5) -> pd.DataFrame:
    """
    Advanced cleaning pipeline: normalizes columns, strips padding,
    handles empty slots, and infers optimal data types.
    """
    if df.empty:
        return df

    df_cleaned = df.dropna(how='all', axis=0).dropna(how='all', axis=1)

    cleaned_cols = []
    for col in df_cleaned.columns:
        col_str = str(col).strip().lower()
        col_str = col_str.replace(" ", "_")
        col_str = re.sub(r'[^a-z0-9_]', '', col_str)
        col_str = re.sub(r'_+', '_', col_str)
        cleaned_cols.append(col_str)
    df_cleaned.columns = cleaned_cols

    for col in df_cleaned.select_dtypes(include=['object', 'string']).columns:
        df_cleaned[col] = df_cleaned[col].apply(
            lambda x: x.strip() if isinstance(x, str) else x
        )

    if use_knn_imputation:
        df_cleaned = impute_missing_knn(df_cleaned, n_neighbors=n_neighbors)
    else:
        numeric_cols = df_cleaned.select_dtypes(include=['number']).columns
        df_cleaned[numeric_cols] = df_cleaned[numeric_cols].fillna(0)

    categorical_cols = df_cleaned.select_dtypes(include=['object', 'string']).columns
    df_cleaned[categorical_cols] = df_cleaned[categorical_cols].fillna("Unknown")

    return df_cleaned.convert_dtypes()


def detect_anomalies(df: pd.DataFrame, contamination: float = 0.05) -> tuple[pd.DataFrame, str]:
    """
    Flags anomalous rows using Isolation Forest.
    Returns the DataFrame with an added 'is_anomaly' column, plus a
    human-readable summary string for the LLM/report.
    """
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()

    if len(numeric_cols) == 0:
        return df, "No numeric columns available for anomaly detection."

    if len(df) < 10:
        return df, "Dataset too small for reliable anomaly detection (fewer than 10 rows)."

    df_flagged = df.copy()

    model = IsolationForest(contamination=contamination, random_state=42)
    predictions = model.fit_predict(df_flagged[numeric_cols])
    df_flagged['is_anomaly'] = predictions == -1

    n_anomalies = int((predictions == -1).sum())
    pct = (n_anomalies / len(df_flagged)) * 100

    summary_lines = [
        "=== Anomaly Detection (Isolation Forest) ===",
        f"Flagged {n_anomalies} anomalous rows out of {len(df_flagged)} ({pct:.1f}%).",
    ]

    if n_anomalies > 0:
        anomaly_rows = df_flagged[df_flagged['is_anomaly']].head(5)
        summary_lines.append("Sample anomalous rows (up to 5 shown):")
        summary_lines.append(anomaly_rows.to_string())

    return df_flagged, "\n".join(summary_lines)


def generate_eda_summary(df: pd.DataFrame) -> str:
    """
    Calculates Summary statistics (mean, median, std, min, max, quartiles)
    for all numeric columns.
    """
    numeric_df = df.select_dtypes(include=['number'])

    if numeric_df.empty:
        return "No numeric columns available for statistical analysis."

    stats_df = numeric_df.describe().round(2)

    summary = ["=== EDA Summary Statistics ==="]
    summary.append(stats_df.to_string())

    return "\n".join(summary)


def format_anomaly_table_for_pdf(anomalies_df: pd.DataFrame, max_rows: int = 5) -> str:
    """
    Formats an anomaly-flagged DataFrame into a clean, PDF-safe string.

    Selects only the most business-relevant columns instead of dumping all
    14+ columns, which would force Pandas to hard-wrap rows mid-line and
    render as broken garbage in a fixed-width PDF cell.
    """
    if anomalies_df.empty or "is_anomaly" not in anomalies_df.columns:
        return "No anomalies detected."

    flagged = anomalies_df[anomalies_df["is_anomaly"] == True]

    if flagged.empty:
        return "No anomalous rows to display."

    # Preferred columns — adjust these to match your actual cleaned column
    # names (post clean() normalization) if your schema differs.
    preferred_cols = ["company", "typename", "cpu", "ram", "price", "is_anomaly"]
    available_cols = [c for c in preferred_cols if c in flagged.columns]

    # Fallback: if none of the preferred columns exist, take the first 5
    # columns present plus is_anomaly, so the report still renders something.
    if not available_cols:
        available_cols = list(flagged.columns[:5])
        if "is_anomaly" not in available_cols:
            available_cols.append("is_anomaly")

    subset = flagged[available_cols].head(max_rows)

    # Safety net: disable Pandas's own width-based wrapping even though
    # the column count is already small, so nothing gets cut mid-row.
    with pd.option_context(
        "display.width", None,
        "display.max_columns", None,
        "display.max_colwidth", 20,
    ):
        table_str = subset.to_string(index=False)

    return table_str


def build_schema_description(df: pd.DataFrame, max_columns: int = 50) -> tuple[str, list]:
    """
    Builds a compact column-name + dtype summary for the LLM prompt.

    On wide datasets (e.g. enterprise tables with 100+ columns), showing
    every column would flood the context window and push out the actual
    EDA statistics. Above `max_columns`, caps the description to:
      - the highest-variance numeric columns (most likely to be analytically interesting)
      - a bounded sample of categorical columns

    Returns (description_string, list_of_columns_shown) — the column list
    is used downstream to validate the LLM's chart config against exactly
    what it was told exists, not the full (possibly unseen) schema.
    """
    all_columns = list(df.columns)

    if len(all_columns) <= max_columns:
        selected = all_columns
    else:
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = [c for c in all_columns if c not in numeric_cols]

        if numeric_cols:
            variances = df[numeric_cols].var(numeric_only=True).sort_values(ascending=False)
            top_numeric = variances.index.tolist()[: max_columns // 2]
        else:
            top_numeric = []

        remaining_budget = max_columns - len(top_numeric)
        if len(categorical_cols) <= remaining_budget:
            cat_sample = categorical_cols
        else:
            rng = np.random.default_rng(seed=42)  # deterministic sampling for reproducibility
            cat_sample = list(rng.choice(categorical_cols, size=remaining_budget, replace=False))

        selected = top_numeric + cat_sample
        print(
            f"[Warning] Dataset has {len(all_columns)} columns; capped schema "
            f"description to {len(selected)} (top-variance numeric + sampled categorical)."
        )

    lines = [f"Available columns (showing {len(selected)} of {len(all_columns)} total):"]
    for col in selected:
        dtype = str(df[col].dtype)
        kind = "numeric" if df[col].dtype.kind in "iuf" else "categorical/text"
        lines.append(f"- {col}: {dtype} ({kind})")

    return "\n".join(lines), selected