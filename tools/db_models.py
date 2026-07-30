"""SQLAlchemy ORM models for the AURA OLTP database.

Defines both business-domain tables (customers, products, sales, orders,
employees) and application tables AURA uses internally to track analysis
runs and generated reports (analysis_jobs, reports, uploaded_files).

Written using SQLAlchemy 2.0's typed declarative style (Mapped[] /
mapped_column()), which is required for annotation-based models to map
correctly under SQLAlchemy 2.x.

Owner: Danish (Agent Architecture) — coordinate schema changes with
whoever owns backend/ if this schema needs to serve the FastAPI layer too.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Shared declarative base for all AURA ORM models."""
    pass


class Customer(Base):
    """A business customer who places orders."""

    __tablename__ = "customers"

    customer_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    orders: Mapped[List["Order"]] = relationship("Order", back_populates="customer")


class Employee(Base):
    """An employee who may process orders."""

    __tablename__ = "employees"

    employee_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    hire_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    orders: Mapped[List["Order"]] = relationship("Order", back_populates="employee")


class Product(Base):
    """A sellable product / catalog item."""

    __tablename__ = "products"

    product_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    price: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    sales: Mapped[List["Sale"]] = relationship("Sale", back_populates="product")


class Order(Base):
    """A customer order, optionally processed by an employee, containing one or more sales lines."""

    __tablename__ = "orders"

    order_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("customers.customer_id"), nullable=False)
    employee_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("employees.employee_id"), nullable=True)
    order_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)

    customer: Mapped["Customer"] = relationship("Customer", back_populates="orders")
    employee: Mapped[Optional["Employee"]] = relationship("Employee", back_populates="orders")
    sales: Mapped[List["Sale"]] = relationship("Sale", back_populates="order")


class Sale(Base):
    """A single line item within an order — one product sold at a quantity/price."""

    __tablename__ = "sales"

    sale_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.order_id"), nullable=False)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.product_id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    total_price: Mapped[float] = mapped_column(Float, nullable=False)
    sale_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    order: Mapped["Order"] = relationship("Order", back_populates="sales")
    product: Mapped["Product"] = relationship("Product", back_populates="sales")


class AnalysisJob(Base):
    """
    One full AURA pipeline run for a single user objective. Created once per
    run by the Data Analyst Agent on its first task, and referenced by every
    Report generated during that run.
    """

    __tablename__ = "analysis_jobs"

    job_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_objective: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")  # running | completed | failed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    reports: Mapped[List["Report"]] = relationship("Report", back_populates="job")


class Report(Base):
    """Metadata record for a single generated report (PDF + JSON) tied to one task."""

    __tablename__ = "reports"

    report_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("analysis_jobs.job_id"), nullable=False)
    task_name: Mapped[str] = mapped_column(Text, nullable=False)
    pdf_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    json_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    job: Mapped["AnalysisJob"] = relationship("AnalysisJob", back_populates="reports")


class UploadedFile(Base):
    """Tracks files (CSV/Excel) uploaded to the system for analysis."""

    __tablename__ = "uploaded_files"

    file_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    filepath: Mapped[str] = mapped_column(String(500), nullable=False)
    uploaded_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)