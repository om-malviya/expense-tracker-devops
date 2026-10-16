# Submission evidence

Every rubric module asks for a screenshot or terminal output. I keep two forms of each
terminal capture side by side:

- `<name>.txt` – the raw command output (first line is the command), so a grader can grep it
  and diff it against their own run;
- `<name>.png` – the same text rendered as a terminal window by `scripts/render-terminal.py`
  (produced via `scripts/capture-evidence.sh <name> "<command>"`).

Browser evidence is a real Chromium screenshot taken with Playwright against the running stack.
GitHub pages (Actions, GHCR, commits) are browser screenshots of github.com.

Where the captures were made:

- **M1, M2, M4** – the local Docker Compose stack (`docker compose up --build -d`, images built from
  this repository at that moment).
- **M3, M5, M6** – `git`/`gh` on the clone, github.com and the GHCR registry API; the pipeline run is
  [38919569372](https://github.com/om-malviya/expense-tracker-devops/actions/runs/38919569372) (commit `ec416e2`).
- **M7** – Terraform 1.16.5 on this machine; the plan ran against a LocalStack 4.6 container (no AWS account, see the last table).
- **M8, M9, M10** – a local k3s cluster (Colima VM, node `colima`, Traefik ingress), images pulled from
  GHCR by the SHA tag `ec416e2b29d120f323c1e0da197c9bed2692f9a9`, kube-prometheus-stack 92.9.0 in namespace `monitoring`.

Rows marked "" name the file that is about to be added; the row is updated when the file lands.

## M1 – Application: Frontend + Backend + Database

| Rubric criterion | File(s) | What it shows | Captured |
|---|---|---|---|
| FastAPI backend starts and responds to `/health` | `m1-api-curl.txt` / `.png` | `curl localhost:8000/health` -> `{"status":"UP"}`, `/ready` -> `{"status":"READY"}`, `/` -> service name, env `compose`, version `1.0.0` | 2026-10-16 |
| Minimum 4 REST endpoints (GET, POST, PUT, DELETE) | `m1-api-curl.txt` / `.png` | six `POST /api/expenses` (201), a 422 validation reply (`amount: -5`, `category: crypto`), `GET /api/expenses` with `?category=`, `?month=` and `?q=` filters, `GET /api/expenses/{id}`, partial `PUT`, `DELETE` (204) followed by the 404, `GET /api/expenses/summary`, first 20 lines of `/metrics` | 2026-10-16 |
| PostgreSQL table managed by Alembic | `m1-alembic-migration.txt` / `.png` | `alembic current` / `alembic history` inside the backend container (`0001_create_expenses (head)`), then `psql` in the postgres container: `\dt`, `\d expenses` (9 columns, pkey + 2 indexes), the seeded rows, and the `alembic_version` table | 2026-10-16 |
| React frontend renders and makes API calls | `m1-app-dashboard.png` | Dashboard at `http://localhost:3000` (1440x900) with KPI cards, category split, 6-month trend and the expense table populated from the API through the nginx `/api/` proxy | 2026-10-16 |
| Responsive and usable UI | `m1-app-mobile.png` | Same page at a 390x844 phone viewport: cards stack, the table collapses into labelled rows | 2026-10-16 |
| API surface (supporting) | `m1-swagger-docs.png` | FastAPI's generated OpenAPI UI at `http://localhost:8000/docs` listing every route | 2026-10-16 |

## M2 – Testing: Pytest + Code Quality

| Rubric criterion | File(s) | What it shows | Captured |
|---|---|---|---|
| `pytest` runs without errors | `m2-pytest-v.txt` / `.png` | `pytest -v` in `backend/`: `20 passed in 0.10s`, Python 3.12.0, pytest 9.1.1 | 2026-10-16 |
| Minimum 5 tests covering 3+ endpoints | `m2-pytest-v.txt` / `.png` | 20 named tests over `/health`, `/ready`, `/`, `/metrics`, `POST`, `GET` list + filters, `GET /{id}`, `PUT`, `DELETE`, `/summary`, CORS | 2026-10-16 |
| Tests use a test database, not production | `m2-pytest-v.txt` / `.png` | The suite runs on a temporary SQLite file set up in `tests/conftest.py` (`DATABASE_URL=sqlite:///<tmp>`, `APP_ENV=test`) – no PostgreSQL involved | 2026-10-16 |
| `pytest.ini` / `conftest.py` present and configured | `m2-pytest-v.txt` / `.png` | header lines `configfile: pytest.ini`, `testpaths: tests`, JUnit report written to `backend/reports/junit.xml` | 2026-10-16 |
| Code quality (supporting) | `m2-ruff-bandit-pip-audit.txt` / `.png` | `ruff check` + `ruff format --check` clean (10 files), Bandit SAST with no findings over 287 lines, `pip-audit` with no known vulnerabilities in `requirements.txt` | 2026-10-16 |

## M3 – Git and GitHub

| Rubric criterion | File(s) | What it shows | Captured |
|---|---|---|---|
| Public GitHub repository | `m3-github-repo.png` | https://github.com/om-malviya/expense-tracker-devops landing page (public, file tree, README) | 2026-10-16 |
| Meaningful commit messages, 10+ commits | `m3-github-commits.png` | The Commits page on github.com, every message describing one change | 2026-10-16 |
| Meaningful commit messages, 10+ commits | `m3-git-log.txt` / `.png` | `git log --oneline --decorate`, the same log with author/date, and `git shortlog -sn`: 16 commits by Om Malviya at capture time (the 17th, "Add offline Terraform plan evidence using a local AWS emulator", was pushed afterwards and appears in `m5-actions-run-cli.txt`) | 2026-10-16 |
| `.gitignore` excludes `.env`, `__pycache__`, `node_modules`, `.venv` | `m3-gitignore.txt` / `.png` | The full `.gitignore` plus `git check-ignore -v` proving the pattern that ignores `backend/.env`, `__pycache__`, `.venv`, `node_modules`, `frontend/dist` and `terraform.tfstate` | 2026-10-16 |

## M4 – Docker: Dockerfile + Compose

| Rubric criterion | File(s) | What it shows | Captured |
|---|---|---|---|
| `backend/Dockerfile` builds successfully | `m4-docker-images.txt` / `.png` | `docker images`: `expense-tracker-backend:local` built from `backend/Dockerfile`, 72.1 MB content size (337 MB on disk) | 2026-10-16 |
| `frontend/Dockerfile` uses a multi-stage build | `m4-docker-images.txt` / `.png`, `m4-docker-compose-up.txt` | `expense-tracker-frontend:local` is 26 MB content size (nginx runtime stage only, no Node); the build log tail shows `Step 11/14 : USER 101` ... `Step 14/14` of the runtime stage | 2026-10-16 |
| Images run as non-root users | `m4-non-root.txt` / `.png` | `id` inside both containers (`uid=10001(appuser)` and `uid=101(nginx)`), `/proc/1/status` Uid 10001, `python -m pip` failing because pip was removed from the backend image, and the `USER` lines of both Dockerfiles | 2026-10-16 |
| `docker compose up --build` starts all three services | `m4-docker-compose-up.txt` / `.png` | Tail of the image build log, container creation order (postgres -> backend -> frontend, gated on health checks) and `docker compose ps` with all three services `(healthy)` on ports 5432 / 8000 / 3000 | 2026-10-16 |
| Browser at `http://localhost:3000` | `m4-app-localhost-3000.png` | The application loaded from the Compose stack (same capture as `m1-app-dashboard.png`) | 2026-10-16 |

## M5 – CI/CD: GitHub Actions Pipeline

| Rubric criterion | File(s) | What it shows | Captured |
|---|---|---|---|
| `.github/workflows/` contains a workflow | `m5-workflow-file.txt` / `.png` | The complete `ci-cd.yml` (5 jobs) | 2026-10-16 |
| Pipeline triggers on push to `main` | `m5-workflow-summary.txt` / `.png` | `grep` of the trigger (`on: push: branches: [main]`), job names, `needs:` edges, Trivy `exit-code`, `docker push` and `github.sha` lines | 2026-10-16 |
| `pytest` runs as a job and fails the build on failure | `m5-actions-run-cli.txt` / `.png` | `gh run view 38919569372`: job "Backend lint + pytest" (21 s) with `20 passed`; `build-scan-push` has `needs: [backend-test, ...]` so a red test job blocks the image build | 2026-10-16 |
| Frontend built in the pipeline | `m5-actions-run-cli.txt` / `.png`, `m5-actions-run.png` | job "Frontend build + npm audit" (8 s): `npm ci`, `npm run build`, `found 0 vulnerabilities` | 2026-10-16 |
| Docker images built for both frontend and backend | `m5-actions-run.png`, `m5-actions-run-cli.txt` | job "Docker build + Trivy gate + push to GHCR" (1 m 43 s) with both build steps | 2026-10-16 |
| Images pushed to GHCR | `m5-ghcr-backend.png`, `m5-ghcr-frontend.png` | The two package pages on github.com with their tags | 2026-10-16 |
| Images pushed to GHCR | `m5-ghcr-pull.txt` / `.png` | Registry API `tags/list` for both repositories; the run log lines `docker push ... digest: sha256:...` | 2026-10-16 |
| Image tags use the git commit SHA | `m5-ghcr-pull.txt` / `.png`, `m5-actions-run-cli.txt` | tags `ec416e2b29d120f323c1e0da197c9bed2692f9a9` and `a9bc797fa227f85b4fca756b3d27259e02f786e3` (full SHAs) next to the `latest` alias; "Print pushed image digests" step output | 2026-10-16 |
| Green pipeline run URL | `m5-actions-run.png`, `m5-actions-list.png` | https://github.com/om-malviya/expense-tracker-devops/actions/runs/38919569372 – all 5 jobs green in 2 m 21 s; the runs list also shows the first run 38919310984 (failed on Gitleaks, fixed in `ec416e2`) | 2026-10-16 |

## M6 – DevSecOps: Trivy Security Scan

| Rubric criterion | File(s) | What it shows | Captured |
|---|---|---|---|
| Trivy scans both images in CI | `m6-trivy-config.txt` / `.png` | `security/trivy.yaml` (severity HIGH/CRITICAL, scanners vuln/secret/misconfig, `vulnerability.ignore-unfixed: true`) and the four Trivy steps of the workflow (gate x2, SARIF x2) | 2026-10-16 |
| Pipeline fails on HIGH/CRITICAL CVEs | `m6-trivy-config.txt` / `.png`, `m6-trivy-scan-output.txt` | the gate steps run with `exit-code: 1`; the SARIF steps with `exit-code: 0` and `continue-on-error` (reporting only) | 2026-10-16 |
| Trivy output from a pipeline run | `m6-trivy-scan-output.txt` / `.png` | Run 38919569372 log: backend `debian 13.7`, 87 OS packages + 30 Python packages, frontend `alpine 3.24.2`, 70 OS packages; Report Summary tables with `0` vulnerabilities for every target; both SARIF uploads succeeded | 2026-10-16 |
| Written explanation of the scan result | `m6-trivy-explanation.txt` | What Trivy scanned and what "clean" means (also in `SECURITY.md` and README section 9) | 2026-10-16 |

## M7 – Terraform: AWS Infrastructure as Code

| Rubric criterion | File(s) | What it shows | Captured |
|---|---|---|---|
| `terraform/` with valid HCL | `m7-terraform-init-validate.txt` / `.png` | `terraform fmt -check -recursive` (no diff) and `terraform validate` -> `Success! The configuration is valid.` | 2026-10-16 |
| `terraform init` completes without errors | `m7-terraform-init-validate.txt` / `.png` | `terraform init -backend=false` downloading `vpc` 5.8.1, `eks` 20.37.1, `iam` 5.52.2, `kms` 2.1.0 and installing the aws 5.100.0, tls, time, cloudinit and null providers | 2026-10-16 |
| `terraform plan` non-empty, no errors | `m7-terraform-plan.txt` / `.png` | Full 1830-line `terraform plan -var-file=terraform.tfvars.example` output via `terraform/localstack/plan.sh` against LocalStack 4.6: `Plan: 61 to add, 0 to change, 0 to destroy.` | 2026-10-16 |
| VPC with at least two public subnets | `m7-terraform-plan-summary.txt` / `.png` | Resource list from the plan: `module.vpc.aws_vpc.this[0]`, `aws_subnet.public[0..1]`, `aws_subnet.private[0..1]`, IGW, NAT gateway + EIP, route tables and associations | 2026-10-16 |
| EKS cluster with a worker node group | `m7-terraform-plan-summary.txt` / `.png` | `module.eks.aws_eks_cluster.this[0]`, `eks_managed_node_group["main"].aws_eks_node_group.this[0]` (t3.medium, 1..3, desired 2), launch template, 4 add-ons, OIDC provider, KMS key, IAM roles, security groups; outputs `cluster_name = expense-tracker-dev-eks`, `cluster_version = 1.31` | 2026-10-16 |
| `terraform.tfvars.example` present, no credentials | `m7-terraform-plan.txt` | the plan is run with `-var-file=terraform.tfvars.example`; the file itself is in `terraform/` and carries no keys | 2026-10-16 |
| `terraform destroy` tears down cleanly | – | **Not available** (no AWS account) – see the last table | – |

## M8 – Kubernetes + Helm

| Rubric criterion | File(s) | What it shows | Captured |
|---|---|---|---|
| `k8s/namespace.yaml` applies cleanly | `m8-namespace.txt` / `.png` | `kubectl apply -f k8s/namespace.yaml` -> `namespace/expense-tracker created`; labels include `pod-security.kubernetes.io/enforce=restricted` | 2026-10-16 |
| Helm chart with `Chart.yaml`, `values.yaml`, templates | `m8-helm-upgrade-install.txt` / `.png`, `m8-helm-list.txt` | the chart renders and installs as `expense-tracker-1.0.0`; the NOTES output comes from `templates/NOTES.txt` | 2026-10-16 |
| `helm upgrade --install` deploys without errors | `m8-helm-upgrade-install.txt` / `.png` | `helm upgrade --install expense-tracker ./helm/expense-tracker -n expense-tracker -f values-dev.yaml --set backend.image.tag=ec416e2b... --set frontend.image.tag=ec416e2b... --wait` -> `STATUS: deployed`, `REVISION: 1` | 2026-10-16 |
| Backend and frontend Deployments with 2+ replicas | `m8-kubectl-get-pods.txt` / `.png` | `deployment.apps/expense-tracker-backend 2/2`, `expense-tracker-frontend 2/2`, `statefulset.apps/expense-tracker-postgres 1/1`, PVC `Bound` (1Gi, `local-path`) | 2026-10-16 |
| ClusterIP Services expose backend and frontend | `m8-kubectl-get-svc.txt` / `.png` | `kubectl get svc,endpoints`: `expense-tracker-backend` ClusterIP :8000, `expense-tracker-frontend` ClusterIP :80, `expense-tracker-postgres` (+ headless) :5432, each with pod IP endpoints | 2026-10-16 |
| Ingress routes `/` to frontend and `/api` to backend | `m8-ingress.txt` / `.png` | `kubectl describe ingress`: host `expense.local`, `/api -> expense-tracker-backend:8000`, `/ -> expense-tracker-frontend:80`, Traefik LoadBalancer `192.168.5.1`; curl through the ingress: `/api/expenses/summary` 200 JSON, `/` returns the SPA, three expenses created and read back | 2026-10-16 |
| `kubectl get pods` shows all pods `Running` | `m8-kubectl-get-pods.txt` / `.png` | 5 pods (2 backend, 2 frontend, postgres-0) `1/1 Running`, 0 restarts, node `colima` | 2026-10-16 |
| `helm list -n <namespace>` | `m8-helm-list.txt` / `.png` | `expense-tracker  expense-tracker  1  deployed  expense-tracker-1.0.0  1.0.0` plus `helm get values` (the `--show-resources` flag is not supported by this Helm version, which the capture shows honestly) | 2026-10-16 |
| Application through the Ingress hostname | `m8-app-via-ingress.png` | Browser at `http://expense.local/` (k3s Traefik) showing the dashboard with the expenses created through the ingress | 2026-10-16 |
| HPA (supporting) | `m8-hpa.txt` / `.png` | `kubectl get hpa -w` while `scripts/load-test.sh` runs (20 workers, 180 s, 9000 requests, 0 failed): `cpu: 22%/60%` 2 replicas -> `528%/60%` 4 replicas -> back to `24%`; `kubectl top pods`; `describe hpa` events `SuccessfulRescale New size: 4` | 2026-10-16 |

## M9 – Observability: Prometheus + Grafana

| Rubric criterion | File(s) | What it shows | Captured |
|---|---|---|---|
| `/metrics` returns Prometheus-formatted output | `m9-curl-metrics.txt` / `.png` | `curl localhost:18000/metrics` through a port-forward to the backend Service: `http_requests_total{handler,method,status}` counters, `http_request_duration_seconds` histogram (count/sum/buckets), 16 metric families | 2026-10-16 |
| Prometheus installed in the cluster | `m9-prometheus-stack-install.txt` / `.png` | `helm upgrade --install kube-prometheus-stack ... -n monitoring -f monitoring/kube-prometheus-stack-values.yaml` -> deployed (chart 92.9.0, app v0.94.1); all 6 pods `Running` (prometheus, alertmanager, grafana, operator, kube-state-metrics, node-exporter) | 2026-10-16 |
| Prometheus scraping the application (Targets `UP`) | `m9-prometheus-targets.txt` / `.png` | the ServiceMonitor selector fix (revision 2), `kubectl get servicemonitor,prometheusrule`, then the Prometheus API `/api/v1/targets`: scrape pool `serviceMonitor/expense-tracker/expense-tracker-backend/0` with one target per backend pod, `health: up` (one freshly scaled pod still `unknown` at that second); `/api/v1/rules` lists the 5 `ExpenseTracker*` alerts | 2026-10-16 |
| Live metrics in PromQL | `m9-promql.txt` / `.png` | `up{namespace="expense-tracker"}` = 1 for 4 pods, request rate by handler and by method/status, p50/p95 latency, 5xx ratio, HPA current replicas = 4; active alerts (`ExpenseTrackerHighLatencyP95`, `ExpenseTrackerHpaAtMax` pending during the load test) | 2026-10-16 |
| Grafana installed and accessible | `m9-grafana-health.txt` / `.png` | `curl localhost:13000/api/health` (Grafana 13.2.4, database ok) through the port-forward, admin user from the Secret, datasources `Prometheus` (default) and `Alertmanager` | 2026-10-16 |
| Grafana panel with live application metrics | `m9-grafana-dashboard.png` | Dashboard "Expense Tracker - API overview" (uid `expense-tracker`) with populated panels: requests/s, 5xx ratio, p95, pods up, requests by handler, latency percentiles, status classes, HPA replicas | 2026-10-16 |
| Dashboard provisioned from the repo (supporting) | `m9-grafana-health.txt` / `.png` | `/api/dashboards/uid/expense-tracker` -> 8 panel titles, `provisioned: true`; the ConfigMap `expense-tracker-grafana-dashboard` labelled `grafana_dashboard=1` that the sidecar imported | 2026-10-16 |

## M10 – Final Presentation + Documentation

| Rubric criterion | File(s) | What it shows | Captured |
|---|---|---|---|
| `README.md` in the project root | `../../README.md` | 16 sections: application, architecture, layout, running, API, tests, Docker, CI/CD, security, Terraform, Kubernetes/Helm, monitoring, troubleshooting, evidence, demo, lessons learned | 2026-10-16 |
| Failure simulation – wrong image tag | `m10-troubleshooting-broken-image.txt` / `.png` | `kubectl apply -f troubleshooting/broken-image.yaml`, new pods in `ImagePullBackOff`, `describe pod` -> `manifest unknown`, recovery with `helm upgrade --install` | |
| Failure simulation – Service selector mismatch | `m10-troubleshooting-broken-service.txt` / `.png` | `kubectl apply -f troubleshooting/broken-service.yaml`, `get endpoints` -> `<none>`, 503 through the ingress, recovery with `helm upgrade --install` | |

## Not available

| Rubric item | Reason |
|---|---|
| M7 – AWS Console screenshot of the VPC and EKS cluster | I had no AWS account while building this project. The configuration is validated and a real `terraform plan` (61 resources) exists against LocalStack, but LocalStack community does not emulate EKS and cannot create real resources, so no console view exists. |
| M7 – `terraform apply` output | Same reason: `apply` needs real AWS credentials. The exact command and capture name (`scripts/capture-evidence.sh m7-terraform-apply "cd terraform && terraform apply -no-color tfplan"`) are in `terraform/README.md`. |
| M7 – `terraform destroy` completion screenshot | Nothing was applied, so there is nothing to destroy. The command for when an account exists: `scripts/capture-evidence.sh m7-terraform-destroy "cd terraform && terraform destroy -no-color -auto-approve"` (expected `Plan: 0 to add, 0 to change, 61 to destroy.`). |
| M5 – Helm deploy executed by the pipeline | The `deploy` job ran and passed (`helm lint`), but my k3s cluster is not reachable from GitHub runners, so `KUBE_CONFIG_DATA` is not set and the job printed the `helm upgrade --install` command instead of running it. I ran that command by hand; see `m8-helm-upgrade-install.txt`. |

## How to reproduce a capture

```bash
# terminal evidence (text + rendered PNG)
scripts/capture-evidence.sh m2-pytest-v "cd backend && pytest -v"

# browser evidence (needs `npx playwright install chromium` once)
npx playwright screenshot --viewport-size=1440,900 --full-page \
  --wait-for-selector '.ledger-row .cell-title' http://localhost:3000 docs/screenshots/m1-app-dashboard.png
```

