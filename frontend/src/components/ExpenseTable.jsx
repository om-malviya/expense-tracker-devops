import { formatINR, formatDate, labelFor } from '../utils.js';

const COLUMNS = ['Date', 'Title', 'Category', 'Paid via', 'Amount', ''];

function SkeletonRows() {
  return (
    <tbody>
      {[0, 1, 2, 3, 4].map((i) => (
        <tr key={i} className="ledger-row">
          {COLUMNS.map((c, j) => (
            <td key={j} data-label={c}>
              <div className="skeleton skeleton-cell" />
            </td>
          ))}
        </tr>
      ))}
    </tbody>
  );
}

// Desktop: a normal table. Below 720px the CSS turns each <tr> into a stacked
// card and uses data-label to print the column name before each value.
export default function ExpenseTable({ expenses = [], loading = false, busyId, onEdit, onDelete }) {
  return (
    <div className="ledger-table-wrap">
      <table className="ledger-table">
        <thead>
          <tr>
            {COLUMNS.map((c, i) => (
              <th key={i} scope="col" className={c === 'Amount' ? 'num' : ''}>
                {c || <span className="visually-hidden">Actions</span>}
              </th>
            ))}
          </tr>
        </thead>
        {loading ? (
          <SkeletonRows />
        ) : (
          <tbody>
            {expenses.map((e) => (
              <tr key={e.id} className={`ledger-row${busyId === e.id ? ' is-busy' : ''}`}>
                <td data-label="Date" className="cell-date">
                  {formatDate(e.spent_on)}
                </td>
                <td data-label="Title" className="cell-title">
                  <span className="title-text">{e.title}</span>
                  {e.note && <span className="title-note">{e.note}</span>}
                </td>
                <td data-label="Category">
                  <span className={`chip chip-${e.category}`}>{labelFor(e.category)}</span>
                </td>
                <td data-label="Paid via" className="cell-method">
                  {labelFor(e.payment_method)}
                </td>
                <td data-label="Amount" className="num cell-amount">
                  {formatINR(e.amount)}
                </td>
                <td className="cell-actions">
                  <button type="button" className="btn btn-small" onClick={() => onEdit(e)} disabled={busyId === e.id}>
                    Edit
                  </button>
                  <button
                    type="button"
                    className="btn btn-small btn-danger"
                    onClick={() => onDelete(e)}
                    disabled={busyId === e.id}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        )}
      </table>
    </div>
  );
}
