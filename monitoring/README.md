# monitoring/ - Prometheus + Grafana for the Expense Tracker

The backend exposes `/metrics` (prometheus-fastapi-instrumentator). kube-prometheus-stack brings the
Prometheus Operator, Prometheus, Alertmanager, Grafana, node-exporter and kube-state-metrics; the files
in this folder tell it what to scrape, what to alert on and what to draw.

| File | Purpose |
|---|---|
| `kube-prometheus-stack-values.yaml` | Helm values: 2d retention, small requests, selectors that pick up *every* ServiceMonitor/PrometheusRule (`*SelectorNilUsesHelmValues: false`), Grafana sidecar that imports ConfigMaps labelled `grafana_dashboard: "1"`, FAKE Grafana admin password placeholder |
| `servicemonitor.yaml` | Standalone scrape config for the backend Service - only needed when the chart is installed with `serviceMonitor.enabled=false` (its default); `values-dev.yaml` / `values-prod.yaml` enable the chart's own |
| `prometheusrule.yaml` | Alerts: `ExpenseTrackerBackendDown`, `ExpenseTrackerPodCrashLooping`, `ExpenseTrackerHighErrorRate` (>5 % 5xx), `ExpenseTrackerHighLatencyP95` (>0.5 s), `ExpenseTrackerHpaAtMax` |
| `dashboards/expense-tracker.json` | Grafana dashboard (uid `expense-tracker`): requests/s, error ratio, p95, pods up, requests by handler, latency percentiles, status classes, HPA replicas |
| `grafana-dashboard-configmap.yaml` | The same JSON wrapped in a ConfigMap in namespace `monitoring` so the sidecar auto-imports it |

## Install

```bash
# 1. the stack (namespace monitoring, ~2 minutes until every pod is Running)
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace -f monitoring/kube-prometheus-stack-values.yaml
kubectl -n monitoring get pods

# 2. the app with its ServiceMonitor (values-dev.yaml already sets serviceMonitor.enabled=true) ...
helm upgrade --install expense-tracker helm/expense-tracker -n expense-tracker -f helm/expense-tracker/values-dev.yaml
# ... or, if the chart was installed with the default values, the standalone ServiceMonitor
kubectl apply -f monitoring/servicemonitor.yaml

# 3. alert rules and the dashboard
kubectl apply -f monitoring/prometheusrule.yaml
kubectl apply -f monitoring/grafana-dashboard-configmap.yaml
```

## Look at it

```bash
# raw metrics straight from a backend pod
kubectl -n expense-tracker port-forward svc/expense-tracker-backend 8000:8000 &
curl -s http://localhost:8000/metrics | grep -E '^http_requests_total' | head

# Prometheus: Status > Targets must list serviceMonitor/expense-tracker/expense-tracker-backend as UP
kubectl -n monitoring port-forward svc/kube-prometheus-stack-prometheus 9090:9090 &
open http://localhost:9090/targets

# Grafana: admin / grafana-local-only (the placeholder in the values file), dashboard "Expense Tracker - API overview"
kubectl -n monitoring port-forward svc/kube-prometheus-stack-grafana 3000:80 &
open http://localhost:3000/d/expense-tracker
```

## PromQL behind the panels and alerts

| Panel / alert | Query |
|---|---|
| Requests / s | `sum(rate(http_requests_total{namespace="expense-tracker"}[1m]))` |
| Requests / s by handler | `sum by (handler, method) (rate(http_requests_total{namespace="expense-tracker", handler!~"/metrics\|/health\|/ready"}[1m]))` |
| 5xx error ratio | `sum(rate(http_requests_total{namespace="expense-tracker",status=~"5.."}[5m])) / sum(rate(http_requests_total{namespace="expense-tracker"}[5m]))` |
| p95 latency | `histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket{namespace="expense-tracker"}[5m])))` |
| Backend pods up | `sum(up{namespace="expense-tracker", job=~".*backend.*"})` |
| HPA replicas | `kube_horizontalpodautoscaler_status_current_replicas{namespace="expense-tracker"}` vs `..._spec_max_replicas` |
| ExpenseTrackerBackendDown | `sum(up{namespace="expense-tracker", job=~".*backend.*"}) == 0` for 2m |
| ExpenseTrackerHighErrorRate | 5xx ratio of `handler=~"/api.*"` `> 0.05` for 5m |
| ExpenseTrackerHighLatencyP95 | p95 of `handler=~"/api.*"` `> 0.5` for 5m |
| ExpenseTrackerHpaAtMax | `current_replicas >= spec_max_replicas` for 10m |

The `handler` label is the FastAPI route template (`/api/expenses/{id}`), not the concrete URL, so the
"by handler" panel stays at a handful of series no matter how many expenses exist.

## Generating load so the panels move

```bash
# through the ingress (expense.local in /etc/hosts), 200 requests across the main endpoints
for i in $(seq 1 200); do
  curl -s -o /dev/null -H 'Host: expense.local' http://127.0.0.1/api/expenses
  curl -s -o /dev/null -H 'Host: expense.local' http://127.0.0.1/api/expenses/summary
  curl -s -o /dev/null -X POST -H 'Host: expense.local' -H 'Content-Type: application/json' \
    -d '{"title":"load test","amount":12.50,"category":"food","spent_on":"2026-10-16","payment_method":"upi"}' \
    http://127.0.0.1/api/expenses
done
# a few 404s to make the 4xx band visible
for i in $(seq 1 20); do curl -s -o /dev/null -H 'Host: expense.local' http://127.0.0.1/api/expenses/999999; done

# sustained CPU load to watch the HPA scale (needs metrics-server; k3s has it built in)
kubectl -n expense-tracker run load --rm -it --image=busybox --restart=Never -- \
  sh -c 'while true; do wget -q -O- http://expense-tracker-backend:8000/api/expenses/summary >/dev/null; done'
kubectl -n expense-tracker get hpa -w
```

Within ~30 s the "Requests / s" stat moves, after 1-2 minutes the HPA panel shows `current` climbing.
