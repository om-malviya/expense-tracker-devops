# Submission evidence

Every rubric module asks for a screenshot or terminal output. I keep two forms of each
terminal capture side by side:

- `<name>.txt` - the raw command output (first line is the command), so a grader can grep it
  and diff it against their own run;
- `<name>.png` - the same text rendered as a terminal window by `scripts/render-terminal.py`
  (produced via `scripts/capture-evidence.sh <name> "<command>"`).

Browser evidence is a real Chromium screenshot taken with Playwright against the running stack.

All captures below were made on the local Docker Compose stack
(`docker compose up --build -d`, images built from this repository at that moment).

| Rubric item | File(s) | What it shows | Captured |
|-------------|---------|---------------|----------|
| M1 - backend responds to `/health`; 4+ REST endpoints (GET/POST/PUT/DELETE) | `m1-api-curl.txt` / `.png` | curl session against `localhost:8000`: `/health`, `/ready`, `/`, six `POST /api/expenses` (201), a 422 validation reply, `GET /api/expenses` with `?category=`, `?month=` and `?q=` filters, `GET /api/expenses/{id}`, partial `PUT`, `DELETE` (204) followed by the 404, `GET /api/expenses/summary`, first 20 lines of `/metrics` | 2026-10-16 |
| M1 - PostgreSQL table managed by Alembic | `m1-alembic-migration.txt` / `.png` | `alembic current` / `alembic history` inside the backend container (revision `0001_create_expenses` = head), then `psql` in the postgres container: `\dt`, `\d expenses` (columns + indexes), the seeded rows, and the `alembic_version` table | 2026-10-16 |
| M1 - React frontend renders and calls the API | `m1-app-dashboard.png` | Dashboard at `http://localhost:3000` (1440x900) with KPI cards, category split, 6-month trend and the expense table populated from the API through the nginx `/api/` proxy | 2026-10-16 |
| M1 - responsive, usable UI | `m1-app-mobile.png` | Same page at a 390x844 phone viewport: cards stack, the table collapses into labelled rows | 2026-10-16 |
| M1 - API surface (bonus) | `m1-swagger-docs.png` | FastAPI's generated OpenAPI UI at `http://localhost:8000/docs` listing every route | 2026-10-16 |
| M2 - `pytest -v` passes; 5+ tests over 3+ endpoints; test DB not production DB; `pytest.ini`/`conftest.py` | `m2-pytest-v.txt` / `.png` | 20 passed in `backend/` (`configfile: pytest.ini`); the suite runs on a temporary SQLite file set up in `tests/conftest.py` | 2026-10-16 |
| M2 - code quality | `m2-ruff-bandit-pip-audit.txt` / `.png` | `ruff check` + `ruff format --check` clean, Bandit SAST with no findings, `pip-audit` with no known vulnerabilities in `requirements.txt` | 2026-10-16 |
| M3 - CI/CD pipeline | pending | | |
| M4 - `docker compose up --build` starts all three services | `m4-docker-compose-up.txt` / `.png` | Tail of the image build log, container creation order (postgres -> backend -> frontend, gated on health checks) and `docker compose ps` with all three services `(healthy)` | 2026-10-16 |
| M4 - Dockerfiles build; multi-stage frontend | `m4-docker-images.txt` / `.png` | `docker images`: backend 72 MB, frontend 26 MB content size (nginx runtime stage only, no Node) next to `postgres:16-alpine` | 2026-10-16 |
| M4 - images run as non-root | `m4-non-root.txt` / `.png` | `id` inside both containers (`uid=10001(appuser)` and `uid=101(nginx)`), `python -m pip` failing because pip was removed from the backend image, and the `USER` lines of both Dockerfiles | 2026-10-16 |
| M4 - browser at `http://localhost:3000` | `m4-app-localhost-3000.png` | The application loaded from the Compose stack (same capture as `m1-app-dashboard.png`) | 2026-10-16 |
| M5 - container security scanning | pending | | |
| M6 - Terraform / AWS | pending | | |
| M7 - Kubernetes / Helm | pending | | |
| M8 - Ingress / exposure | pending | | |
| M9 - Prometheus + Grafana | pending | | |
| M10 - presentation + documentation | pending | | |

## How to reproduce a capture

```bash
# terminal evidence (text + rendered PNG)
scripts/capture-evidence.sh m2-pytest-v "cd backend && pytest -v"

# browser evidence (needs `npx playwright install chromium` once)
npx playwright screenshot --viewport-size=1440,900 --full-page \
  --wait-for-selector '.ledger-row .cell-title' http://localhost:3000 docs/screenshots/m1-app-dashboard.png
```
