"""Analytics tool - pattern detection and dynamic chart generation.

Owner: Danish
"""
from __future__ import annotations
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os


def generate_dynamic_charts(df: pd.DataFrame, chart_configs: list, output_dir: str = "output") -> list:
    """
    Takes a JSON list of chart configurations from an LLM and renders highly
    readable, styled PNGs.

    output_dir should be a unique folder per task/run (e.g. "output/task_1")
    when this is called multiple times in one program invocation — otherwise
    chart PNGs from one task (e.g. plot_1_scatter.png) get overwritten by
    the next task's charts using the same filename pattern.

    Supported chart_types and their required config fields:

    - "scatter": requires x_column, y_column. Optional hue (grouping column).
    - "histogram": requires column. Distribution of a single numeric column.
    - "bar": requires x_column, y_column. Optional aggregation
      ("mean" | "sum" | "median" | "count" | "min" | "max"), defaults to "mean".
      Categories are capped to the top 15 by aggregated value for readability.
    - "line": requires y_column. x_column is optional — if the DataFrame has
      a datetime column, it's preferred automatically for the x-axis over
      whatever x_column was given. Falls back to the provided x_column if
      no datetime column exists.
    - "box": either a single `column` (simple distribution/outlier box plot),
      or `x_column` + `y_column` for a grouped box plot. Optional hue for a
      further sub-grouping within a grouped box plot.
    - "heatmap": no column fields required — automatically uses ALL numeric
      columns in the DataFrame to build a correlation matrix.
    - "countplot": requires `column` (categorical). Shows frequency counts.
      Optional hue for a grouped/stacked count comparison. Capped to top 15
      categories by frequency.

    On any missing/invalid column reference, a warning is printed and that
    specific chart is skipped — the rest of the chart_configs list still
    processes normally.
    """
    if df.empty or not chart_configs:
        return []

    os.makedirs(output_dir, exist_ok=True)
    chart_paths = []

    plt.style.use('ggplot')
    sns.set_theme(context="talk", style="whitegrid")

    for i, config in enumerate(chart_configs):
        chart_type = config.get("chart_type", "").lower()
        fig, ax = plt.subplots(figsize=(10, 6), dpi=300)

        try:
            if chart_type == "scatter":
                x_col = config["x_column"]
                y_col = config["y_column"]
                hue_col = config.get("hue")

                if hue_col and hue_col in df.columns:
                    sns.scatterplot(data=df, x=x_col, y=y_col, hue=hue_col, ax=ax, alpha=0.7)
                    ax.legend(loc="best", fontsize="small", title_fontsize="small")
                else:
                    sns.scatterplot(data=df, x=x_col, y=y_col, ax=ax, color="#E24A33", alpha=0.7)

            elif chart_type == "histogram":
                col = config["column"]
                sns.histplot(data=df, x=col, ax=ax, color="#348ABD", kde=True)

            elif chart_type == "bar":
                x_col = config["x_column"]
                y_col = config["y_column"]
                agg_method = config.get("aggregation", "mean").lower()
                if agg_method not in ("mean", "sum", "median", "count", "min", "max"):
                    print(f"[Warning] Unsupported aggregation '{agg_method}' in Chart {i+1}, defaulting to mean.")
                    agg_method = "mean"

                agg_df = df.groupby(x_col)[y_col].agg(agg_method).reset_index()
                agg_df = agg_df.sort_values(by=y_col, ascending=False).head(15)

                sns.barplot(data=agg_df, x=x_col, y=y_col, ax=ax, color="#988ED5")
                plt.xticks(rotation=45, ha='right')

            elif chart_type == "line":
                y_col = config["y_column"]

                datetime_cols = df.select_dtypes(include=["datetime", "datetimetz"]).columns.tolist()

                if datetime_cols:
                    x_col = datetime_cols[0]
                    if config.get("x_column") and config["x_column"] != x_col:
                        print(
                            f"[Info] Chart {i+1} ('line'): using detected datetime column "
                            f"'{x_col}' instead of requested x_column '{config['x_column']}'."
                        )
                else:
                    x_col = config.get("x_column")
                    if not x_col:
                        print(f"[Warning] Chart {i+1} ('line'): no datetime column found and no x_column provided — skipping.")
                        plt.close(fig)
                        continue

                if x_col not in df.columns or y_col not in df.columns:
                    print(f"[Warning] Chart {i+1} ('line'): column(s) not found — skipping.")
                    plt.close(fig)
                    continue

                plot_df = df[[x_col, y_col]].dropna().sort_values(by=x_col)
                sns.lineplot(data=plot_df, x=x_col, y=y_col, ax=ax, marker="o", color="#2C3E50")
                if plot_df[x_col].dtype.kind not in "iuf":
                    plt.xticks(rotation=45, ha='right')

            elif chart_type == "box":
                x_col = config.get("x_column")
                y_col = config.get("y_column")
                single_col = config.get("column")
                hue_col = config.get("hue")

                if x_col and y_col:
                    if x_col not in df.columns or y_col not in df.columns:
                        print(f"[Warning] Chart {i+1} ('box'): column(s) not found — skipping.")
                        plt.close(fig)
                        continue

                    if hue_col and hue_col in df.columns:
                        sns.boxplot(data=df, x=x_col, y=y_col, hue=hue_col, ax=ax)
                        ax.legend(loc="best", fontsize="small", title_fontsize="small")
                    else:
                        sns.boxplot(data=df, x=x_col, y=y_col, ax=ax, color="#59A14F")
                    plt.xticks(rotation=45, ha='right')

                elif single_col:
                    if single_col not in df.columns:
                        print(f"[Warning] Chart {i+1} ('box'): column '{single_col}' not found — skipping.")
                        plt.close(fig)
                        continue
                    sns.boxplot(data=df, y=single_col, ax=ax, color="#59A14F")

                else:
                    print(f"[Warning] Chart {i+1} ('box'): needs either 'column', or both 'x_column' and 'y_column' — skipping.")
                    plt.close(fig)
                    continue

            elif chart_type == "heatmap":
                numeric_df = df.select_dtypes(include=["number"])

                if numeric_df.shape[1] < 2:
                    print(f"[Warning] Chart {i+1} ('heatmap'): need at least 2 numeric columns, found {numeric_df.shape[1]} — skipping.")
                    plt.close(fig)
                    continue

                corr = numeric_df.corr()
                sns.heatmap(
                    corr, annot=True, fmt=".2f", cmap="coolwarm",
                    vmin=-1, vmax=1, ax=ax, square=True,
                    annot_kws={"size": 8}, cbar_kws={"shrink": 0.8}
                )
                plt.xticks(rotation=45, ha='right')
                plt.yticks(rotation=0)

            elif chart_type == "countplot":
                col = config.get("column")
                hue_col = config.get("hue")

                if not col or col not in df.columns:
                    print(f"[Warning] Chart {i+1} ('countplot'): column '{col}' not found — skipping.")
                    plt.close(fig)
                    continue

                top_categories = df[col].value_counts().head(15).index
                plot_df = df[df[col].isin(top_categories)]

                if hue_col and hue_col in df.columns:
                    sns.countplot(data=plot_df, x=col, hue=hue_col, ax=ax, order=top_categories)
                    ax.legend(loc="best", fontsize="small", title_fontsize="small")
                else:
                    sns.countplot(data=plot_df, x=col, ax=ax, color="#E8A33D", order=top_categories)

                plt.xticks(rotation=45, ha='right')

            else:
                print(f"[Warning] Unsupported chart type requested: {chart_type}")
                plt.close(fig)
                continue

            ax.set_title(config.get("title", f"Chart {i+1}"), pad=15, fontweight='bold')
            plt.tight_layout()

            filepath = os.path.join(output_dir, f"plot_{i+1}_{chart_type}.png")
            fig.savefig(filepath)
            chart_paths.append(filepath)

        except KeyError as e:
            print(f"[Warning] Chart {i+1} missing required field: {e}")
        except Exception as e:
            print(f"[Error] Failed to render Chart {i+1}: {e}")
        finally:
            plt.close(fig)

    return chart_paths