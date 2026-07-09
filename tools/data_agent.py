"""Data tool - reads Excel/CSV into DataFrames for the Analyst Agent.

Owner: Ahmad
"""
from __future__ import annotations


def load_table(path: str):
    """Load an Excel or CSV file into a pandas DataFrame."""
    # TODO: use pandas.read_csv / read_excel based on the file extension
    raise NotImplementedError("Ahmad: implement table loading")


def clean(df):
    """Basic cleaning: drop empties, fix dtypes, strip whitespace."""
    # TODO: implement cleaning rules
    raise NotImplementedError
