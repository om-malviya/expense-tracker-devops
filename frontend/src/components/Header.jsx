// Top bar: logo, product name and the primary "add expense" action.
function Logo() {
  // A rupee coin with a rising tick - drawn inline so the image needs no extra
  // network request and inherits the accent colour from CSS.
  return (
    <svg className="logo-mark" viewBox="0 0 40 40" width="36" height="36" aria-hidden="true">
      <circle cx="20" cy="20" r="18" fill="currentColor" opacity="0.14" />
      <circle cx="20" cy="20" r="13" fill="none" stroke="currentColor" strokeWidth="2.5" />
      <path
        d="M14 14h11M14 18.5h11M14 14c6 0 7.5 1.5 7.5 4.5S19.5 23 14 23l8 6"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default function Header({ onAdd, refreshing }) {
  return (
    <header className="topbar">
      <div className="topbar-brand">
        <Logo />
        <div>
          <div className="topbar-title">Expense Tracker</div>
          <div className="topbar-tag">Where the money went, month by month</div>
        </div>
      </div>
      <div className="topbar-actions">
        {refreshing && <span className="sync-dot" title="Refreshing data" />}
        <button type="button" className="btn btn-accent" onClick={onAdd}>
          <span aria-hidden="true">+</span> Add expense
        </button>
      </div>
    </header>
  );
}
