# Expense Tracker API (backend)

FastAPI + SQLAlchemy 2 + Alembic service that stores personal expenses in PostgreSQL and
exposes Prometheus metrics. I kept it deliberately small so every DevOps layer on top of it
(tests, Docker, CI, Helm, monitoring) is easy to reason about.

## Run locally

```bash
cd backend
python3.12 -m venv ../.venv && source ../.venv/bin/activate   # keep the venv outside the repo
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env                                          # point DATABASE_URL at your Postgres
alembic upgrade head                                          # create the expenses table
uvicorn app.main:app --reload --port 8000
```

No PostgreSQL handy? `DATABASE_URL=sqlite:///./dev.db` works for both Alembic and the API.

## Environment variables

| Variable       | Default                                                                   | Purpose |
|----------------|---------------------------------------------------------------------------|---------|
| `APP_NAME`     | `Expense Tracker API`                                                     | shown in `/` and OpenAPI title |
| `APP_ENV`      | `local`                                                                   | `test` makes the app create tables itself; anything else relies on Alembic |
| `LOG_LEVEL`    | `info`                                                                    | Python logging level |
| `DATABASE_URL` | `postgresql+psycopg://expenses:expenses-local-only@localhost:5432/expenses` | SQLAlchemy URL; injected from a K8s Secret in production |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000`                             | comma list of allowed browser origins (no wildcard) |

## API

| Method | Path                      | Description |
|--------|---------------------------|-------------|
| GET    | `/`                       | service name, env, version |
| GET    | `/health`                 | liveness (no DB) |
| GET    | `/ready`                  | readiness, runs `SELECT 1`; `503 {"status":"NOT_READY"}` on failure |
| GET    | `/metrics`                | Prometheus text format |
| GET    | `/api/expenses`           | list, newest `spent_on` first; filters `category`, `month=YYYY-MM`, `q` |
| GET    | `/api/expenses/summary`   | totals, by category, last 6 months, top category, this-month figures |
| GET    | `/api/expenses/{id}`      | single expense, `404` when missing |
| POST   | `/api/expenses`           | create (`201`) |
| PUT    | `/api/expenses/{id}`      | partial update |
| DELETE | `/api/expenses/{id}`      | delete (`204`) |

Validation: `amount` > 0 with 2 decimal places, `category` in
`food|transport|housing|utilities|health|entertainment|shopping|education|other`,
`payment_method` in `cash|card|upi|bank_transfer|other`, `title` 1-120 chars, `spent_on` ISO date.

## Tests and quality gates

```bash
pytest -v                    # uses a temporary SQLite file, never the real database
ruff check app tests         # lint
bandit -q -r app             # SAST
pip-audit -r requirements.txt  # dependency CVEs
```

## Docker

```bash
docker build -t expense-tracker-backend .
docker run --rm -p 8000:8000 -e DATABASE_URL=... expense-tracker-backend
```

The container runs as UID 10001, applies migrations on start (`alembic upgrade head`) and then
serves on port 8000.
