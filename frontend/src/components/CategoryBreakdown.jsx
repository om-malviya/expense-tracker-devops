import { formatINR, labelFor } from '../utils.js';

// Horizontal bars, one per category, width = share of total spend.
// Pure CSS: each bar is a div whose width is set inline from the percentage.
export default function CategoryBreakdown({ summary, loading }) {
  const rows = summary && Array.isArray(summary.by_category) ? summary.by_category : [];
  const total = rows.reduce((acc, r) => acc + Number(r.total || 0), 0);
  const sorted = [...rows].sort((a, b) => Number(b.total) - Number(a.total));

  return (
    <article className="card">
      <div className="card-head">
        <h2>By category</h2>
        <span className="card-meta">share of all-time spend</span>
      </div>

      {loading ? (
        <div className="bar-list">
          {[0, 1, 2, 3, 4].map((i) => (
            <div className="skeleton skeleton-bar" key={i} />
          ))}
        </div>
      ) : sorted.length === 0 ? (
        <p className="card-empty">No categories yet. Add your first expense to see the split.</p>
      ) : (
        <ul className="bar-list">
          {sorted.map((row) => {
            const pct = total > 0 ? (Number(row.total) / total) * 100 : 0;
            return (
              <li className="bar-row" key={row.category}>
                <div className="bar-row-top">
                  <span className="bar-name">{labelFor(row.category)}</span>
                  <span className="bar-figures">
                    <span className="bar-amount">{formatINR(row.total)}</span>
                    <span className="bar-pct">{pct.toFixed(1)}%</span>
                  </span>
                </div>
                <div
                  className="bar-track"
                  role="img"
                  aria-label={`${labelFor(row.category)}: ${pct.toFixed(1)} percent, ${row.count} expenses`}
                >
                  <div className="bar-fill" style={{ width: `${Math.max(pct, 1)}%` }} />
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </article>
  );
}
