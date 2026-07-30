"""Production-quality OLTP database layer for AURA.

Provides connection management (with dialect-aware pooling), transaction-
safe CRUD operations, and DataFrame-returning query helpers, plus small
repository classes for AURA's own application tables (analysis_jobs, reports).

Defaults to SQLite for local development/demo use. Switching to PostgreSQL
requires only setting the DATABASE_URL environment variable — no code
changes needed, since the pooling logic below already branches on dialect.

Owner: Danish (Agent Architecture)
"""
from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional

import pandas as pd
from sqlalchemy import MetaData, Table, create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from tools.db_models import AnalysisJob, Base, Report

logger = logging.getLogger(__name__)
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def _get_database_url() -> str:
    """
    Resolves the database connection string. Defaults to a local SQLite
    file so the project runs with zero external setup. To use PostgreSQL
    instead, set DATABASE_URL, e.g.:
        postgresql+psycopg2://user:password@localhost:5432/aura
    No other code changes are required — _build_engine() below already
    branches its pooling settings on the URL's dialect.
    """
    return os.getenv("DATABASE_URL", "sqlite:///aura.db")


def _build_engine(database_url: str) -> Engine:
    """
    Builds a SQLAlchemy engine with dialect-appropriate connection settings.

    SQLite: uses check_same_thread=False since LangGraph nodes may run on a
    different thread than the one that created the engine. SQLite doesn't
    benefit from a networked-style connection pool.

    PostgreSQL (or any other networked DB): uses a bounded QueuePool with
    pre-ping enabled, so stale connections are detected and replaced
    automatically instead of surfacing as a runtime error mid-query.
    """
    connect_args: Dict[str, Any] = {}
    engine_kwargs: Dict[str, Any] = {}

    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    else:
        engine_kwargs.update(
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=1800,  # recycle connections every 30 min to avoid stale-connection errors
        )

    return create_engine(database_url, connect_args=connect_args, **engine_kwargs)


class DatabaseManager:
    """
    Central point of access to the OLTP database. Owns the engine and
    session factory, exposes transaction-safe CRUD helpers, and returns
    query results as pandas DataFrames for direct use by the analytics
    pipeline.
    """

    def __init__(self, database_url: Optional[str] = None, auto_create_tables: bool = True) -> None:
        """
        Args:
            database_url: SQLAlchemy connection string. Defaults to the
                DATABASE_URL environment variable, or a local SQLite file
                if unset.
            auto_create_tables: If True, calls init_db() immediately so a
                fresh SQLite file gets its schema created automatically.
                create_all() is idempotent (skips tables that already
                exist), so this is safe for local/dev use. For a production
                PostgreSQL deployment, schema management should instead go
                through a migration tool (e.g. Alembic), and this should be
                set to False.
        """
        self.database_url = database_url or _get_database_url()
        self.engine: Engine = _build_engine(self.database_url)
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)

        logger.info("DatabaseManager initialized (dialect=%s)", self.engine.dialect.name)

        if auto_create_tables:
            self.init_db()

    def init_db(self) -> None:
        """Creates all tables defined in db_models.py if they don't already exist."""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database schema verified/created.")
        except SQLAlchemyError:
            logger.exception("Failed to initialize database schema.")
            raise

    @contextmanager
    def session_scope(self) -> Iterator[Session]:
        """
        Provides a transactional session scope: commits on success, rolls
        back and re-raises on any exception, and always closes the session
        — callers never need to manage session lifecycle themselves.
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            logger.exception("Transaction rolled back due to an error.")
            raise
        finally:
            session.close()

    def fetch_table(self, table_name: str, limit: Optional[int] = None) -> pd.DataFrame:
        """
        Fetches an entire table (optionally capped by `limit`) as a pandas
        DataFrame — the primary entry point the Data Analyst Agent uses
        when data_source is "database" and a table name is given.
        """
        query = f"SELECT * FROM {table_name}"
        if limit is not None:
            query += f" LIMIT {int(limit)}"
        return self.execute_query(query)

    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """
        Executes a raw SELECT query and returns the result as a DataFrame.
        Used both by fetch_table() and directly when the Data Analyst Agent
        is given a custom database_query instead of a table name.
        """
        try:
            with self.engine.connect() as conn:
                df = pd.read_sql(text(query), conn, params=params or {})
            logger.info("Query executed successfully, returned %d rows.", len(df))
            return df
        except SQLAlchemyError:
            logger.exception("Query execution failed: %s", query)
            raise

    def insert_rows(self, table_name: str, records: List[Dict[str, Any]]) -> int:
        """
        Inserts one or more rows into an arbitrary table by name (reflected
        at call time, so this works for any table in the schema without a
        dedicated ORM class per table). Returns the number of rows inserted.
        """
        if not records:
            return 0

        try:
            table = Table(table_name, MetaData(), autoload_with=self.engine)
            with self.session_scope() as session:
                session.execute(table.insert(), records)
            logger.info("Inserted %d row(s) into '%s'.", len(records), table_name)
            return len(records)
        except SQLAlchemyError:
            logger.exception("Insert failed for table '%s'.", table_name)
            raise

    def update_rows(self, table_name: str, filters: Dict[str, Any], updates: Dict[str, Any]) -> int:
        """
        Updates rows matching `filters` (column=value equality conditions,
        ANDed together) with the values in `updates`. Returns rows affected.
        """
        if not updates:
            raise ValueError("update_rows() requires at least one field in 'updates'.")

        try:
            table = Table(table_name, MetaData(), autoload_with=self.engine)
            stmt = table.update()
            for column, value in filters.items():
                stmt = stmt.where(table.c[column] == value)
            stmt = stmt.values(**updates)

            with self.session_scope() as session:
                result = session.execute(stmt)
                affected = result.rowcount

            logger.info("Updated %d row(s) in '%s'.", affected, table_name)
            return affected
        except SQLAlchemyError:
            logger.exception("Update failed for table '%s'.", table_name)
            raise

    def delete_rows(self, table_name: str, filters: Dict[str, Any]) -> int:
        """
        Deletes rows matching `filters` (column=value equality conditions,
        ANDed together). Returns rows affected. Refuses to run with empty
        filters to prevent an accidental full-table delete.
        """
        if not filters:
            raise ValueError("delete_rows() requires at least one filter to avoid deleting an entire table.")

        try:
            table = Table(table_name, MetaData(), autoload_with=self.engine)
            stmt = table.delete()
            for column, value in filters.items():
                stmt = stmt.where(table.c[column] == value)

            with self.session_scope() as session:
                result = session.execute(stmt)
                affected = result.rowcount

            logger.info("Deleted %d row(s) from '%s'.", affected, table_name)
            return affected
        except SQLAlchemyError:
            logger.exception("Delete failed for table '%s'.", table_name)
            raise

    def close(self) -> None:
        """Disposes of the engine's connection pool, releasing all connections."""
        self.engine.dispose()
        logger.info("Database engine disposed and connections released.")


