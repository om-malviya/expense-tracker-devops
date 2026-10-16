# Demo script – Expense Tracker DevOps capstone

Om Malviya (24BCS10448). This is the 15-step walkthrough from the course, with the exact commands
and URLs for my project. Total time about 20 minutes; the durations are what I timed in rehearsal.
Everything runs from the repository root.

## Before I start (not part of the recording)

```bash
# 1. Compose stack up (steps 1-3)
docker compose up --build -d && docker compose ps

# 2. k3s cluster with the release installed (steps 10-15); kube-prometheus-stack already in `monitoring`
kubectl get pods -n expense-tracker          # 2 backend, 2 frontend, postgres-0 Running
kubectl get pods -n monitoring               # 6 pods Running
grep expense.local /etc/hosts || echo '127.0.0.1 expense.local' | sudo tee -a /etc/hosts

# 3. Port-forwards in two background terminals (steps 14)
kubectl -n monitoring port-forward svc/kube-prometheus-stack-prometheus 19090:9090
kubectl -n monitoring port-forward svc/kube-prometheus-stack-grafana 13000:80

# 4. Browser tabs: localhost:3000, localhost:8000/docs, the Actions page, both GHCR pages,
#    localhost:19090/targets, localhost:13000/d/expense-tracker, http://expense.local/
```

| # | Step | Duration |
|---|---|---|
| 1 | Application | 1 min |
| 2 | API | 1 min |
| 3 | Database | 1 min |
| 4 | Git | 1 min |
| 5 | CI | 2 min (pipeline runs in the background from here) |
| 6 | Docker | 1 min |
| 7 | Security | 1 min |
| 8 | Registry | 1 min |
| 9 | Terraform | 2 min |
| 10 | Kubernetes | 1 min |
| 11 | Helm | 2 min (deploy the SHA from step 5) |
| 12 | Ingress | 1 min |
| 13 | HPA | 2 min |
| 14 | Monitoring | 2 min |
| 15 | Failure simulation | 2 min |

---

### 1. Application (1 min)

> "This is Expense Tracker, my own domain: I log what I spend, and the dashboard tells me this month's total, the split by category and the six-month trend."

- Open http://localhost:3000.
- Click **Add expense**, enter `Coffee with friends`, `320`, `entertainment`, today, `cash`, save; the KPI cards and the table update.
- Narrow the window to phone width to show the responsive layout.

### 2. API (1 min)

> "The frontend only talks to `/api`; the same endpoints are documented by FastAPI itself."

- Open http://localhost:8000/docs and run `GET /api/expenses/summary` from the UI.
- In a terminal:

```bash
curl -s http://localhost:8000/health
curl -s -X POST http://localhost:8000/api/expenses -H 'Content-Type: application/json' \
  -d '{"title":"Metro card top-up","amount":500,"category":"transport","spent_on":"2026-10-14","payment_method":"card"}'
curl -s -X PUT http://localhost:8000/api/expenses/1 -H 'Content-Type: application/json' -d '{"amount":600}'
curl -s -o /dev/null -w '%{http_code}\n' -X DELETE http://localhost:8000/api/expenses/1
curl -s -X POST http://localhost:8000/api/expenses -H 'Content-Type: application/json' \
  -d '{"title":"Bad","amount":-5,"category":"crypto","spent_on":"2026-10-10","payment_method":"cash"}'   # 422
```

### 3. Database (1 min)

> "The table is created by an Alembic migration, which the container runs on every start, not by hand."

```bash
docker compose exec backend alembic current
docker compose exec postgres psql -U expenses -d expenses -c '\d expenses' \
  -c 'select id,title,amount,category,spent_on from expenses order by spent_on desc limit 5;' \
  -c 'select * from alembic_version;'
```

### 4. Git (1 min)

> "One visible change, one meaningful commit – this is the commit the rest of the demo follows through the pipeline."

- Change the tagline on line 28 of `frontend/src/components/Header.jsx`
  (`<div className="topbar-tag">Where the money went, month by month</div>`), for example to
  `Where the money went, month by month – live demo`; it is visible in the header of every page.

```bash
git log --oneline | head -5
git add frontend/src/components/Header.jsx
git commit -m "Show the live-demo tagline in the dashboard header"
git push origin main
```

### 5. CI (2 min)

> "The push triggers the pipeline: tests, frontend build and the static security jobs run in parallel; only if all three are green are the images built, scanned and pushed."

