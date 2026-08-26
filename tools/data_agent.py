import os
import pandas as pd
import numpy as np


def available_input_files(folder: str = ".") -> list:
    files = []
    for name in os.listdir(folder):
        path = os.path.join(folder, name)
        if os.path.isfile(path) and os.path.splitext(name)[1].lower() in (".csv", ".xlsx", ".xls"):
            files.append(path)
    return files


def load_file(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        choices = available_input_files()
        if choices:
            raise FileNotFoundError(f"File not found: {path}. Available files: {choices}")
        raise FileNotFoundError(f"File not found: {path}. Put data.csv or another CSV/Excel file in this folder.")

    ext = os.path.splitext(path)[1].lower()

    if ext == ".csv":
        last_error = None
        for encoding in ("utf-8", "utf-8-sig", "cp1252", "latin1"):
            try:
                df = pd.read_csv(path, encoding=encoding)
                break
            except UnicodeDecodeError as error:
                last_error = error
        else:
            raise last_error
    elif ext in (".xlsx", ".xls"):
        df = pd.read_excel(path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    if df.empty:
        raise ValueError("Uploaded file is empty.")

    return df


def detect_structure(df: pd.DataFrame) -> dict:
    date_cols, numeric_cols, category_cols, id_cols = [], [], [], []

    for col in df.columns:
        series = df[col]

        if pd.api.types.is_datetime64_any_dtype(series):
            date_cols.append(col)
            continue

        name_hint = any(k in col.lower() for k in ["date", "time", "timestamp", "day", "month", "year"])

        if name_hint or series.dtype == "object":
            sample = series.dropna().astype(str).head(20)
            if len(sample) > 0:
                parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
                if parsed.notna().mean() > 0.8:
                    date_cols.append(col)
                    continue

        if pd.api.types.is_numeric_dtype(series):
            numeric_cols.append(col)
            continue

        n_unique = series.nunique(dropna=True)
        n_rows = len(series)
        if n_rows > 0 and (n_unique / n_rows) > 0.9 and n_unique > 20:
            id_cols.append(col)
        else:
            category_cols.append(col)

    return {
        "date_columns": date_cols,
        "numeric_columns": numeric_cols,
        "category_columns": category_cols,
        "id_columns": id_cols,
    }


def clean_data(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    df = df.copy()

    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    structure = detect_structure(df)

    df = df.drop_duplicates()

    for col in structure["date_columns"]:
        df[col] = pd.to_datetime(df[col], errors="coerce", format="mixed")

    for col in structure["numeric_columns"]:
        if df[col].dtype == "object":
            df[col] = df[col].astype(str).str.replace(",", "", regex=False)
        df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in structure["category_columns"]:
        df[col] = df[col].astype(str).str.strip().str.title()
        df[col] = df[col].replace({"Nan": np.nan, "None": np.nan, "": np.nan})

    for col in structure["numeric_columns"]:
        if df[col].isna().any():
            df[col] = df[col].fillna(df[col].mean())

    for col in structure["category_columns"]:
        if df[col].isna().any():
            df[col] = df[col].fillna("Unknown")

    df = df.dropna(how="all")

    for col in structure["date_columns"]:
        df = df[df[col].notna()]

    return df, structure


def analyze(file_path: str) -> dict:
    try:
        from tools.analytics import compute_summary_stats, generate_charts
    except ImportError:  # pragma: no cover - supports running this file from tools/
        from analytics import compute_summary_stats, generate_charts

    df = load_file(file_path)
    df, structure = clean_data(df)
    summary = compute_summary_stats(df, structure)
    charts = generate_charts(df, structure)

    return {
        "structure": structure,
        "summary": summary,
        "charts": charts,
    }


if __name__ == "__main__":
    import sys
    import json

    path = sys.argv[1] if len(sys.argv) > 1 else "data.csv"
    try:
        result = analyze(path)
    except Exception as error:
        print("Error:", error)
        sys.exit(1)
    os.makedirs("reports", exist_ok=True)
    output_path = os.path.join("reports", "analysis_result.json")
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(result, file, indent=2, default=str)
    print("Analysis complete")
    print("Rows:", result["summary"]["row_count"])
    print("Numeric columns:", len(result["structure"]["numeric_columns"]))
    print("Category columns:", len(result["structure"]["category_columns"]))
    print("Date columns:", len(result["structure"]["date_columns"]))
    print("Charts saved:", len(result["charts"]))
    print("Result file:", output_path)
