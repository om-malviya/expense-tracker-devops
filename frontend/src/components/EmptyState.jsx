// Shown instead of the table when the list is empty. Two flavours: nothing in
// the database yet, or nothing matches the active filters.
export default function EmptyState({ filtered, onAdd, onClear }) {
  return (
    <div className="nothing-here">
      <svg viewBox="0 0 64 64" width="56" height="56" aria-hidden="true">
        <rect x="10" y="14" width="44" height="36" rx="5" fill="none" stroke="currentColor" strokeWidth="2.5" />
        <path d="M10 24h44" stroke="currentColor" strokeWidth="2.5" />
        <path d="M20 36h12M20 42h20" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" opacity="0.45" />
      </svg>
      {filtered ? (
        <>
          <h3>No expenses match</h3>
          <p>Try a different month, category or search term.</p>
          <button type="button" className="btn btn-ghost" onClick={onClear}>
            Clear filters
          </button>
        </>
      ) : (
        <>
          <h3>Your ledger is empty</h3>
          <p>Record your first expense and the charts above will start filling in.</p>
          <button type="button" className="btn btn-accent" onClick={onAdd}>
            Add an expense
          </button>
        </>
      )}
    </div>
  );
}