- Open https://github.com/om-malviya/expense-tracker-devops/actions – the new run appears at the top.
- Open the **Backend lint + pytest** job and show `20 passed`.
- Point at the job graph: `build-scan-push` waits for the three jobs; `deploy` waits for it.
- Keep the tab open; the run takes about 2.5 minutes and I come back to it in step 8.
- Reference green run: https://github.com/om-malviya/expense-tracker-devops/actions/runs/38919569372

```bash
gh run watch -R om-malviya/expense-tracker-devops      # optional, in a terminal
```

### 6. Docker (1 min)

> "Two images: a single-stage slim Python image without pip, and a two-stage frontend where Node never reaches the runtime. Both run as non-root."

```bash
docker images | grep -E 'expense-tracker|postgres:16'
docker compose exec backend id            # uid=10001(appuser)
docker compose exec frontend id           # uid=101(nginx)
docker compose exec backend python -m pip --version   # "No module named pip" – on purpose
sed -n '14,19p;26,28p' backend/Dockerfile
sed -n '11p;29p;44p' frontend/Dockerfile
```

### 7. Security (1 min)

> "Trivy scans both images for HIGH and CRITICAL CVEs with a fix available and exits 1 on any – nothing vulnerable reaches the registry. Gitleaks, Bandit, pip-audit and npm audit run before that."

- In the Actions tab open the **Docker build + Trivy gate + push to GHCR** job and expand "Trivy gate: backend image": Report Summary with `0` vulnerabilities on `debian 13.7` and the Python packages.
- Show `security/trivy.yaml` (`ignore-unfixed` under `vulnerability:`) and the `exit-code: "1"` in the workflow.
- Mention the first-ever run, which failed in Gitleaks on my own documentation example – and the fix in `ec416e2`.

### 8. Registry (1 min)

> "Images are tagged with the full commit SHA, so any running pod can be traced back to one commit; `latest` is only an alias."

- https://github.com/om-malviya/expense-tracker-devops/pkgs/container/expense-tracker-backend
- https://github.com/om-malviya/expense-tracker-devops/pkgs/container/expense-tracker-frontend
- The new SHA from step 4 is now in the list (the run from step 5 should be green by now).

```bash
git rev-parse HEAD                                    # the tag to deploy in step 11
docker pull ghcr.io/om-malviya/expense-tracker-backend:$(git rev-parse HEAD)
```

### 9. Terraform (2 min)

> "The AWS side is code: a VPC with two public and two private subnets, and an EKS 1.31 cluster with a managed node group. I had no AWS account, so I show init, validate and a real plan against LocalStack – and say plainly that apply and destroy are not in my evidence."

```bash
sed -n '1,60p' terraform/main.tf
cat terraform/terraform.tfvars.example
cd terraform && terraform init -backend=false && terraform validate && cd ..
grep -n '^Plan:' docs/screenshots/m7-terraform-plan.txt          # Plan: 61 to add, 0 to change, 0 to destroy.
sed -n '/Resources that will be created/,$p' docs/screenshots/m7-terraform-plan-summary.txt | head -30
```

- If LocalStack is running (`docker run -d --name localstack -p 4566:4566 localstack/localstack:4.6`), the plan can be reproduced live with `terraform/localstack/plan.sh` (about 1 minute).

### 10. Kubernetes (1 min)

> "The same three components run on k3s in the `expense-tracker` namespace, which enforces the restricted Pod Security profile."

```bash
kubectl get ns expense-tracker --show-labels
kubectl get pods -n expense-tracker -o wide
kubectl get svc -n expense-tracker
kubectl get deploy,statefulset,pvc -n expense-tracker
```

### 11. Helm (2 min)

> "Everything in the namespace is one Helm release. I deploy the SHA the pipeline just built – this is the 'see the deployment update' part of the demo."

```bash
helm list -n expense-tracker
SHA=$(git rev-parse HEAD)
helm upgrade --install expense-tracker ./helm/expense-tracker -n expense-tracker \
  -f helm/expense-tracker/values-dev.yaml \
  --set backend.image.tag=$SHA --set frontend.image.tag=$SHA --wait --timeout 5m
kubectl -n expense-tracker rollout status deployment/expense-tracker-frontend
kubectl -n expense-tracker get pods -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[0].image}{"\n"}{end}'
helm history expense-tracker -n expense-tracker
```

- Reload http://expense.local/ – the header now shows the change from step 4.
- If anything is wrong: `helm rollback expense-tracker <previous revision> -n expense-tracker`.

