# Expense Tracker – DevOps Capstone

Student: Om Malviya | Enrollment No: 24BCS10448
Repository: https://github.com/om-malviya/expense-tracker-devops
Green pipeline run: https://github.com/om-malviya/expense-tracker-devops/actions/runs/38919569372 (first green run);
latest green run: https://github.com/om-malviya/expense-tracker-devops/actions/runs/40339582631

I built a small personal expense tracker (FastAPI + PostgreSQL API, React dashboard) and then put
the complete delivery chain from the course around it: pytest and static analysis, hardened Docker
images, a GitHub Actions pipeline with a Trivy gate that publishes SHA-tagged images to GHCR,
Terraform for an AWS VPC + EKS cluster, a Helm chart running on Kubernetes with Ingress and an HPA,
Prometheus/Grafana monitoring with alert rules, and Argo CD for a GitOps deployment path. This README
is the single page a grader needs; every claim below links to a file in the repo or a capture in
[`docs/screenshots/`](docs/screenshots/README.md). The presentation deck and the demo video are in
[`demo/`](demo/README.md); the course's submission rules are copied in [`SUBMISSION.md`](SUBMISSION.md).

| Section | | |
|---|---|---|
| [1. What the application does](#1-what-the-application-does) | [8. Docker](#8-docker) | [15. Troubleshooting lab](#15-troubleshooting-lab) |
| [2. Tech stack](#2-tech-stack) | [9. CI/CD pipeline](#9-cicd-pipeline) | [16. Known issues and limitations](#16-known-issues-and-limitations) |
| [3. Architecture](#3-architecture) | [10. Security](#10-security) | [17. Evidence index](#17-evidence-index) |
| [4. Repository layout](#4-repository-layout) | [11. Terraform](#11-terraform) | [18. Presentation and demo video](#18-presentation-and-demo-video) |
| [5. Running locally](#5-running-locally) | [12. Kubernetes + Helm](#12-kubernetes--helm) | [19. Lessons learned](#19-lessons-learned) |
| [6. API reference](#6-api-reference) | [13. GitOps with Argo CD](#13-gitops-with-argo-cd) | |
| [7. Tests and code quality](#7-tests-and-code-quality) | [14. Monitoring](#14-monitoring) | |

---|---|---|
| [1. What the application does](#1-what-the-application-does) | [7. Docker](#7-docker) | [12. Monitoring](#12-monitoring) |
| [2. Architecture](#2-architecture) | [8. CI/CD pipeline](#8-cicd-pipeline) | [13. Troubleshooting lab](#13-troubleshooting-lab) |
| [3. Repository layout](#3-repository-layout) | [9. Security](#9-security) | [14. Evidence index](#14-evidence-index) |
| [4. Running locally](#4-running-locally) | [10. Terraform](#10-terraform) | [15. Demo](#15-demo) |
| [5. API reference](#5-api-reference) | [11. Kubernetes + Helm](#11-kubernetes--helm) | [16. Lessons learned](#16-lessons-learned) |
| [6. Tests and code quality](#6-tests-and-code-quality) | | |

---

## 1. What the application does

Expense Tracker is a single-user ledger for day-to-day spending. I record what I paid for
(`title`), how much (`amount`), a `category` (food, transport, housing, utilities, health,
entertainment, shopping, education, other), the date (`spent_on`), the `payment_method` (cash,
card, upi, bank_transfer, other) and an optional `note`. The dashboard then answers the questions I
actually ask at the end of a month: how much did I spend this month, on what, what is my average
per day, and how does this month compare with the last six.

I chose this domain because it is my own (not the TaskBoard reference app), it is small enough that
every DevOps layer stays easy to reason about, and it still needs the things the rubric asks for: a
relational table with real types (`Numeric(10,2)`, `Date`, indexed columns), validation rules worth
testing, list/filter/aggregate endpoints that do real database work (useful for the HPA demo), and
a UI with enough state (filters, modal form, empty and error states) to be judged as "usable".

Features:

- KPI cards: this month's total, number of expenses, top category, average per day
- Category breakdown with percentages and a 6-month trend chart (CSS only, no chart library)
- Filter bar: category, month (`YYYY-MM`), free-text search, all backed by API query parameters
- Add / edit / delete through a modal form that mirrors the backend validation
- Loading skeleton and an error banner when the API is unreachable, so the page never goes blank
- Responsive layout: the table collapses into labelled rows on a phone viewport

![Dashboard at http://localhost:3000](docs/screenshots/m1-app-dashboard.png)

Mobile viewport (390x844): [`docs/screenshots/m1-app-mobile.png`](docs/screenshots/m1-app-mobile.png).
Generated OpenAPI UI: [`docs/screenshots/m1-swagger-docs.png`](docs/screenshots/m1-swagger-docs.png).

---

## 2. Tech stack

| Layer | Tools and versions |
|---|---|
| Backend | Python 3.12, FastAPI 0.142, Uvicorn 0.54, SQLAlchemy 2.0, Alembic 1.20, psycopg 3, pydantic-settings 2.15, prometheus-fastapi-instrumentator 8.1 |
| Database | PostgreSQL 16 (alpine); SQLite only for the test suite |
| Frontend | React 18.3, Vite 7.3, plain CSS; served by nginx-unprivileged 1.30-alpine |
| Testing and code quality | pytest 9.1, pytest-cov, ruff 0.17 (lint + format), Bandit 1.9, pip-audit 2.10, npm audit |
| Containers | Docker 29 (multi-stage builds, non-root users), Docker Compose |
| CI/CD and registry | GitHub Actions, GitHub Container Registry (GHCR), images tagged with the git commit SHA |
| Security scanning | Trivy 0.75 (image gate + SARIF), Gitleaks (secret scan), Bandit (SAST), pip-audit / npm audit (SCA) |
| Infrastructure as Code | Terraform 1.16, AWS provider 5.100, modules `terraform-aws-modules/vpc` 5.8.1 and `eks` 20.37.1 (EKS 1.31), LocalStack 4.6 for an offline plan |
| Orchestration | Kubernetes (EKS in the Terraform design; k3s v1.35 via Colima for the local run), Helm 4, Traefik ingress, HPA with metrics-server |
| GitOps | Argo CD (automated sync, prune, self-heal) |
| Observability | kube-prometheus-stack (Prometheus Operator, Prometheus, Alertmanager, Grafana 13), ServiceMonitor, PrometheusRule |
| Tooling | macOS (Apple Silicon), kubectl, AWS CLI v2, Playwright (evidence screenshots) |

---

## 3. Architecture

Runtime (identical topology in Docker Compose and in Kubernetes):

```text
 browser ──> nginx (frontend image, uid 101, :8080) ──/api/──> FastAPI (backend image, uid 10001, :8000) ──> PostgreSQL 16
              serves the Vite bundle, proxies /api/                 alembic upgrade head on start          table: expenses
              so the UI and API are one origin (no CORS)            /health /ready /metrics                 (StatefulSet + PVC on K8s)
```

Delivery chain:

```text
 git push main ──> GitHub Actions ──> backend-test (ruff + pytest, SQLite)  ─┐
                                      frontend-build (npm ci, build, audit)  ─┼─> build-scan-push ──> deploy (Helm)
                                      security-static (bandit, pip-audit,    ─┘   docker build x2        helm lint, then
                                                       gitleaks)                  Trivy gate x2          helm upgrade --install
                                                                                  push to GHCR           when KUBE_CONFIG_DATA is set
                                                                                  :<git sha> + :latest
```

Platform:

```text
 Terraform ──> AWS: VPC (2 public + 2 private subnets, IGW, NAT) + EKS 1.31 + managed node group (t3.medium x2)
 Helm chart helm/expense-tracker ──> namespace expense-tracker: ConfigMap, Secret, Postgres StatefulSet,
                                     backend + frontend Deployments (2 replicas each), ClusterIP Services,
                                     Ingress (expense.local: / -> frontend:80, /api -> backend:8000),
                                     HPA (backend, CPU 60 %), ServiceMonitor
 kube-prometheus-stack (namespace monitoring) ──> Prometheus scrapes backend /metrics every 15 s
                                                   ──> Grafana dashboard "Expense Tracker - API overview"
                                                   ──> PrometheusRule: 5 alerts
```

---

## 4. Repository layout

```text
.
├── .github/workflows/ci-cd.yml     the pipeline: 5 jobs, see section 9
├── backend/                        FastAPI service
│   ├── app/                        config.py (pydantic-settings), db.py, models.py, schemas.py, main.py (routes)
│   ├── alembic/versions/0001_create_expenses.py   the migration that creates the `expenses` table
│   ├── tests/                      conftest.py (SQLite test DB) + test_api.py (20 tests)
│   ├── Dockerfile                  python:3.12-slim, non-root uid 10001, pip removed, HEALTHCHECK
│   ├── pytest.ini, ruff.toml       test and lint configuration
│   └── requirements*.txt           exact pins (runtime / dev tooling)
├── frontend/                       React 18 + Vite 7 dashboard
│   ├── src/                        App.jsx, api.js, utils.js, styles.css, components/
│   ├── nginx.conf.template         envsubst template: /api/ proxy, /healthz, SPA fallback
│   └── Dockerfile                  node:22-alpine build stage -> nginx-unprivileged:1.30-alpine runtime
├── docker-compose.yml              postgres + backend + frontend with health-gated start order
├── helm/expense-tracker/           Chart.yaml, values.yaml, values-dev.yaml (k3s), values-prod.yaml (EKS), templates/
├── k8s/namespace.yaml              the one object created outside Helm (Pod Security "restricted" labels)
├── monitoring/                     kube-prometheus-stack values, ServiceMonitor, PrometheusRule, Grafana dashboard JSON + ConfigMap
├── terraform/                      VPC + EKS (community modules), tfvars example, localstack/ for an offline plan
├── security/                       trivy.yaml, .trivyignore, bandit.yaml, .gitleaks.toml
├── troubleshooting/                two deliberately broken manifests + the triage runbook
├── scripts/                        load-test.sh (HPA demo), capture-evidence.sh + render-terminal.py (evidence)
├── gitops/                         Argo CD install script, Application manifest and GitOps walkthrough
├── demo/                           presentation deck (PPTX + PDF) and the recorded demo video
├── docs/screenshots/               every capture, indexed in docs/screenshots/README.md
├── SUBMISSION.md, GRADING.md       the course's submission rules and rubric, copied unchanged
└── SECURITY.md                     the security gates, why they are configured that way, exceptions policy
```

---

## 5. Running locally

### One command (Docker Compose)

```bash
docker compose up --build        # add -d to detach
```

| Service | URL | Notes |
|---|---|---|
| Frontend | http://localhost:3000 | nginx-unprivileged on container port 8080 |
| Backend | http://localhost:8000 – docs at http://localhost:8000/docs | `/health`, `/ready`, `/metrics` |
| PostgreSQL | `localhost:5432`, db `expenses`, user `expenses` | password `expenses-local-only` (compose-only placeholder) |

Start order is gated on health checks (`depends_on: condition: service_healthy`): postgres must
answer `pg_isready`, then the backend runs `alembic upgrade head` and must answer `/health`, then
the frontend starts. Evidence: [`m4-docker-compose-up.png`](docs/screenshots/m4-docker-compose-up.png).

```bash
docker compose exec postgres psql -U expenses -d expenses -c '\d expenses'   # look at the table
docker compose down -v                                                      # stop and drop the volume
```

### Without Docker

```bash
# backend (needs a PostgreSQL, or set DATABASE_URL=sqlite:///./dev.db)
cd backend
python3.12 -m venv ../.venv && source ../.venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# frontend (Vite dev server proxies /api to :8000)
cd frontend && npm install && npm run dev      # http://localhost:5173
```

### Backend environment variables (`backend/app/config.py`)

| Variable | Default | Purpose |
|---|---|---|
| `APP_NAME` | `Expense Tracker API` | shown by `/` and as the OpenAPI title |
| `APP_ENV` | `local` | `test` makes the app create tables itself; everything else relies on Alembic |
| `LOG_LEVEL` | `info` | Python logging level |
| `DATABASE_URL` | `postgresql+psycopg://expenses:expenses-local-only@localhost:5432/expenses` | SQLAlchemy URL; in Kubernetes it comes from a Secret |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | comma-separated allow-list, no wildcard |

The frontend image takes `BACKEND_HOST` (default `expense-tracker-backend`) and `BACKEND_PORT`
(`8000`), rendered into `nginx.conf.template` at start-up, so the same image works in Compose
(`BACKEND_HOST=backend`) and in Kubernetes (the Service name).

---

## 6. API reference

All data endpoints live under `/api`. Full curl session with responses:
[`m1-api-curl.txt`](docs/screenshots/m1-api-curl.txt) / [`.png`](docs/screenshots/m1-api-curl.png).

| Method | Path | Status | Description |
|---|---|---|---|
| GET | `/` | 200 | `{"service":"Expense Tracker API","env":"compose","version":"1.0.0"}` |
| GET | `/health` | 200 | liveness, no DB access: `{"status":"UP"}` |
| GET | `/ready` | 200 / 503 | readiness, runs `SELECT 1`: `{"status":"READY"}` or `{"status":"NOT_READY"}` |
| GET | `/metrics` | 200 | Prometheus text format (`http_requests_total`, `http_request_duration_seconds`, ...) |
| GET | `/api/expenses?category=&month=YYYY-MM&q=` | 200 | list, newest `spent_on` first, optional filters |
| GET | `/api/expenses/summary` | 200 | totals, by category, last 6 months, top category, this-month figures |
| GET | `/api/expenses/{id}` | 200 / 404 | one expense; `{"detail":"Expense not found"}` when missing |
| POST | `/api/expenses` | 201 / 422 | create |
| PUT | `/api/expenses/{id}` | 200 / 404 / 422 | partial update, every field optional |
| DELETE | `/api/expenses/{id}` | 204 / 404 | delete |

Example – create, then read the summary:

```bash
curl -s -X POST http://localhost:8000/api/expenses -H 'Content-Type: application/json' \
  -d '{"title":"Groceries - DMart","amount":2350.75,"category":"food","spent_on":"2026-10-12","payment_method":"upi"}'
# {"id":2,"title":"Groceries - DMart","amount":2350.75,"category":"food","spent_on":"2026-10-12",
#  "payment_method":"upi","note":null,"created_at":"2026-10-16T14:53:37.796630Z","updated_at":"..."}   [HTTP 201]

curl -s http://localhost:8000/api/expenses/summary
# {"total":18789.75,"count":5,
#  "by_category":[{"category":"housing","total":12000.0,"count":1},{"category":"food","total":2350.75,"count":1},...],
#  "by_month":[{"month":"2026-05","total":0.0},...,{"month":"2026-10","total":14950.75}],
#  "top_category":"housing","this_month_total":14950.75,"average_per_day_this_month":934.42}
```

Validation (`backend/app/schemas.py`), enforced with Pydantic and returned as `422`:

- `amount` must be `> 0`, at most 2 decimal places, fits `Numeric(10,2)`; serialised as a JSON number
- `category` and `payment_method` are enums (lists in section 1); an unknown value lists the allowed ones in the error
- `title` 1–120 characters, `note` up to 1000, `spent_on` an ISO date, `month` filter must be `YYYY-MM`

Example of a rejected body (`amount: -5`, `category: "crypto"`): see the 422 block in
[`m1-api-curl.txt`](docs/screenshots/m1-api-curl.txt).

Database: one table `expenses` created by Alembic revision `0001_create_expenses` (columns `id`,
`title`, `amount numeric(10,2)`, `category` indexed, `spent_on date` indexed, `payment_method`,
`note`, `created_at`, `updated_at`). The backend container runs `alembic upgrade head` before
uvicorn, so every start converges the schema. Evidence: [`m1-alembic-migration.png`](docs/screenshots/m1-alembic-migration.png).

---

## 7. Tests and code quality

```bash
cd backend && pytest -v        # 20 passed
ruff check . && ruff format --check .
bandit -c ../security/bandit.yaml -r app
pip-audit -r requirements.txt
```

- `tests/conftest.py` sets `DATABASE_URL=sqlite:///<tmp>/test.db` and `APP_ENV=test` **before** importing
  the app, so the suite never touches PostgreSQL; a fixture truncates the table between tests.
- `pytest.ini` sets `pythonpath`, `testpaths`, disables the cache provider (nothing written into the repo)
  and writes `reports/junit.xml`, which CI uploads as an artifact.
- 20 tests over every endpoint: `/health`, `/ready`, `/`, `/metrics`, create (201 + four validation
  cases), list ordering and all three filters, get by id + 404, partial update, delete 204 then 404,
  summary (empty and populated) and the CORS allow-list.
- Lint/SAST/SCA all clean: ruff, Bandit (287 lines scanned, no issues), pip-audit (no known vulnerabilities).

![pytest -v](docs/screenshots/m2-pytest-v.png)

Evidence: [`m2-pytest-v.txt`](docs/screenshots/m2-pytest-v.txt), [`m2-ruff-bandit-pip-audit.png`](docs/screenshots/m2-ruff-bandit-pip-audit.png).

---

## 8. Docker

**`backend/Dockerfile`** – single stage on `python:3.12-slim`. Dependencies are installed first (cached
layer), then `pip`, `setuptools` and `wheel` are uninstalled: Trivy had flagged CVEs in the libraries pip
vendors and nothing at runtime needs pip. Only `alembic.ini`, `alembic/` and `app/` are copied (tests are
excluded by `.dockerignore`). A numeric user `10001` is created so Kubernetes `runAsNonRoot` can verify
it. The `HEALTHCHECK` uses `urllib` because the slim image has no curl. `CMD` runs
`alembic upgrade head && uvicorn ...`.

**`frontend/Dockerfile`** – multi-stage. Stage 1 (`node:22-alpine`) runs `npm ci` and `npm run build`;
stage 2 (`nginxinc/nginx-unprivileged:1.30-alpine`) copies only `dist/` plus the nginx template, so
Node, npm and `node_modules` never reach the runtime image. The base already runs as uid `101` on
port `8080`; `USER 101` is declared again so scanners see it. `HEALTHCHECK` hits `/healthz`.

| Image | Content size | Disk usage | User |
|---|---|---|---|
| `expense-tracker-backend:local` | 72.1 MB | 337 MB | `uid=10001(appuser)` |
| `expense-tracker-frontend:local` | 26 MB | 90.5 MB | `uid=101(nginx)` |
| `postgres:16-alpine` | 115 MB | 411 MB | – |

Evidence: [`m4-docker-images.png`](docs/screenshots/m4-docker-images.png),
[`m4-non-root.png`](docs/screenshots/m4-non-root.png) (`id` inside both containers and
`python -m pip` failing with "No module named pip"), [`m4-app-localhost-3000.png`](docs/screenshots/m4-app-localhost-3000.png).

---

## 9. CI/CD pipeline

File: [`.github/workflows/ci-cd.yml`](.github/workflows/ci-cd.yml). Triggers: `push` and
`pull_request` on `main`, plus `workflow_dispatch`.

```text
backend-test ──┐
frontend-build ─┼─> build-scan-push ──> deploy (main only)
security-static ┘
```

| Job | What it does | Time in run 38919569372 |
|---|---|---|
| Backend lint + pytest | `ruff check`, `pytest -v --junitxml`, upload report (also on failure) | 21 s |
| Frontend build + npm audit | `npm ci`, `npm run build`, `npm audit --audit-level=high`, upload `dist` | 8 s |
| Security (bandit + pip-audit + gitleaks) | SAST, SCA (`--strict`), secret scan over the full history (`fetch-depth: 0`) | 23 s |
| Docker build + Trivy gate + push to GHCR | build both images tagged `${{ github.sha }}`, Trivy gate on each (`exit-code: 1`), SARIF upload, login, push `:sha`, then `:latest` on main | 1 m 43 s |
| Helm deploy | `helm lint` (default + prod values); `helm upgrade --install ... --set backend.image.tag=$sha` when `KUBE_CONFIG_DATA` exists | 5 s |

- A failing test stops the image build, the push and the deploy because of the `needs:` edges.
- Images are tagged with the **full git SHA** so a running pod can always be traced to one commit;
  `latest` is only added on pushes to `main`. Pull requests build and scan but never push.
- The deploy job runs with `environment: production` and reads the cluster kubeconfig from the
  `KUBE_CONFIG_DATA` secret (base64 of `~/.kube/config`). When the secret is not set it prints the
  exact `helm upgrade --install` command instead of failing, so the pipeline stays green on a fresh
  fork; my local k3s cluster is not reachable from GitHub runners, so that is what happened here and
  I ran the same command by hand (section 12).
- Run history: the first run [38919310984](https://github.com/om-malviya/expense-tracker-devops/actions/runs/38919310984)
  failed after 29 s in the Gitleaks step – my own `postgresql+psycopg://<user>:<password>@` rule matched
  the documented connection-string example in the repo. Commit `ec416e2` replaced the example with
  placeholders and the next run [38919569372](https://github.com/om-malviya/expense-tracker-devops/actions/runs/38919569372)
  went green in 2 m 21 s.

![Green pipeline](docs/screenshots/m5-actions-run.png)

GHCR packages: [backend](https://github.com/om-malviya/expense-tracker-devops/pkgs/container/expense-tracker-backend),
[frontend](https://github.com/om-malviya/expense-tracker-devops/pkgs/container/expense-tracker-frontend).
The registry tag list ([`m5-ghcr-pull.txt`](docs/screenshots/m5-ghcr-pull.txt)) shows
`ec416e2b29d120f323c1e0da197c9bed2692f9a9`, `a9bc797fa227f85b4fca756b3d27259e02f786e3` and `latest`
on both repositories; the run log prints the digests, e.g.
`expense-tracker-backend:ec416e2b... -> @sha256:f5f298bb...`.

Evidence: [`m5-workflow-summary.png`](docs/screenshots/m5-workflow-summary.png),
[`m5-actions-run-cli.png`](docs/screenshots/m5-actions-run-cli.png), [`m5-ghcr-backend.png`](docs/screenshots/m5-ghcr-backend.png),
[`m5-ghcr-frontend.png`](docs/screenshots/m5-ghcr-frontend.png).

---

## 10. Security

Everything is described in [`SECURITY.md`](SECURITY.md); the short version:

| Gate | Tool | Fails when | Config |
|---|---|---|---|
| Lint + tests | ruff, pytest | any error / failing test | `backend/ruff.toml`, `backend/pytest.ini` |
| Frontend dependencies | npm audit | HIGH/CRITICAL advisory | – |
| SAST | Bandit | any finding | `security/bandit.yaml` |
| SCA | pip-audit `--strict` | any known vulnerability | – |
| Secrets | Gitleaks (full history) | any non-allow-listed leak | `security/.gitleaks.toml` |
| Images | Trivy on **both** images | HIGH/CRITICAL CVE with a fix available | `security/trivy.yaml`, `security/.trivyignore` (empty) |

**What Trivy scanned and what the result means.** Trivy scanned the two images the pipeline built
from commit `ec416e2` – the backend (Python 3.12 slim on Debian: OS packages plus every library in
`requirements.txt`) and the frontend (nginx-unprivileged on Alpine: OS packages plus the static bundle)
– for known CVEs rated HIGH or CRITICAL, embedded secrets and Dockerfile misconfiguration. Both came
back clean: Trivy detected `debian 13.7` (87 OS packages) plus 30 Python packages in the backend image
and `alpine 3.24.2` (70 OS packages) in the frontend image, and every target in the Report Summary shows
`0` vulnerabilities, so both gate steps exited 0 and the push steps ran. "Clean" means no CVE with a
fixed package at scan time (2026-10-16): `vulnerability.ignore-unfixed: true` drops advisories that
Debian/Alpine have not patched yet, and because the action exported its default severity list the scan
was in fact evaluated at every severity, so the gate held with margin. The gate matters because a
fixable HIGH/CRITICAL CVE makes the step exit 1, the job goes red and nothing reaches GHCR; it re-runs on
every push, so a CVE published tomorrow is caught on the next build instead of shipping silently.

![Trivy report summary](docs/screenshots/m6-trivy-scan-output.png)

Image and runtime hardening: both images run as non-root (uid 10001 / 101), pip is removed from the
backend image, the Helm chart sets `runAsNonRoot`, `readOnlyRootFilesystem`, `allowPrivilegeEscalation: false`,
`capabilities: drop: [ALL]` and a `RuntimeDefault` seccomp profile, and the namespace enforces the
Pod Security `restricted` profile, so any regression in that hardening is rejected at admission.

Evidence: [`m6-trivy-config.png`](docs/screenshots/m6-trivy-config.png),
[`m6-trivy-explanation.txt`](docs/screenshots/m6-trivy-explanation.txt),
[`m2-ruff-bandit-pip-audit.png`](docs/screenshots/m2-ruff-bandit-pip-audit.png), [`m3-gitignore.png`](docs/screenshots/m3-gitignore.png).

---

## 11. Terraform

[`terraform/`](terraform/README.md) provisions, in `ap-south-1`:

- a VPC `10.30.0.0/16` with **2 public** (`10.30.101.0/24`, `10.30.102.0/24`) and 2 private subnets
  across two AZs, an internet gateway and a single NAT gateway (module `terraform-aws-modules/vpc` 5.8.1);
- an EKS 1.31 cluster `expense-tracker-dev-eks` with one managed node group `main`
  (`t3.medium`, min 1 / desired 2 / max 3), the `coredns`, `kube-proxy`, `vpc-cni` and `aws-ebs-csi-driver`
  add-ons, IAM roles, security groups, OIDC provider, KMS key and CloudWatch log group
  (module `terraform-aws-modules/eks` 20.37.1);
- an IRSA role for the EBS CSI driver so only the CSI pods can create the volume behind the Postgres PVC.

`terraform.tfvars.example` is committed; `terraform.tfvars`, state and plan files are git-ignored,
and no credentials exist anywhere in the repo (authentication is `aws configure` / `AWS_PROFILE`).

```bash
cd terraform && cp terraform.tfvars.example terraform.tfvars
terraform init && terraform fmt -check -recursive && terraform validate
terraform plan -out=tfplan
terraform apply tfplan                           # 12-15 minutes
$(terraform output -raw configure_kubectl)       # aws eks update-kubeconfig --region ap-south-1 --name expense-tracker-dev-eks
terraform destroy                                # after helm uninstall, so no NLB/EBS is left outside the state
```

**What I could prove, and what I could not.** I did not have an AWS account while building this
project. `terraform init`, `fmt` and `validate` ran for real (Terraform 1.16.5, AWS provider 5.100.0,
modules downloaded from the registry). To get a real `terraform plan` without credentials I ran it
against a **LocalStack 4.6** container through `terraform/localstack/plan.sh`, which drops a temporary
provider override, plans with `terraform.tfvars.example`, and removes the override, the plan file and
any lock-file change again via an `EXIT` trap. The result is genuine Terraform output for this
configuration – `Plan: 61 to add, 0 to change, 0 to destroy.` – and all 1830 lines are in
[`m7-terraform-plan.txt`](docs/screenshots/m7-terraform-plan.txt) (the resource list is in
[`m7-terraform-plan-summary.txt`](docs/screenshots/m7-terraform-plan-summary.txt)).
**`terraform apply`, `terraform destroy` and the AWS console screenshots are not included** because
they cannot be produced without a real account (LocalStack community does not emulate EKS at all).
The exact commands that produce each of those captures once an account exists are listed at the end of
[`terraform/README.md`](terraform/README.md#what-still-requires-a-real-account-and-the-exact-commands).

![terraform plan against LocalStack](docs/screenshots/m7-terraform-plan-summary.png)

Evidence: [`m7-terraform-init-validate.png`](docs/screenshots/m7-terraform-init-validate.png),
[`m7-terraform-plan.png`](docs/screenshots/m7-terraform-plan.png).

---

## 12. Kubernetes + Helm

I ran the chart on a local **k3s** cluster (Colima VM, single node `colima`, Traefik as the ingress
controller, metrics-server built in). The same chart targets EKS by switching the values file.

**Namespace** – [`k8s/namespace.yaml`](k8s/namespace.yaml) is the only object created outside Helm.
Its labels enforce Pod Security Admission `restricted`, so every pod the chart creates must be non-root
with all capabilities dropped – a free regression test for the hardening.

**Chart** – [`helm/expense-tracker/`](helm/expense-tracker/) (`Chart.yaml` version 1.0.0, `values.yaml`,
`values-dev.yaml`, `values-prod.yaml`):

| Template | What it renders |
|---|---|
| `configmap.yaml` | `APP_NAME`, `APP_ENV`, `LOG_LEVEL`, `CORS_ORIGINS` (envFrom on the backend) |
| `secret.yaml` | `DATABASE_URL` (+ Postgres credentials); skipped when `postgres.existingSecret` is set |
| `postgres-statefulset.yaml` / `postgres-service.yaml` | `postgres:16-alpine`, 1 replica, PVC (`local-path` on k3s, `gp3` on EKS), headless + ClusterIP Service |
| `backend-deployment.yaml` | 2 replicas, RollingUpdate `maxUnavailable: 0`, startup/readiness/liveness probes (`/health`, `/ready`, `/health`), checksum annotations so a ConfigMap/Secret change triggers a rollout, full securityContext |
| `backend-service.yaml` | ClusterIP `expense-tracker-backend:8000` |
| `frontend-deployment.yaml` / `frontend-service.yaml` | 2 replicas of nginx-unprivileged with `BACKEND_HOST` set to the backend Service, emptyDirs for the read-only root FS; ClusterIP `expense-tracker-frontend:80 -> 8080` |
| `ingress.yaml` | host `expense.local`: `/api` -> backend:8000, `/` -> frontend:80 (longest prefix wins) |
| `hpa.yaml` | `autoscaling/v2` on backend CPU utilisation (60 %), 120 s scale-down stabilisation |
| `servicemonitor.yaml` | Prometheus Operator scrape of the backend Service on `/metrics` (enabled in dev/prod values) |

Images are pulled from GHCR by the **SHA tag** that CI printed, never `latest`:

```bash
kubectl apply -f k8s/namespace.yaml
helm upgrade --install expense-tracker ./helm/expense-tracker -n expense-tracker \
  -f helm/expense-tracker/values-dev.yaml \
  --set backend.image.tag=ec416e2b29d120f323c1e0da197c9bed2692f9a9 \
  --set frontend.image.tag=ec416e2b29d120f323c1e0da197c9bed2692f9a9 --wait --timeout 10m

kubectl get pods -n expense-tracker -o wide        # 2 backend + 2 frontend + postgres-0, all Running
kubectl get svc -n expense-tracker                 # three ClusterIP services (+ postgres headless)
helm list -n expense-tracker                       # expense-tracker, chart expense-tracker-1.0.0, deployed
helm history expense-tracker -n expense-tracker    # revision 1 install, revision 2 = ServiceMonitor fix
helm rollback expense-tracker 1 -n expense-tracker # roll back if a release misbehaves
```

![kubectl get pods](docs/screenshots/m8-kubectl-get-pods.png)

**Ingress** – with `127.0.0.1 expense.local` in `/etc/hosts` (the Traefik LoadBalancer on my Colima
node was `192.168.5.1`, port 80 forwarded to the host) the UI is at `http://expense.local/` and the API
at `http://expense.local/api/expenses/summary`. Without editing hosts:
`curl -H 'Host: expense.local' http://127.0.0.1/api/expenses/summary`. In
[`m8-ingress.txt`](docs/screenshots/m8-ingress.txt) I create three expenses through the ingress and
read them back; [`m8-app-via-ingress.png`](docs/screenshots/m8-app-via-ingress.png) is the browser at `http://expense.local/`.

**HPA** – `values-dev.yaml` sets min 2 / max 4 at 60 % CPU. I drove load with
`scripts/load-test.sh` (20 parallel curl workers for 180 s against the backend Service: 9000 requests,
0 failed) and watched `kubectl get hpa -n expense-tracker -w` go from `cpu: 22%/60%, 2 replicas` to
`528%/60%, 4 replicas` within about a minute, then back under target after the load stopped
([`m8-hpa.txt`](docs/screenshots/m8-hpa.txt)).

**Mapping to EKS** – `values-prod.yaml` switches to 3 replicas, bigger requests, `storageClass: gp3`
(the EBS CSI add-on from Terraform), `ingressClassName: nginx` with TLS via cert-manager, HPA 3..10,
and `postgres.existingSecret` so the password never passes through Helm values. The deploy job in CI
runs exactly that command with `--set *.image.tag=${{ github.sha }}` once `KUBE_CONFIG_DATA` holds the
EKS kubeconfig.

Evidence: [`m8-namespace.png`](docs/screenshots/m8-namespace.png), [`m8-helm-upgrade-install.png`](docs/screenshots/m8-helm-upgrade-install.png),
[`m8-helm-list.png`](docs/screenshots/m8-helm-list.png), [`m8-kubectl-get-svc.png`](docs/screenshots/m8-kubectl-get-svc.png),
[`m8-ingress.png`](docs/screenshots/m8-ingress.png), [`m8-hpa.png`](docs/screenshots/m8-hpa.png).

---

## 13. GitOps with Argo CD

The CI pipeline's deploy job pushes a release with `helm upgrade` when a kubeconfig secret is present.
Argo CD is the second, pull-based path: the desired state lives in Git, and a controller inside the
cluster keeps the cluster equal to it.

```text
 git push (values-gitops.yaml) ──> GitHub main ──> Argo CD polls the repo (every 3 min, or Refresh)
                                                      │ renders helm/expense-tracker with values-gitops.yaml
                                                      ▼
                                       namespace expense-tracker-gitops  ──  automated sync, prune, self-heal
```

- [`gitops/argocd/install.sh`](gitops/argocd/install.sh) installs Argo CD into the `argocd` namespace.
- [`gitops/argocd/application.yaml`](gitops/argocd/application.yaml) is the `Application`: source
  `helm/expense-tracker` on `main` with [`values-gitops.yaml`](helm/expense-tracker/values-gitops.yaml),
  destination namespace `expense-tracker-gitops`, `syncPolicy.automated` with `prune` and `selfHeal`.
- A change is a commit: bumping the image tag or `replicaCount` in `values-gitops.yaml` and pushing
  is the whole deployment. If someone changes the cluster by hand (`kubectl scale`, deleting a pod),
  Argo CD reports the drift and reverts it.

The walkthrough with exact commands is in [`gitops/README.md`](gitops/README.md).
Evidence: [`m10-argocd-app-synced.png`](docs/screenshots/m10-argocd-app-synced.png),
[`m10-argocd-self-heal.png`](docs/screenshots/m10-argocd-self-heal.png),
[`m10-argocd-ui.png`](docs/screenshots/m10-argocd-ui.png).

---

## 14. Monitoring

- **Metrics endpoint** – `prometheus-fastapi-instrumentator` exposes `/metrics` on the backend:
  `http_requests_total{handler,method,status}` and the `http_request_duration_seconds` histogram
  (16 metric families in total). The `handler` label is the route template, so cardinality stays flat.
  [`m9-curl-metrics.png`](docs/screenshots/m9-curl-metrics.png).
- **Prometheus** – `kube-prometheus-stack` 92.9.0 installed in namespace `monitoring` from
  [`monitoring/kube-prometheus-stack-values.yaml`](monitoring/kube-prometheus-stack-values.yaml)
  (2-day retention, 15 s scrape interval, `*SelectorNilUsesHelmValues: false` so every ServiceMonitor
  and PrometheusRule is picked up). The chart's `ServiceMonitor` selects the backend Service by its
  `app.kubernetes.io/*` labels; `Status > Targets` lists `serviceMonitor/expense-tracker/expense-tracker-backend`
  with one `up` entry per backend pod. [`m9-prometheus-targets.png`](docs/screenshots/m9-prometheus-targets.png).
- **PromQL I used** ([`m9-promql.txt`](docs/screenshots/m9-promql.txt)):

  ```promql
  up{namespace="expense-tracker"}
  sum(rate(http_requests_total{namespace="expense-tracker"}[5m])) by (handler)
  sum(rate(http_requests_total{namespace="expense-tracker", handler=~"/api.*"}[5m])) by (method, status)
  histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket{namespace="expense-tracker", handler=~"/api.*"}[5m])))
  sum(rate(http_requests_total{namespace="expense-tracker", handler=~"/api.*", status=~"5.."}[5m]))
    / sum(rate(http_requests_total{namespace="expense-tracker", handler=~"/api.*"}[5m]))
  kube_horizontalpodautoscaler_status_current_replicas{namespace="expense-tracker"}
  ```

- **Grafana** – dashboard "Expense Tracker - API overview" (uid `expense-tracker`,
  [`monitoring/dashboards/expense-tracker.json`](monitoring/dashboards/expense-tracker.json), auto-imported
  by the sidecar from [`monitoring/grafana-dashboard-configmap.yaml`](monitoring/grafana-dashboard-configmap.yaml)):
  requests/s, 5xx error ratio, p95 latency, backend pods up, requests/s by handler, p50/p95/p99,
  responses by status class, HPA current/desired/max replicas.
  `kubectl -n monitoring port-forward svc/kube-prometheus-stack-grafana 13000:80`, then
  http://localhost:13000/d/expense-tracker (user `admin`, password from
  `kubectl -n monitoring get secret kube-prometheus-stack-grafana -o jsonpath='{.data.admin-password}' | base64 -d`;
  the values file sets the placeholder `grafana-local-only`). The sidecar imported the dashboard from the
  `expense-tracker-grafana-dashboard` ConfigMap (`provisioned: true`, Grafana 13.2.4, Prometheus as the
  default datasource – [`m9-grafana-health.txt`](docs/screenshots/m9-grafana-health.txt)).

![Grafana dashboard](docs/screenshots/m9-grafana-dashboard.png)
- **Alert rules** ([`monitoring/prometheusrule.yaml`](monitoring/prometheusrule.yaml)):
  `ExpenseTrackerBackendDown` (no scrape target for 2 m), `ExpenseTrackerPodCrashLooping`,
  `ExpenseTrackerHighErrorRate` (>5 % 5xx on `/api` for 5 m), `ExpenseTrackerHighLatencyP95` (>500 ms for 5 m),
  `ExpenseTrackerHpaAtMax` (at max replicas for 10 m). During the load test both `HighLatencyP95` and
  `HpaAtMax` went to `pending`, which is exactly what they are for.

![Prometheus targets](docs/screenshots/m9-prometheus-targets.png)

---

## 15. Troubleshooting lab

[`troubleshooting/`](troubleshooting/README.md) holds two manifests I break on purpose and the
runbook I follow (`get pods` -> `describe` -> `logs --previous` -> `get endpoints` -> `describe ingress`):

| Scenario | Apply | Symptom | Reveals it | Fix |
|---|---|---|---|---|
| Wrong image tag (`broken-image.yaml`) | `kubectl apply -f troubleshooting/broken-image.yaml` | new backend pods `ImagePullBackOff`, old ones keep serving (`maxUnavailable: 0`) | `kubectl describe pod` -> `manifest unknown` | `helm upgrade --install ...` with the real SHA tag |
| Service selector mismatch (`broken-service.yaml`) | `kubectl apply -f troubleshooting/broken-service.yaml` | pods Ready, `/api` returns 503 through the ingress | `kubectl get endpoints expense-tracker-backend` -> `<none>` | `helm upgrade --install ...` (or `kubectl patch svc`) |

Because Helm is the source of truth, the fix is always the same `helm upgrade --install` command.
Captures: `docs/screenshots/m10-troubleshooting-broken-image.png` and
`docs/screenshots/m10-troubleshooting-broken-service.png`.

---

## 16. Known issues and limitations

1. **AWS apply, console and destroy evidence.** The Terraform code is validated and a real
   `terraform plan` (61 resources) was produced against LocalStack; the `apply` / AWS Console /
   `destroy` captures depend on running it against a real AWS account (section 11).
2. **Images are built for amd64 only.** On the Apple Silicon development machine k3s runs them through
   qemu emulation, which is why p95 latency under the HPA load test was about 1 s. A
   `docker buildx --platform linux/amd64,linux/arm64` build would remove this; EKS nodes (`t3.medium`)
   are amd64, so production is unaffected.
3. **The CI deploy job is skipped without cluster credentials.** It runs `helm lint` and then deploys
   only when the `KUBE_CONFIG_DATA` secret exists; for the local cluster I deployed with Helm by hand
   and through Argo CD.
4. **PostgreSQL runs inside the cluster** as a single-replica StatefulSet with one PVC: no replication,
   no automated backups. A production setup would use Amazon RDS (the chart supports an external
   `DATABASE_URL` through `existingSecret`).
5. **Single-user application without authentication.** Anyone who can reach the API can read and
   change expenses; adding auth (for example OIDC at the ingress) is out of scope for the capstone.
6. **No TLS on the local ingress** (`http://expense.local`); `values-prod.yaml` expects TLS from the
   ingress controller / cert-manager on EKS.
7. **Unfixed CVEs do not block the pipeline.** Trivy runs with `ignore-unfixed`, so OS packages with no
   available fix are reported in the SARIF upload but do not fail the gate (policy in `SECURITY.md`).
8. **The Argo CD image tag is bumped by a commit**, not automatically; an image-updater or a CI step
   that edits `values-gitops.yaml` would close that loop.

---

## 17. Evidence index

The complete table (every file, one row per rubric criterion) is in
[`docs/screenshots/README.md`](docs/screenshots/README.md). The key captures per module:

| Module | Key evidence |
|---|---|
| M1 Application | [`m1-app-dashboard.png`](docs/screenshots/m1-app-dashboard.png), [`m1-app-mobile.png`](docs/screenshots/m1-app-mobile.png), [`m1-api-curl.png`](docs/screenshots/m1-api-curl.png), [`m1-alembic-migration.png`](docs/screenshots/m1-alembic-migration.png) |
| M2 Testing | [`m2-pytest-v.png`](docs/screenshots/m2-pytest-v.png), [`m2-ruff-bandit-pip-audit.png`](docs/screenshots/m2-ruff-bandit-pip-audit.png) |
| M3 Git | [`m3-github-commits.png`](docs/screenshots/m3-github-commits.png), [`m3-git-log.png`](docs/screenshots/m3-git-log.png), [`m3-gitignore.png`](docs/screenshots/m3-gitignore.png) |
| M4 Docker | [`m4-docker-compose-up.png`](docs/screenshots/m4-docker-compose-up.png), [`m4-docker-images.png`](docs/screenshots/m4-docker-images.png), [`m4-non-root.png`](docs/screenshots/m4-non-root.png), [`m4-app-localhost-3000.png`](docs/screenshots/m4-app-localhost-3000.png) |
| M5 CI/CD | [`m5-actions-run.png`](docs/screenshots/m5-actions-run.png), [`m5-workflow-summary.png`](docs/screenshots/m5-workflow-summary.png), [`m5-ghcr-backend.png`](docs/screenshots/m5-ghcr-backend.png), [`m5-ghcr-frontend.png`](docs/screenshots/m5-ghcr-frontend.png) |
| M6 Trivy | [`m6-trivy-scan-output.png`](docs/screenshots/m6-trivy-scan-output.png), [`m6-trivy-config.png`](docs/screenshots/m6-trivy-config.png), [`m6-trivy-explanation.txt`](docs/screenshots/m6-trivy-explanation.txt) |
| M7 Terraform | [`m7-terraform-init-validate.png`](docs/screenshots/m7-terraform-init-validate.png), [`m7-terraform-plan.png`](docs/screenshots/m7-terraform-plan.png), [`m7-terraform-plan-summary.png`](docs/screenshots/m7-terraform-plan-summary.png) – apply/console/destroy: see section 11 and section 16 |
| M8 Kubernetes + Helm | [`m8-kubectl-get-pods.png`](docs/screenshots/m8-kubectl-get-pods.png), [`m8-kubectl-get-svc.png`](docs/screenshots/m8-kubectl-get-svc.png), [`m8-helm-list.png`](docs/screenshots/m8-helm-list.png), [`m8-app-via-ingress.png`](docs/screenshots/m8-app-via-ingress.png), [`m8-hpa.png`](docs/screenshots/m8-hpa.png) |
| M9 Monitoring | [`m9-curl-metrics.png`](docs/screenshots/m9-curl-metrics.png), [`m9-prometheus-targets.png`](docs/screenshots/m9-prometheus-targets.png), [`m9-promql.png`](docs/screenshots/m9-promql.png), [`m9-grafana-dashboard.png`](docs/screenshots/m9-grafana-dashboard.png) |
| M10 Presentation + docs | this README, [`demo/presentation.pptx`](demo/presentation.pptx) / [`demo/presentation.pdf`](demo/presentation.pdf), the demo video in [`demo/`](demo/README.md), [`m10-argocd-app-synced.png`](docs/screenshots/m10-argocd-app-synced.png), `m10-troubleshooting-*.png` |

Git: every commit is by Om Malviya and describes one change ([`m3-git-log.txt`](docs/screenshots/m3-git-log.txt)
shows the history at the time of capture; the live history is on GitHub). `.gitignore` excludes `.env`, `__pycache__`, `.venv`, `node_modules`,
`dist`, Terraform state and `terraform.tfvars`, verified with `git check-ignore -v`.

---

## 18. Presentation and demo video

Everything for the final presentation is in [`demo/`](demo/README.md):

| File | What it is |
|---|---|
| [`demo/presentation.pptx`](demo/presentation.pptx) | The slide deck (11 slides): overview, tech stack, architecture, CI/CD, security, Terraform, Kubernetes + Helm, Argo CD, observability, key learnings |
| [`demo/presentation.pdf`](demo/presentation.pdf) | The same deck as PDF |
| `demo/expense-tracker-demo.mp4` | The recorded presentation and live walkthrough |

The video follows the order required in [`SUBMISSION.md`](SUBMISSION.md): the slides first, then the
codebase, a push that triggers the GitHub Actions pipeline end to end, Terraform (`plan`, `apply`
output and the AWS Console view of the VPC and EKS cluster), the Argo CD application in sync, the
Kubernetes workloads (`kubectl get pods`, services, ingress), the Prometheus Targets page with the
application `UP`, and the live Grafana dashboard.

---

## 19. Lessons learned

These are the things that actually went wrong or surprised me while building this, in the order I hit them.

1. **A secret scanner will match your own documentation.** The first pipeline run failed in Gitleaks
   because my custom `postgresql+psycopg://<user>:<password>@` rule matched the example connection string in
   a README. The fix (`ec416e2`) was placeholders in the docs plus an allow-list by value and path –
   not disabling the rule. Earlier, a capturing group in that regex made Gitleaks report `+psycopg` as
   the secret, so the allow-list could never match; a non-capturing group and `regexTarget = "line"` solved it.
2. **Trivy silently ignores a misplaced key.** `ignore-unfixed: true` at the top level of `trivy.yaml`
   does nothing; the first scan reported 44 HIGH findings and exit code 1. It has to live under
   `vulnerability:`. I also pass the ignore file through the action input because a relative
   `ignorefile:` inside the config did not resolve the same way locally and in CI.
3. **Pin the scanner, not just the action.** `aquasecurity/trivy-action` is pinned to `v0.36.0` *and*
   `version: v0.75.0`, because the action's default Trivy build was removed upstream once and broke installs.
4. **pip itself is attack surface.** Trivy flagged CVEs in the libraries pip vendors, and nothing at
   runtime needs pip, so the backend Dockerfile uninstalls `pip`, `setuptools` and `wheel` after the
   install step. Likewise `nginx-unprivileged:1.27-alpine` carried fixable HIGH OS CVEs; `1.30-alpine` is clean.
   A clean scan is only true on the day it runs: on 2026-10-26 the unchanged frontend image failed the
   gate with three new HIGH CVEs (`brotli-libs`, `curl`/`libcurl`) published after my last build. The
   fix was `apk upgrade --no-cache` in the runtime stage (as root, then back to uid 101), which pulls the
   patched Alpine packages without waiting for an upstream image rebuild
   ([run 40338536035](https://github.com/om-malviya/expense-tracker-devops/actions/runs/40338536035) red,
   [run 40339582631](https://github.com/om-malviya/expense-tracker-devops/actions/runs/40339582631) green).
5. **A ServiceMonitor selects Services, not pods.** Revision 1 of the chart used the pod selector labels
   (`app=expense-tracker-backend`) in the ServiceMonitor; the Service only carries `app.kubernetes.io/*`
   labels, so Prometheus found no target. Revision 2 matches on exactly those labels – a Helm upgrade
   with no pod restart ([`m9-prometheus-targets.txt`](docs/screenshots/m9-prometheus-targets.txt)).
6. **Pod Security `restricted` is a good regression test.** Turning it on at the namespace forced me to
   set `runAsNonRoot`, `seccompProfile`, `allowPrivilegeEscalation: false` and `drop: [ALL]` on every
   container, including Postgres (uid 70 with `fsGroup` so the PVC is writable) and emptyDirs for a
   read-only root filesystem.
7. **The HPA needs CPU requests and a little patience.** Utilisation is a percentage of
   `resources.requests.cpu`, and for the first ~1.5 minutes the HPA logged `FailedGetResourceMetric`
   until metrics-server had samples. The Deployment must also *not* set `spec.replicas` while the HPA is
   enabled, otherwise every `helm upgrade` resets the replica count.
8. **GitHub Actions expression quirks.** `env.*` is not available inside the workflow-level `env` block,
   and `secrets.*` cannot be used in a step-level `if`, so the image names are spelled out and the
   kubeconfig presence check is materialised into `HAS_KUBECONFIG`.
9. **Lint config matters for third-party code.** ruff tried to sort Alembic's imports as first-party;
   classifying `alembic` as third-party (`b878b66`) kept `ruff check` and `ruff format --check` clean.
10. **You can get further without an AWS account than I expected, but not all the way.** `validate` is
    offline; `plan` needs STS/IAM, which LocalStack 4.6 community emulates (the `latest` tag now needs a
    licence token). `apply`/`destroy` and console evidence genuinely need an account, and saying so is
    better than faking it.
