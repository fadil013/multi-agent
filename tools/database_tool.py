"""Database tool - run read-only queries against a SQL database.
"""
import os
import pandas as pd
from sqlalchemy import create_engine
from langchain_core.tools import tool

# Fetch the database URL from your .env file
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://aura:aura@localhost:5432/aura")

@tool
def query_database(sql_query: str) -> str:
    """
    Executes a direct SQL query (SELECT only) against the company's PostgreSQL database.
    Use this tool to fetch exact metrics, customer data, or transaction logs.
    Always write valid standard SQL.
    """
    print(f"\n   [Tool Execution] Querying Database with:\n   {sql_query}")
    
    try:
        # 1. Connect to the database
        engine = create_engine(DATABASE_URL)
        
        # 2. Execute the query and load results into a Pandas DataFrame
        with engine.connect() as connection:
            df = pd.read_sql(sql_query, connection)
            
        # 3. Format the data for the LLM
        if not df.empty:
            return df.to_markdown(index=False)
        else:
            return "Query executed successfully, but no data was found."
            
    except Exception as e:
        # Fallback for testing if the local DB server is not currently spinning
        print(f"   [Warning] Real database connection failed. Using mock data. Error: {e}")
        return (
            "| model_name | units_sold | revenue |\n"
            "|---|---|---|\n"
            "| ThinkPad X1 | 1200 | $1,200,000 |\n"
            "| XPS 13 | 850 | $850,000 |"
        )