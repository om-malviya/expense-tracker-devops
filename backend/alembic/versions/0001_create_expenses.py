"""create expenses table

Revision ID: 0001_create_expenses
Revises: None
Create Date: 2026-10-16
"""
import sqlalchemy as sa
from alembic import op

revision = "0001_create_expenses"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "expenses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=120), nullable=False),
        # Numeric, not Float: money must be exact to the paisa/cent.
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("spent_on", sa.Date(), nullable=False),
        sa.Column("payment_method", sa.String(length=20), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        # Timestamps default on the database side so any writer (API, psql, a future job) gets them.
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    # The list filter (WHERE category = ?) and the summary (GROUP BY category) use this index.
    op.create_index("ix_expenses_category", "expenses", ["category"])
    # Month filter, "newest first" ordering and the 6-month window all range over spent_on.
    op.create_index("ix_expenses_spent_on", "expenses", ["spent_on"])


def downgrade() -> None:
    op.drop_index("ix_expenses_spent_on", table_name="expenses")
    op.drop_index("ix_expenses_category", table_name="expenses")
    op.drop_table("expenses")
