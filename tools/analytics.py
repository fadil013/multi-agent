import os
import json
import itertools
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D


def numeric_overview(df: pd.DataFrame, numeric_cols: list) -> dict:
    overview = {}
    for col in numeric_cols:
        overview[col] = {
            "sum": round(float(df[col].sum()), 2),
            "mean": round(float(df[col].mean()), 2),
            "min": round(float(df[col].min()), 2),
            "max": round(float(df[col].max()), 2),
            "std": round(float(df[col].std()), 2) if len(df[col]) > 1 else 0.0,
        }
    return overview


def category_breakdown(df: pd.DataFrame, category_cols: list, numeric_cols: list, top_n: int = 5) -> dict:
    breakdown = {}
    for cat_col in category_cols:
        breakdown[cat_col] = {}
        for num_col in numeric_cols:
            grouped = df.groupby(cat_col)[num_col].sum().sort_values(ascending=False)
            breakdown[cat_col][num_col] = {
                k: round(float(v), 2) for k, v in grouped.head(top_n).items()
            }
    return breakdown


def percent_change(old: float, new: float) -> float:
    if old == 0:
        return 0.0
    return round(((new - old) / old) * 100, 2)


def detect_trend(df: pd.DataFrame, date_col: str, numeric_cols: list) -> dict:
    trend_result = {}
    df = df.copy()
    df["_period"] = df[date_col].dt.to_period("M").astype(str)

    for num_col in numeric_cols:
        monthly = df.groupby("_period")[num_col].sum().sort_index()
        pct = monthly.pct_change().dropna() * 100

        entry = {
            "monthly_totals": {k: round(float(v), 2) for k, v in monthly.items()},
        }

        if not pct.empty:
            entry["biggest_drop"] = {
                "period": pct.idxmin(),
                "percent_change": round(float(pct.min()), 2),
            }
            entry["biggest_spike"] = {
                "period": pct.idxmax(),
                "percent_change": round(float(pct.max()), 2),
            }

        trend_result[num_col] = entry

    return trend_result


def detect_outliers(df: pd.DataFrame, numeric_cols: list, z_thresh: float = 3.0) -> dict:
    outliers = {}
    for col in numeric_cols:
        series = df[col].dropna()
        if series.std() == 0 or len(series) < 2:
            outliers[col] = {"count": 0, "values": []}
            continue

        z_scores = (series - series.mean()) / series.std()
        flagged = series[z_scores.abs() > z_thresh]

        outliers[col] = {
            "count": int(len(flagged)),
            "values": [round(float(v), 2) for v in flagged.head(10)],
        }
    return outliers


def generate_trend_chart(df: pd.DataFrame, date_col: str, numeric_col: str, output_dir: str = "charts") -> str:
    os.makedirs(output_dir, exist_ok=True)
    monthly = df.groupby(df[date_col].dt.to_period("M"))[numeric_col].sum()

    plt.figure(figsize=(10, 5))
    monthly.plot(kind="line", marker="o")
    plt.title(f"{numeric_col} Trend Over Time")
    plt.ylabel(numeric_col)
    plt.xlabel("Period")
    plt.tight_layout()

    path = os.path.join(output_dir, f"trend_{numeric_col}.png")
    plt.savefig(path)
    plt.close()
    return path


def generate_category_chart(df: pd.DataFrame, category_col: str, numeric_col: str, output_dir: str = "charts", top_n: int = 10) -> str:
    os.makedirs(output_dir, exist_ok=True)
    grouped = df.groupby(category_col)[numeric_col].sum().sort_values(ascending=False).head(top_n)

    plt.figure(figsize=(10, 5))
    grouped.plot(kind="bar")
    plt.title(f"{numeric_col} by {category_col}")
    plt.ylabel(numeric_col)
    plt.xticks(rotation=45)
    plt.tight_layout()

    path = os.path.join(output_dir, f"{numeric_col}_by_{category_col}.png")
    plt.savefig(path)
    plt.close()
    return path


def safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in str(value).lower()).strip("_")


def save_plot(path: str) -> str:
    plt.tight_layout()
    plt.savefig(path, dpi=140)
    plt.close()
    return path


def top_categories(df: pd.DataFrame, col: str, top_n: int = 10) -> list:
    return df[col].value_counts().head(top_n).index.tolist()


