"""API tests for the Expense Tracker backend.

They run against a temporary SQLite database (see conftest.py) and cover every endpoint:
/, /health, /ready, /metrics and the full CRUD + summary surface under /api/expenses.
"""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal


def _expense(**overrides):
    base = {
        "title": "Metro card top-up",
        "amount": "120.00",
        "category": "transport",
        "spent_on": "2026-10-01",
        "payment_method": "card",
    }
    base.update(overrides)
    return base


def _create(client, **overrides):
    response = client.post("/api/expenses", json=_expense(**overrides))
    assert response.status_code == 201, response.text
    return response.json()


# --- operational endpoints -------------------------------------------------------------------


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "UP"}


def test_ready_runs_database_check(client):
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "READY"}


def test_root_reports_service_and_env(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"service": "Expense Tracker API", "env": "test", "version": "1.0.0"}


def test_metrics_endpoint_is_prometheus_format(client):
    client.get("/health")  # make sure at least one request has been observed
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "http_requests_total" in response.text
    assert "http_request_duration_seconds" in response.text


# --- create ----------------------------------------------------------------------------------


def test_create_expense_returns_201_and_echoes_fields(client):
    body = _create(client, title="Groceries", amount="845.50", category="food", note="weekly shop")
    assert body["title"] == "Groceries"
    assert body["amount"] == 845.5
    assert body["category"] == "food"
    assert body["spent_on"] == "2026-10-01"
    assert body["payment_method"] == "card"
    assert body["note"] == "weekly shop"
    assert isinstance(body["id"], int)
    assert body["created_at"] and body["updated_at"]


def test_create_rejects_non_positive_amount(client):
    assert client.post("/api/expenses", json=_expense(amount="-5.00")).status_code == 422
    assert client.post("/api/expenses", json=_expense(amount="0")).status_code == 422


def test_create_rejects_more_than_two_decimal_places(client):
    assert client.post("/api/expenses", json=_expense(amount="10.555")).status_code == 422


def test_create_rejects_unknown_category_and_payment_method(client):
    assert client.post("/api/expenses", json=_expense(category="crypto")).status_code == 422
    assert client.post("/api/expenses", json=_expense(payment_method="cheque")).status_code == 422


def test_create_rejects_empty_or_overlong_title(client):
    assert client.post("/api/expenses", json=_expense(title="")).status_code == 422
    assert client.post("/api/expenses", json=_expense(title="x" * 121)).status_code == 422


# --- list / filters --------------------------------------------------------------------------


def test_list_orders_newest_spent_on_first(client):
    older = _create(client, title="Older", spent_on="2026-09-20")
    newest = _create(client, title="Newest", spent_on="2026-10-12")
    middle = _create(client, title="Middle", spent_on="2026-10-03")
    ids = [e["id"] for e in client.get("/api/expenses").json()]
    assert ids == [newest["id"], middle["id"], older["id"]]


def test_list_filters_by_category(client):
    _create(client, category="food")
    _create(client, category="food")
    _create(client, category="housing")
    rows = client.get("/api/expenses", params={"category": "food"}).json()
    assert len(rows) == 2
    assert {r["category"] for r in rows} == {"food"}
    # unknown category values are rejected rather than silently returning everything
    assert client.get("/api/expenses", params={"category": "crypto"}).status_code == 422


def test_list_filters_by_month(client):
    september = _create(client, title="Sept rent", spent_on="2026-09-05")
    _create(client, title="Oct rent", spent_on="2026-10-05")
    _create(client, title="Oct last day", spent_on="2026-10-31")
    rows = client.get("/api/expenses", params={"month": "2026-09"}).json()
    assert [r["id"] for r in rows] == [september["id"]]
    assert len(client.get("/api/expenses", params={"month": "2026-10"}).json()) == 2
    assert client.get("/api/expenses", params={"month": "2026-13"}).status_code == 422
    assert client.get("/api/expenses", params={"month": "Oct-2026"}).status_code == 422


def test_list_searches_title_case_insensitively(client):
    _create(client, title="Netflix subscription")
    _create(client, title="Electricity bill")
    rows = client.get("/api/expenses", params={"q": "netflix"}).json()
    assert [r["title"] for r in rows] == ["Netflix subscription"]


# --- read / update / delete ------------------------------------------------------------------


def test_get_expense_by_id(client, expense):
    response = client.get(f"/api/expenses/{expense['id']}")
    assert response.status_code == 200
    assert response.json() == expense


def test_get_missing_expense_returns_404(client):
    response = client.get("/api/expenses/999999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Expense not found"}


def test_update_is_partial(client, expense):
    response = client.put(f"/api/expenses/{expense['id']}", json={"amount": "199.99", "category": "shopping"})
    assert response.status_code == 200
    body = response.json()
    assert body["amount"] == 199.99
    assert body["category"] == "shopping"
    # fields that were not sent are untouched
    assert body["title"] == expense["title"]
    assert body["note"] == expense["note"]
    assert body["spent_on"] == expense["spent_on"]
    # the same validation rules apply to updates
    assert client.put(f"/api/expenses/{expense['id']}", json={"amount": "-1"}).status_code == 422
    assert client.put("/api/expenses/999999", json={"title": "ghost"}).status_code == 404


def test_delete_returns_204_then_404(client, expense):
    response = client.delete(f"/api/expenses/{expense['id']}")
    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/api/expenses/{expense['id']}").status_code == 404
    assert client.delete(f"/api/expenses/{expense['id']}").status_code == 404


# --- summary ---------------------------------------------------------------------------------


def test_summary_is_empty_but_well_formed_without_data(client):
    body = client.get("/api/expenses/summary").json()
    assert body["total"] == 0
    assert body["count"] == 0
    assert body["by_category"] == []
    assert body["top_category"] is None
    assert len(body["by_month"]) == 6
    assert body["this_month_total"] == 0
    assert body["average_per_day_this_month"] == 0


def test_summary_aggregates_totals_by_category_and_month(client):
    today = date.today()
    _create(client, title="Lunch", amount="100.00", category="food", spent_on=today.isoformat())
    _create(client, title="Dinner", amount="50.50", category="food", spent_on=today.isoformat())
    _create(client, title="Bus", amount="30.25", category="transport", spent_on=today.isoformat())

    body = client.get("/api/expenses/summary").json()
    assert body["total"] == 180.75
    assert body["count"] == 3
    assert body["by_category"] == [
        {"category": "food", "total": 150.5, "count": 2},
        {"category": "transport", "total": 30.25, "count": 1},
    ]
    assert body["top_category"] == "food"
    assert body["this_month_total"] == 180.75
    expected_avg = (Decimal("180.75") / Decimal(today.day)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    assert body["average_per_day_this_month"] == float(expected_avg)

    months = body["by_month"]
    assert len(months) == 6
    assert months[-1] == {"month": today.strftime("%Y-%m"), "total": 180.75}
    assert months == sorted(months, key=lambda m: m["month"])  # ascending
    assert sum(m["total"] for m in months) == 180.75


# --- CORS ------------------------------------------------------------------------------------


def test_cors_allows_only_configured_origins(client):
    """The API must echo an allowed origin and must NOT answer with '*' or echo unknown origins."""
    allowed = client.options(
        "/api/expenses",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"},
    )
    assert allowed.status_code == 200
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:5173"

    denied = client.options(
        "/api/expenses",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"},
    )
    assert denied.headers.get("access-control-allow-origin") is None
