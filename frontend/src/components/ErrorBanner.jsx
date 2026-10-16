// Non-blocking banner for API failures. The rest of the page keeps rendering
// whatever data it last had, so a backend restart never produces a blank screen.
export default function ErrorBanner({ message, onRetry, onDismiss }) {
  return (
    <div className="notice notice-error" role="alert">
      <svg viewBox="0 0 20 20" width="18" height="18" aria-hidden="true">
        <circle cx="10" cy="10" r="8.5" fill="none" stroke="currentColor" strokeWidth="1.8" />
        <path d="M10 6v5M10 13.5v.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      </svg>
      <div className="notice-text">
        <strong>API unavailable.</strong> {message}. The figures below may be stale.
      </div>
      <div className="notice-actions">
        <button type="button" className="btn btn-small" onClick={onRetry}>
          Retry
        </button>
        <button type="button" className="btn btn-icon" onClick={onDismiss} aria-label="Dismiss">
          ×
        </button>
      </div>
    </div>
  );
}
