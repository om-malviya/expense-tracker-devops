# Expense Tracker – frontend

The dashboard for my Expense Tracker capstone. It is a small React 18 app built with
Vite 7, written in plain JSX and CSS (no component library), and served by an
unprivileged nginx in production.

## What it shows

- KPI cards: this month's spend, number of expenses, top category, average per day
- Category breakdown (horizontal bars with percentages) and a 6-month trend chart,
  both drawn with CSS only
- Filter bar (category, month, free-text search) backed by the API query params
- Expense table with add / edit / delete through a modal form that mirrors the
  backend validation rules (amount > 0, title 1-120 chars, fixed category and
  payment-method lists)
- Loading skeleton on first load and an error banner when the API is unreachable,
  so the page never goes blank

## Local development

```bash
npm install
npm run dev          # http://localhost:5173 ; /api is proxied to http://localhost:8000
npm run build        # writes dist/
```

The backend must be running on port 8000 (see `../backend/README.md`).

## Container image

```bash
docker build -t expense-tracker-frontend:local .
docker run --rm -p 3000:8080 -e BACKEND_HOST=host.docker.internal expense-tracker-frontend:local
```

The image is a two-stage build (Node builds the bundle, nginx serves it), runs as
uid 101 and listens on 8080. `BACKEND_HOST` / `BACKEND_PORT` are substituted into
`nginx.conf.template` at start-up so the same image works in docker-compose and in
Kubernetes. `/healthz` is the probe endpoint.

## Layout

```
src/
  main.jsx          React entry point
  App.jsx           data loading, filters, modal state
  api.js            fetch helpers for /api/expenses and /api/expenses/summary
  utils.js          INR formatting, month helpers, validation
  styles.css        the whole stylesheet (light theme, responsive)
  components/       Header, KpiCards, CategoryBreakdown, MonthlyTrend, Filters,
                    ExpenseTable, ExpenseForm, EmptyState, ErrorBanner
```