def generate_univariate_charts(df: pd.DataFrame, structure: dict, output_dir: str = "charts", top_n: int = 10) -> list:
    chart_paths = []
    uni_dir = os.path.join(output_dir, "univariate")
    os.makedirs(uni_dir, exist_ok=True)

    for col in structure["numeric_columns"]:
        plt.figure(figsize=(9, 5))
        plt.hist(df[col].dropna(), bins=30, edgecolor="black")
        plt.title(f"Distribution of {col}")
        plt.xlabel(col)
        plt.ylabel("Frequency")
        path = os.path.join(uni_dir, f"hist_{safe_name(col)}.png")
        chart_paths.append(save_plot(path))

    for col in structure["category_columns"]:
        counts = df[col].value_counts().head(top_n).sort_values()
        plt.figure(figsize=(10, 6))
        counts.plot(kind="barh")
        plt.title(f"Top {top_n} {col}")
        plt.xlabel("Count")
        plt.ylabel(col)
        path = os.path.join(uni_dir, f"count_{safe_name(col)}.png")
        chart_paths.append(save_plot(path))

    return chart_paths


def generate_bivariate_charts(df: pd.DataFrame, structure: dict, output_dir: str = "charts", top_n: int = 10, max_charts: int = 45) -> list:
    chart_paths = []
    bi_dir = os.path.join(output_dir, "bivariate")
    os.makedirs(bi_dir, exist_ok=True)

    for x_col, y_col in itertools.combinations(structure["numeric_columns"], 2):
        if len(chart_paths) >= max_charts:
            return chart_paths
        plt.figure(figsize=(8, 5))
        plt.scatter(df[x_col], df[y_col], alpha=0.45, s=18)
        plt.title(f"{y_col} vs {x_col}")
        plt.xlabel(x_col)
        plt.ylabel(y_col)
        path = os.path.join(bi_dir, f"scatter_{safe_name(x_col)}_vs_{safe_name(y_col)}.png")
        chart_paths.append(save_plot(path))

    for cat_col in structure["category_columns"]:
        selected = df[df[cat_col].isin(top_categories(df, cat_col, top_n))]
        for num_col in structure["numeric_columns"]:
            if len(chart_paths) >= max_charts:
                return chart_paths
            grouped = selected.groupby(cat_col)[num_col].mean().sort_values()
            plt.figure(figsize=(10, 6))
            grouped.plot(kind="barh")
            plt.title(f"Average {num_col} by {cat_col}")
            plt.xlabel(f"Average {num_col}")
            plt.ylabel(cat_col)
            path = os.path.join(bi_dir, f"bar_{safe_name(num_col)}_by_{safe_name(cat_col)}.png")
            chart_paths.append(save_plot(path))

    for x_col, hue_col in itertools.combinations(structure["category_columns"], 2):
        if len(chart_paths) >= max_charts:
            return chart_paths
        x_values = top_categories(df, x_col, min(top_n, 8))
        hue_values = top_categories(df, hue_col, min(top_n, 5))
        selected = df[df[x_col].isin(x_values) & df[hue_col].isin(hue_values)]
        table = pd.crosstab(selected[x_col], selected[hue_col])
        if table.empty:
            continue
        plt.figure(figsize=(11, 6))
        table.plot(kind="bar", stacked=True, ax=plt.gca())
        plt.title(f"{x_col} by {hue_col}")
        plt.xlabel(x_col)
        plt.ylabel("Count")
        plt.xticks(rotation=45, ha="right")
        path = os.path.join(bi_dir, f"stacked_{safe_name(x_col)}_by_{safe_name(hue_col)}.png")
        chart_paths.append(save_plot(path))

    return chart_paths


