import { formatINR, formatINRShort, lastMonths, monthShort, monthLabel, currentMonth } from '../utils.js';

// Six vertical bars (last six calendar months, oldest on the left). The summary
// endpoint only returns months with data, so missing months are padded with 0
// to keep a fixed window. Bar height is a percentage of the tallest month.
export default function MonthlyTrend({ summary, loading }) {
  const months = lastMonths(6);
  const byMonth = new Map(
    (summary && Array.isArray(summary.by_month) ? summary.by_month : []).map((m) => [m.month, Number(m.total) || 0]),
  );
  const points = months.map((m) => ({ month: m, total: byMonth.get(m) || 0 }));
  const max = Math.max(...points.map((p) => p.total), 0);
  const thisMonth = currentMonth();
  const anyData = max > 0;

  return (
    <article className="card">
      <div className="card-head">
        <h2>Last 6 months</h2>
        <span className="card-meta">{anyData ? `peak ${formatINRShort(max)}` : 'monthly totals'}</span>
      </div>

      {loading ? (
        <div className="trend">
          {months.map((m) => (
            <div className="trend-col" key={m}>
              <div className="trend-stack">
                <div className="skeleton trend-skeleton" />
              </div>
              <span className="trend-label">{monthShort(m)}</span>
            </div>
          ))}
        </div>
      ) : (
        <div className="trend" role="img" aria-label="Monthly spend for the last six months">
          {points.map((p) => {
            const h = max > 0 ? (p.total / max) * 100 : 0;
            const isCurrent = p.month === thisMonth;
            return (
              <div className="trend-col" key={p.month} title={`${monthLabel(p.month)}: ${formatINR(p.total)}`}>
                <span className="trend-value">{p.total > 0 ? formatINRShort(p.total) : ''}</span>
                <div className="trend-stack">
                  <div
                    className={`trend-bar${isCurrent ? ' is-current' : ''}${p.total === 0 ? ' is-zero' : ''}`}
                    style={{ height: `${p.total > 0 ? Math.max(h, 3) : 0}%` }}
                  />
                </div>
                <span className={`trend-label${isCurrent ? ' is-current' : ''}`}>{monthShort(p.month)}</span>
              </div>
            );
          })}
        </div>
      )}
      {!loading && !anyData && <p className="card-empty">Nothing recorded in this window yet.</p>}
    </article>
  );
}