### 12. Ingress (1 min)

> "One hostname, two paths: `/` goes to the frontend Service, `/api` to the backend Service. Longest prefix wins."

```bash
kubectl describe ingress expense-tracker -n expense-tracker | sed -n '/Rules/,/Annotations/p'
curl -s -H 'Host: expense.local' http://127.0.0.1/api/expenses/summary
curl -s -H 'Host: expense.local' http://127.0.0.1/ | head -5
```

- Browser: http://expense.local/ (requires `127.0.0.1 expense.local` in `/etc/hosts`).

### 13. HPA (2 min)

> "The backend autoscales on CPU relative to its requests. Twenty parallel workers on the summary endpoint push it past 60 %, and the HPA goes from 2 to 4 replicas."

```bash
kubectl get hpa -n expense-tracker
scripts/load-test.sh http://expense.local 180 20 &      # through the ingress; or the backend ClusterIP
kubectl get hpa -n expense-tracker -w                    # watch TARGETS and REPLICAS climb
```

- After about a minute: `kubectl top pods -n expense-tracker` and `kubectl get pods -n expense-tracker -l app.kubernetes.io/component=backend` (4 pods).
- Leave the load running into step 14 so the Grafana panels move.

### 14. Monitoring (2 min)

> "The backend exposes `/metrics`; a ServiceMonitor tells the Prometheus Operator to scrape every backend pod; Grafana draws request rate, error ratio, latency percentiles and the HPA replica count from those series."

```bash
kubectl -n expense-tracker port-forward svc/expense-tracker-backend 18000:8000 &
curl -s localhost:18000/metrics | grep -E '^http_requests_total' | head
```

- Prometheus (port-forward 19090): http://localhost:19090/targets – `serviceMonitor/expense-tracker/expense-tracker-backend` with every pod `UP`.
  Query tab: `sum(rate(http_requests_total{namespace="expense-tracker"}[1m])) by (handler)` and
  `histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket{namespace="expense-tracker", handler=~"/api.*"}[5m])))`.
- http://localhost:19090/alerts – the five `ExpenseTracker*` rules; `ExpenseTrackerHpaAtMax` goes pending during the load.
- Grafana (port-forward 13000): http://localhost:13000/d/expense-tracker – user `admin`, password:

```bash
kubectl -n monitoring get secret kube-prometheus-stack-grafana -o jsonpath='{.data.admin-password}' | base64 -d; echo
# (the placeholder in monitoring/kube-prometheus-stack-values.yaml is grafana-local-only)
```

### 15. Failure simulation (2 min)

> "Two faults I break on purpose. The first is a tag that was never built; the second is a Service whose selector matches no pod. The triage order is the same every time: pods, describe, endpoints, ingress."

Scenario 1 – wrong image tag:

```bash
kubectl apply -f troubleshooting/broken-image.yaml
kubectl get pods -n expense-tracker -l app.kubernetes.io/component=backend     # new pod ImagePullBackOff, old ones still Running
kubectl describe pod -n expense-tracker -l app.kubernetes.io/component=backend | grep -A3 -E 'Failed|BackOff'
```

Scenario 2 – Service selector mismatch:

```bash
kubectl apply -f troubleshooting/broken-service.yaml
kubectl get endpoints expense-tracker-backend -n expense-tracker               # <none>
curl -si -H 'Host: expense.local' http://127.0.0.1/api/expenses/summary | head -1   # 503
kubectl get svc expense-tracker-backend -n expense-tracker -o jsonpath='{.spec.selector}'; echo
```

Fix for both (Helm is the source of truth):

```bash
helm upgrade --install expense-tracker ./helm/expense-tracker -n expense-tracker \
  -f helm/expense-tracker/values-dev.yaml --set backend.image.tag=$SHA --set frontend.image.tag=$SHA --wait
kubectl get endpoints expense-tracker-backend -n expense-tracker
curl -s -o /dev/null -w '%{http_code}\n' -H 'Host: expense.local' http://127.0.0.1/api/expenses/summary   # 200
```

> "Closing: application, commit, pipeline, image, scan, registry, infrastructure code, Kubernetes, Helm, ingress, autoscaling, monitoring, troubleshooting – every layer is in the repository and every claim has a capture in `docs/screenshots/`."

## Clean-up after the demo

```bash
kill %1 2>/dev/null                      # load-test if still running
docker compose down                      # keep the volume; -v to drop it
# the k3s release stays installed for questions
```
