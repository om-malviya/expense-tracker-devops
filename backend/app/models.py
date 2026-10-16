from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Expense(Base):
    """One spending record. The table is created by Alembic (alembic/versions/0001_create_expenses.py);
    this mapping must stay in sync with that migration."""

    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    # Numeric(10, 2) instead of Float: money must not suffer binary floating-point rounding.
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    # category and spent_on are indexed because every list filter and the summary
    # aggregation (GROUP BY category, range on spent_on) hits them.
    category: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    spent_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    payment_method: Mapped[str] = mapped_column(String(20), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Timestamps are set by the database (server_default) so they are correct no matter which
    # client writes the row; updated_at is refreshed by SQLAlchemy on every UPDATE.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
