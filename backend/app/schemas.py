from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer


class Category(StrEnum):
    food = "food"
    transport = "transport"
    housing = "housing"
    utilities = "utilities"
    health = "health"
    entertainment = "entertainment"
    shopping = "shopping"
    education = "education"
    other = "other"


class PaymentMethod(StrEnum):
    cash = "cash"
    card = "card"
    upi = "upi"
    bank_transfer = "bank_transfer"
    other = "other"


# Money is validated as a Decimal (exact, max 2 decimal places, fits Numeric(10,2)) but is
# serialised to a JSON number instead of Pydantic's default string, so the React frontend can
# use the value directly without parsing.
Money = Annotated[
    Decimal,
    Field(gt=0, max_digits=10, decimal_places=2),
    PlainSerializer(lambda v: float(v), return_type=float, when_used="json"),
]
# Aggregates may legitimately be 0 (empty database), so they have no "> 0" rule.
MoneyTotal = Annotated[Decimal, PlainSerializer(lambda v: float(v), return_type=float, when_used="json")]


class ExpenseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120, examples=["Groceries"])
    amount: Money
    category: Category
    spent_on: date
    payment_method: PaymentMethod
    note: str | None = Field(default=None, max_length=1000)


class ExpenseUpdate(BaseModel):
    """Partial update: every field is optional and only the ones present in the request body are applied."""

    title: str | None = Field(default=None, min_length=1, max_length=120)
    amount: Money | None = None
    category: Category | None = None
    spent_on: date | None = None
    payment_method: PaymentMethod | None = None
    note: str | None = Field(default=None, max_length=1000)


class ExpenseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    amount: Money
    category: Category
    spent_on: date
    payment_method: PaymentMethod
    note: str | None
    created_at: datetime
    updated_at: datetime


class CategoryTotal(BaseModel):
    category: str
    total: MoneyTotal
    count: int


class MonthTotal(BaseModel):
    month: str  # YYYY-MM
    total: MoneyTotal


class SummaryOut(BaseModel):
    total: MoneyTotal
    count: int
    by_category: list[CategoryTotal]
    by_month: list[MonthTotal]
    top_category: str | None
    this_month_total: MoneyTotal
    average_per_day_this_month: MoneyTotal
