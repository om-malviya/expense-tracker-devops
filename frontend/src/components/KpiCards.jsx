import { formatINR, labelFor, currentMonth, monthLabel } from '../utils.js';

// Four headline numbers from GET /api/expenses/summary. While the first load is
// in flight each value is a grey skeleton bar so the layout does not jump.
export default function KpiCards({ summary, loading }) {
  const cards = [
    {
      key: 'month',
      label: `Spent in ${monthLabel(currentMonth())}`,
      value: summary ? formatINR(summary.this_month_total) : '',
      hint: 'All categories, this calendar month',
    },
    {
      key: 'count',
      label: 'Expenses recorded',
      value: summary ? String(summary.count) : '',
      hint: summary ? `${formatINR(summary.total)} all time` : '',
    },
    {
      key: 'top',
      label: 'Top category',
      value: summary && summary.top_category ? labelFor(summary.top_category) : '—',
      hint: 'Largest share of total spend',
    },
    {
      key: 'avg',
      label: 'Average per day',
      value: summary ? formatINR(summary.average_per_day_this_month) : '',
      hint: 'This month so far',
    },
  ];

  return (
    <section className="kpi-grid" aria-label="Key figures">
      {cards.map((c) => (
        <article className="kpi" key={c.key}>
          <div className="kpi-label">{c.label}</div>
          {loading ? (
            <div className="skeleton skeleton-kpi" />
          ) : (
            <div className="kpi-value">{c.value || '—'}</div>
          )}
          <div className="kpi-hint">{loading ? '' : c.hint}</div>
        </article>
      ))}
    </section>
  );
}