def generate_trivariate_charts(df: pd.DataFrame, structure: dict, output_dir: str = "charts", top_n: int = 8, max_charts: int = 25) -> list:
    chart_paths = []
    tri_dir = os.path.join(output_dir, "trivariate")
    os.makedirs(tri_dir, exist_ok=True)

    for hue_col in structure["category_columns"]:
        hue_values = top_categories(df, hue_col, min(top_n, 5))
        selected = df[df[hue_col].isin(hue_values)]
        for x_col, y_col in itertools.combinations(structure["numeric_columns"], 2):
            if len(chart_paths) >= max_charts:
                return chart_paths
            plt.figure(figsize=(9, 6))
            for hue_value in hue_values:
                subset = selected[selected[hue_col] == hue_value]
                plt.scatter(subset[x_col], subset[y_col], alpha=0.45, s=18, label=str(hue_value))
            plt.title(f"{y_col} vs {x_col} by {hue_col}")
            plt.xlabel(x_col)
            plt.ylabel(y_col)
            plt.legend(fontsize=8)
            path = os.path.join(tri_dir, f"scatter_{safe_name(x_col)}_vs_{safe_name(y_col)}_by_{safe_name(hue_col)}.png")
            chart_paths.append(save_plot(path))

    for cat_col in structure["category_columns"]:
        cat_values = top_categories(df, cat_col, min(top_n, 8))
        for hue_col in structure["category_columns"]:
            if cat_col == hue_col:
                continue
            hue_values = top_categories(df, hue_col, min(top_n, 5))
            selected = df[df[cat_col].isin(cat_values) & df[hue_col].isin(hue_values)]
            for num_col in structure["numeric_columns"]:
                if len(chart_paths) >= max_charts:
                    return chart_paths
                table = selected.pivot_table(index=cat_col, columns=hue_col, values=num_col, aggfunc="mean")
                if table.empty:
                    continue
                plt.figure(figsize=(11, 6))
                table.plot(kind="bar", ax=plt.gca())
                plt.title(f"Average {num_col} by {cat_col} and {hue_col}")
                plt.xlabel(cat_col)
                plt.ylabel(f"Average {num_col}")
                plt.xticks(rotation=45, ha="right")
                path = os.path.join(tri_dir, f"grouped_{safe_name(num_col)}_by_{safe_name(cat_col)}_and_{safe_name(hue_col)}.png")
                chart_paths.append(save_plot(path))

    return chart_paths


def generate_heatmaps(df: pd.DataFrame, structure: dict, output_dir: str = "charts", top_n: int = 10) -> list:
    chart_paths = []
    heatmap_dir = os.path.join(output_dir, "heatmaps")
    os.makedirs(heatmap_dir, exist_ok=True)
    numeric_cols = structure["numeric_columns"]

    if len(numeric_cols) >= 2:
        corr = df[numeric_cols].corr()
        plt.figure(figsize=(10, 8))
        plt.imshow(corr, cmap="coolwarm", vmin=-1, vmax=1)
        plt.colorbar(label="Correlation")
        plt.xticks(range(len(corr.columns)), corr.columns, rotation=45, ha="right")
        plt.yticks(range(len(corr.index)), corr.index)
        for row in range(len(corr.index)):
            for col in range(len(corr.columns)):
                plt.text(col, row, f"{corr.iloc[row, col]:.2f}", ha="center", va="center", fontsize=8)
        plt.title("Correlation Heatmap")
        path = os.path.join(heatmap_dir, "correlation_heatmap.png")
        chart_paths.append(save_plot(path))

    if structure["category_columns"] and numeric_cols:
        cat_col = structure["category_columns"][0]
        values = top_categories(df, cat_col, top_n)
        selected = df[df[cat_col].isin(values)]
        table = selected.groupby(cat_col)[numeric_cols].mean()
        if not table.empty:
            normalized = (table - table.min()) / (table.max() - table.min()).replace(0, 1)
            plt.figure(figsize=(11, 7))
            plt.imshow(normalized, cmap="viridis", aspect="auto")
            plt.colorbar(label="Normalized average")
            plt.xticks(range(len(normalized.columns)), normalized.columns, rotation=45, ha="right")
            plt.yticks(range(len(normalized.index)), normalized.index)
            plt.title(f"Average Numeric Heatmap by {cat_col}")
            path = os.path.join(heatmap_dir, f"average_numeric_by_{safe_name(cat_col)}_heatmap.png")
            chart_paths.append(save_plot(path))

    return chart_paths


