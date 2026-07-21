"""Analytics tool - pattern detection and chart generation."""
from __future__ import annotations
import pandas as pd
import matplotlib.pyplot as plt
import os


def make_chart(df: pd.DataFrame, kind: str = "histogram", x_col: str = None, y_col: str = None, path: str = "chart.png") -> str:
    """Generate a chart and return the saved file path."""
    if df.empty:
        raise ValueError("Cannot generate chart: DataFrame is empty.")

    plot_df = df.copy()

    # Automatically drop garbage index columns (like 'unnamed_0' or 'id')
    garbage_cols = [c for c in plot_df.columns if 'unnamed' in str(c).lower() or str(c).lower() == 'id']
    plot_df = plot_df.drop(columns=garbage_cols)

    text_cols = plot_df.select_dtypes(include=['object', 'string']).columns.tolist()
    numeric_cols = plot_df.select_dtypes(include=['number']).columns.tolist()

    if len(numeric_cols) == 0:
        raise ValueError("No numeric columns available to plot.")

    # Heatmap specifically needs at least 2 numeric columns to build a correlation matrix
    if kind == "heatmap" and len(numeric_cols) < 2:
        raise ValueError(
            f"Cannot generate heatmap: need at least 2 numeric columns, found {len(numeric_cols)}."
        )

    fig, ax = plt.subplots(figsize=(10, 6))

    # --- SMART PLOTTING LOGIC ---
    if kind in ["hist", "histogram"]:
        # Histogram should only plot ONE variable to prevent scale squashing.
        # If x_col isn't specified, intelligently default to the LAST numeric column
        target = x_col if x_col and x_col in numeric_cols else numeric_cols[-1]

        plot_df[target].plot(kind='hist', bins=20, alpha=0.7, ax=ax, color='#2c3e50')
        ax.set_xlabel(target.capitalize())
        plt.title(f"Distribution of {target.capitalize()}")

    elif kind == "scatter":
        # Scatter needs exactly 2 variables
        x = x_col if x_col and x_col in numeric_cols else numeric_cols[0]
        y = y_col if y_col and y_col in numeric_cols else numeric_cols[-1]

        # Prevent plotting a variable against itself if not specified
        if x == y and len(numeric_cols) > 1:
            y = numeric_cols[1]

        plot_df.plot(kind='scatter', x=x, y=y, ax=ax, s=60, alpha=0.7, color='#e74c3c')
        plt.title(f"Scatter: {x.capitalize()} vs {y.capitalize()}")

    elif kind == "heatmap":
        # Generates a visual correlation matrix
        corr = plot_df[numeric_cols].corr()
        cax = ax.matshow(corr, cmap='coolwarm', vmin=-1, vmax=1)
        fig.colorbar(cax)

        # Fix the labels for the heatmap
        ax.set_xticks(range(len(corr.columns)))
        ax.set_yticks(range(len(corr.columns)))
        ax.set_xticklabels(corr.columns, rotation=45, ha='left')
        ax.set_yticklabels(corr.columns)
        plt.title("Correlation Heatmap", pad=20)

    else:  # Default Bar or Line
        # Use a text column for the X-axis labels to make it readable
        if x_col and x_col in text_cols:
            plot_df = plot_df.set_index(x_col)
        elif len(text_cols) > 0:
            plot_df = plot_df.set_index(text_cols[0])

        # Target specific Y columns, or plot all remaining numeric if none specified
        y = [y_col] if y_col and y_col in numeric_cols else numeric_cols

        if kind == "bar":
            plot_df[y].head(15).plot(kind='bar', ax=ax)
        else:
            plot_df[y].plot(kind='line', marker='o', ax=ax)
        plt.title(f"Data Insight: {kind.capitalize()} Chart")

    plt.tight_layout()

    # Save the file safely
    save_dir = os.path.dirname(path)
    if save_dir:
        os.makedirs(save_dir, exist_ok=True)

    absolute_path = os.path.abspath(path)
    plt.savefig(absolute_path)
    plt.close()

    return absolute_path