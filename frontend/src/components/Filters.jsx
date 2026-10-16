import { CATEGORIES, labelFor } from '../utils.js';

// Filter bar wired straight to the API's query parameters
// (GET /api/expenses?category=&month=&q=). The parent owns the state.
export default function Filters({ filters, onChange, onClear, hasFilters }) {
  const set = (key) => (e) => onChange({ ...filters, [key]: e.target.value });

  return (
    <form className="filterbar" onSubmit={(e) => e.preventDefault()} role="search">
      <label className="filter-field">
        <span className="visually-hidden">Search</span>
        <input
          type="search"
          placeholder="Search title or note…"
          value={filters.q}
          onChange={set('q')}
          aria-label="Search expenses"
        />
      </label>

      <label className="filter-field">
        <span className="visually-hidden">Category</span>
        <select value={filters.category} onChange={set('category')} aria-label="Filter by category">
          <option value="">All categories</option>
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {labelFor(c)}
            </option>
          ))}
        </select>
      </label>

      <label className="filter-field">
        <span className="visually-hidden">Month</span>
        <input type="month" value={filters.month} onChange={set('month')} aria-label="Filter by month" />
      </label>

      {hasFilters && (
        <button type="button" className="btn btn-ghost" onClick={onClear}>
          Clear
        </button>
      )}
    </form>
  );
}