def generate_3d_charts(df: pd.DataFrame, structure: dict, output_dir: str = "charts", top_n: int = 8, max_charts: int = 8) -> list:
    chart_paths = []
    maps_dir = os.path.join(output_dir, "3d")
    os.makedirs(maps_dir, exist_ok=True)
    numeric_cols = structure["numeric_columns"]

    for x_col, y_col, z_col in itertools.combinations(numeric_cols, 3):
        if len(chart_paths) >= max_charts:
            return chart_paths
        fig = plt.figure(figsize=(10, 7))
        ax = fig.add_subplot(111, projection="3d")
        color_values = df[z_col]
        plot = ax.scatter(df[x_col], df[y_col], df[z_col], c=color_values, cmap="plasma", s=18, alpha=0.65)
        ax.set_title(f"3D Map: {x_col}, {y_col}, {z_col}")
        ax.set_xlabel(x_col)
        ax.set_ylabel(y_col)
        ax.set_zlabel(z_col)
        fig.colorbar(plot, ax=ax, shrink=0.6, label=z_col)
        path = os.path.join(maps_dir, f"3d_scatter_{safe_name(x_col)}_{safe_name(y_col)}_{safe_name(z_col)}.png")
        chart_paths.append(save_plot(path))

    if len(numeric_cols) >= 1 and len(structure["category_columns"]) >= 2 and len(chart_paths) < max_charts:
        x_cat = structure["category_columns"][0]
        y_cat = structure["category_columns"][1]
        z_num = numeric_cols[0]
        x_values = top_categories(df, x_cat, top_n)
        y_values = top_categories(df, y_cat, min(top_n, 6))
        selected = df[df[x_cat].isin(x_values) & df[y_cat].isin(y_values)]
        table = selected.pivot_table(index=x_cat, columns=y_cat, values=z_num, aggfunc="mean").fillna(0)
        if not table.empty:
            xpos, ypos = np.meshgrid(np.arange(len(table.index)), np.arange(len(table.columns)), indexing="ij")
            xpos = xpos.ravel()
            ypos = ypos.ravel()
            zpos = np.zeros_like(xpos)
            dx = np.full_like(xpos, 0.5, dtype=float)
            dy = np.full_like(ypos, 0.5, dtype=float)
            dz = table.to_numpy().ravel()
            fig = plt.figure(figsize=(11, 7))
            ax = fig.add_subplot(111, projection="3d")
            ax.bar3d(xpos, ypos, zpos, dx, dy, dz, shade=True)
            ax.set_title(f"3D Bar Map: Average {z_num}")
            ax.set_xlabel(x_cat)
            ax.set_ylabel(y_cat)
            ax.set_zlabel(f"Average {z_num}")
            ax.set_xticks(np.arange(len(table.index)) + 0.25)
            ax.set_xticklabels(table.index, rotation=45, ha="right")
            ax.set_yticks(np.arange(len(table.columns)) + 0.25)
            ax.set_yticklabels(table.columns)
            path = os.path.join(maps_dir, f"3d_bar_{safe_name(z_num)}_by_{safe_name(x_cat)}_and_{safe_name(y_cat)}.png")
            chart_paths.append(save_plot(path))

    return chart_paths


def generate_charts(df: pd.DataFrame, structure: dict, output_dir: str = "charts") -> list:
    chart_paths = []

    if structure["date_columns"] and structure["numeric_columns"]:
        path = generate_trend_chart(df, structure["date_columns"][0], structure["numeric_columns"][0], output_dir)
        chart_paths.append(path)

    if structure["category_columns"] and structure["numeric_columns"]:
        path = generate_category_chart(df, structure["category_columns"][0], structure["numeric_columns"][0], output_dir)
        chart_paths.append(path)

    chart_paths.extend(generate_univariate_charts(df, structure, output_dir))
    chart_paths.extend(generate_bivariate_charts(df, structure, output_dir))
    chart_paths.extend(generate_trivariate_charts(df, structure, output_dir))
    chart_paths.extend(generate_heatmaps(df, structure, output_dir))
    chart_paths.extend(generate_3d_charts(df, structure, output_dir))

    return chart_paths


def compute_summary_stats(df: pd.DataFrame, structure: dict, top_n: int = 5) -> dict:
    summary = {
        "row_count": int(len(df)),
        "columns": {
            "date": structure["date_columns"],
            "numeric": structure["numeric_columns"],
            "category": structure["category_columns"],
        },
        "numeric_overview": numeric_overview(df, structure["numeric_columns"]),
        "category_breakdown": category_breakdown(df, structure["category_columns"], structure["numeric_columns"], top_n),
        "outliers": detect_outliers(df, structure["numeric_columns"]),
        "trend_over_time": {},
    }

    if structure["date_columns"]:
        summary["trend_over_time"] = detect_trend(df, structure["date_columns"][0], structure["numeric_columns"])

    return summary
