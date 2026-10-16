"""Pytest configuration.

The suite must never touch the real PostgreSQL database, so before `app` is imported I point
DATABASE_URL at a throw-away SQLite file and set APP_ENV=test (which makes the lifespan hook
create the tables). Settings are read at import time, hence the env vars come first.
"""
import os
import tempfile

import pytest

_TEST_DB = os.path.join(tempfile.mkdtemp(prefix="expense-tracker-test-"), "test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB}"
os.environ["APP_ENV"] = "test"

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import delete  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Expense  # noqa: E402


@pytest.fixture(scope="session")
def client():
    # The context manager runs the lifespan (create_all for APP_ENV=test) once per session.
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def _empty_table(client):
    """Every test starts with an empty expenses table so assertions on counts/ordering are exact."""
    with SessionLocal() as db:
        db.execute(delete(Expense))
        db.commit()
    yield


@pytest.fixture()
def expense(client):
    payload = {
        "title": "Fixture lunch",
        "amount": "250.00",
        "category": "food",
        "spent_on": "2026-10-10",
        "payment_method": "upi",
        "note": "created by fixture",
    }
    response = client.post("/api/expenses", json=payload)
    assert response.status_code == 201
    return response.json()