class AnalysisJobRepository:
    """
    Repository for AnalysisJob records — tracks one row per full AURA
    pipeline run (one user objective), independent of how many tasks it
    breaks into.
    """

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db_manager = db_manager

    def create_job(self, user_objective: str) -> int:
        """Creates a new AnalysisJob row and returns its generated job_id."""
        with self.db_manager.session_scope() as session:
            job = AnalysisJob(
                user_objective=user_objective,
                status="running",
                created_at=datetime.utcnow(),
            )
            session.add(job)
            session.flush()  # populate job.job_id before the session closes
            job_id = job.job_id

        logger.info("Created AnalysisJob id=%d.", job_id)
        return job_id

    def mark_completed(self, job_id: int, status: str = "completed") -> None:
        """Marks an existing AnalysisJob as finished (completed or failed)."""
        with self.db_manager.session_scope() as session:
            job = session.query(AnalysisJob).filter_by(job_id=job_id).first()
            if job is None:
                logger.warning("AnalysisJob id=%d not found; cannot mark as %s.", job_id, status)
                return
            job.status = status
            job.completed_at = datetime.utcnow()

        logger.info("AnalysisJob id=%d marked as '%s'.", job_id, status)


class ReportRepository:
    """
    Repository for Report metadata records — one row per PDF/JSON report
    generated by the Data Analyst Agent for a single task.
    """

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db_manager = db_manager

    def create_report(
        self,
        job_id: int,
        task_name: str,
        pdf_path: Optional[str],
        json_path: Optional[str],
    ) -> int:
        """Records a generated report's metadata and returns its report_id."""
        with self.db_manager.session_scope() as session:
            report = Report(
                job_id=job_id,
                task_name=task_name,
                pdf_path=pdf_path,
                json_path=json_path,
                created_at=datetime.utcnow(),
            )
            session.add(report)
            session.flush()
            report_id = report.report_id

        logger.info("Recorded Report id=%d for job_id=%d.", report_id, job_id)
        return report_id


# Module-level singleton so the whole application shares one engine/connection
# pool instead of every import spinning up a fresh one.
#
# Wrapped in a try/except so that an unreachable database at import time
# doesn't crash the entire program — analyst_node() itself will surface a
# clear, catchable error the moment it actually tries to use the database
# (e.g. when data_source == "database"), rather than the whole app failing
# to even start.
try:
    db_manager = DatabaseManager()
    analysis_job_repo = AnalysisJobRepository(db_manager)
    report_repo = ReportRepository(db_manager)
except Exception:
    logger.exception(
        "Failed to initialize the database connection at import time. "
        "The application will continue to load, but any database-backed "
        "operation (data_source='database', job/report tracking) will fail "
        "until this is resolved."
    )
    db_manager = None
    analysis_job_repo = None
    report_repo = None

    
def fetch_table(table_name: str, limit: Optional[int] = None) -> pd.DataFrame:
    """Module-level convenience wrapper around the shared DatabaseManager instance."""
    return db_manager.fetch_table(table_name, limit=limit)


def execute_query(query: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    """Module-level convenience wrapper around the shared DatabaseManager instance."""
    return db_manager.execute_query(query, params=params)