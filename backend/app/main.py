import logging
from calendar import monthrange
from contextlib import asynccontextmanager
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from .config import settings
from .db import Base, engine, get_db
from .models import Expense
from .schemas import Category, ExpenseCreate, ExpenseOut, ExpenseUpdate, SummaryOut

API_VERSION = "1.0.0"
logging.basicConfig(level=settings.log_level.upper())
log = logging.getLogger("expense-tracker")


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Schema management belongs to Alembic (the container runs `alembic upgrade head` before
    # uvicorn). create_all is used ONLY for the test environment so the pytest suite can run
    # against a throw-away SQLite file without needing the migration tooling.
    if settings.app_env == "test":
        Base.metadata.create_all(bind=engine)
    log.info("%s starting (env=%s)", settings.app_name, settings.app_env)
    yield


app = FastAPI(title=settings.app_name, version=API_VERSION, lifespan=lifespan)

# CORS is restricted to the configured origins and to the verbs the API actually uses.
# A wildcard would be flagged by SAST tooling and is not needed behind the nginx proxy.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)

# Exposes http_requests_total / http_request_duration_seconds for Prometheus (module M9).
Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

NOT_FOUND = "Expense not found"
TWO_PLACES = Decimal("0.01")


def _money(value) -> Decimal:
    """Normalise a SQL aggregate (None / int / float / Decimal) to a 2-dp Decimal."""
    return Decimal(str(value or 0)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def _month_bounds(month: str) -> tuple[date, date]:
    """Turn 'YYYY-MM' into (first day, last day); raises 422 on nonsense such as 2026-13."""
    try:
        year, mon = (int(part) for part in month.split("-"))
        first = date(year, mon, 1)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="month must be YYYY-MM") from exc
    return first, date(year, mon, monthrange(year, mon)[1])


def _month_expr(db: Session):
    """SQL expression yielding 'YYYY-MM' for spent_on. Date formatting is dialect specific, so
    I pick the function based on the connected database instead of post-processing in Python."""
    if db.get_bind().dialect.name == "sqlite":
        return func.strftime("%Y-%m", Expense.spent_on)
    return func.to_char(Expense.spent_on, "YYYY-MM")


def _column_values(payload: ExpenseCreate | ExpenseUpdate, **dump_kwargs) -> dict:
    """model_dump() keeps Decimal/date intact (unlike mode='json') but leaves the enum members;
    the DB columns are plain strings, so enums are unwrapped to their .value here."""
    return {k: (v.value if isinstance(v, Enum) else v) for k, v in payload.model_dump(**dump_kwargs).items()}


def _get_or_404(db: Session, expense_id: int) -> Expense:
    expense = db.get(Expense, expense_id)
    if expense is None:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    return expense


@app.get("/")
def root():
    return {"service": settings.app_name, "env": settings.app_env, "version": API_VERSION}


@app.get("/health")
def health():
    """Liveness probe: no DB access on purpose, so a DB outage does not get the pod restarted."""
    return {"status": "UP"}


@app.get("/ready")
def ready(db: Session = Depends(get_db)):
    """Readiness probe: a real round-trip to the database. 503 takes the pod out of the Service."""
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - any driver error means "not ready"
        log.warning("readiness check failed: %s", exc)
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"status": "NOT_READY"})
    return {"status": "READY"}


@app.get("/api/expenses", response_model=list[ExpenseOut])
def list_expenses(
    db: Session = Depends(get_db),
    category: Category | None = None,
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$", description="YYYY-MM"),
    q: str | None = Query(default=None, max_length=120, description="case-insensitive title search"),
):
    stmt = select(Expense)
    if category is not None:
        stmt = stmt.where(Expense.category == category.value)
    if month:
        first, last = _month_bounds(month)
        stmt = stmt.where(Expense.spent_on.between(first, last))
    if q:
        stmt = stmt.where(Expense.title.ilike(f"%{q}%"))
    # Newest spending first; id breaks ties so the order is stable for same-day entries.
    stmt = stmt.order_by(Expense.spent_on.desc(), Expense.id.desc())
    return list(db.scalars(stmt))


# NOTE: this route is declared BEFORE /api/expenses/{expense_id}; otherwise FastAPI would try
# to parse the literal "summary" as an integer id and answer 422.
@app.get("/api/expenses/summary", response_model=SummaryOut)
def summary(db: Session = Depends(get_db)):
    """Dashboard figures. Everything is aggregated by the database (SUM/COUNT/GROUP BY) rather
    than by loading rows into Python, so the cost stays flat as the table grows."""
    today = date.today()
    month_start = today.replace(day=1)

    total, count = db.execute(select(func.coalesce(func.sum(Expense.amount), 0), func.count(Expense.id))).one()

    by_category = [
        {"category": cat, "total": _money(cat_total), "count": cat_count}
        for cat, cat_total, cat_count in db.execute(
            select(Expense.category, func.sum(Expense.amount), func.count(Expense.id))
            .group_by(Expense.category)
            .order_by(func.sum(Expense.amount).desc(), Expense.category)
        )
    ]

    # Last six calendar months (including the current one), oldest first. Months with no
    # spending are filled with 0 so the frontend chart always has six points.
    window_year, window_month = today.year, today.month - 5
    if window_month <= 0:
        window_year, window_month = window_year - 1, window_month + 12
    window_start = date(window_year, window_month, 1)
    month_expr = _month_expr(db)
    month_rows = dict(
        db.execute(
            select(month_expr, func.sum(Expense.amount)).where(Expense.spent_on >= window_start).group_by(month_expr)
        ).all()
    )
    by_month = []
    year, mon = window_start.year, window_start.month
    for _ in range(6):
        key = f"{year:04d}-{mon:02d}"
        by_month.append({"month": key, "total": _money(month_rows.get(key))})
        year, mon = (year + 1, 1) if mon == 12 else (year, mon + 1)

    this_month_total = _money(
        db.execute(
            select(func.coalesce(func.sum(Expense.amount), 0)).where(Expense.spent_on.between(month_start, today))
        ).scalar_one()
    )
    # Average over the days elapsed so far (not the whole month) so the figure is a real daily burn rate.
    average_per_day = (this_month_total / Decimal(today.day)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

    return SummaryOut(
        total=_money(total),
        count=count,
        by_category=by_category,
        by_month=by_month,
        top_category=by_category[0]["category"] if by_category else None,
        this_month_total=this_month_total,
        average_per_day_this_month=average_per_day,
    )


@app.get("/api/expenses/{expense_id}", response_model=ExpenseOut)
def get_expense(expense_id: int, db: Session = Depends(get_db)):
    return _get_or_404(db, expense_id)


@app.post("/api/expenses", response_model=ExpenseOut, status_code=status.HTTP_201_CREATED)
def create_expense(payload: ExpenseCreate, db: Session = Depends(get_db)):
    expense = Expense(**_column_values(payload))
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


@app.put("/api/expenses/{expense_id}", response_model=ExpenseOut)
def update_expense(expense_id: int, payload: ExpenseUpdate, db: Session = Depends(get_db)):
    expense = _get_or_404(db, expense_id)
    # exclude_unset => only the fields the client actually sent are touched (partial update).
    for key, value in _column_values(payload, exclude_unset=True).items():
        setattr(expense, key, value)
    db.commit()
    db.refresh(expense)
    return expense


@app.delete("/api/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(expense_id: int, db: Session = Depends(get_db)):
    expense = _get_or_404(db, expense_id)
    db.delete(expense)
    db.commit()
