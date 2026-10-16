// Shared helpers: money formatting, calendar helpers and the client-side
// validation that mirrors the backend's Pydantic rules.

// These two lists must stay in sync with the enums in backend/app/schemas.py.
export const CATEGORIES = [
  'food',
  'transport',
  'housing',
  'utilities',
  'health',
  'entertainment',
  'shopping',
  'education',
  'other',
];

export const PAYMENT_METHODS = ['cash', 'card', 'upi', 'bank_transfer', 'other'];

const PAYMENT_LABELS = {
  cash: 'Cash',
  card: 'Card',
  upi: 'UPI',
  bank_transfer: 'Bank transfer',
  other: 'Other',
};

export function labelFor(value) {
  if (!value) return '';
  if (PAYMENT_LABELS[value]) return PAYMENT_LABELS[value];
  return value.charAt(0).toUpperCase() + value.slice(1);
}

const inr = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

// Indian grouping (1,23,456.00) is what the user expects for rupee amounts.
export function formatINR(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return inr.format(0);
  return inr.format(n);
}

// Compact variant for chart labels where "₹12.5k" reads better than "₹12,500.00".
export function formatINRShort(value) {
  const n = Number(value) || 0;
  if (Math.abs(n) >= 100000) return `₹${(n / 100000).toFixed(1)}L`;
  if (Math.abs(n) >= 1000) return `₹${(n / 1000).toFixed(1)}k`;
  return `₹${n.toFixed(0)}`;
}

function pad(n) {
  return String(n).padStart(2, '0');
}

// Local date, not toISOString(), so the default in the form is not off by one
// for users east of UTC (India is UTC+5:30).
export function todayISO() {
  const d = new Date();
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export function currentMonth() {
  return todayISO().slice(0, 7);
}

// "2026-10" -> "Oct 2026"
export function monthLabel(ym) {
  if (!ym) return '';
  const [y, m] = ym.split('-').map(Number);
  const d = new Date(y, m - 1, 1);
  return d.toLocaleDateString('en-IN', { month: 'short', year: 'numeric' });
}

// "2026-10" -> "Oct"
export function monthShort(ym) {
  if (!ym) return '';
  const [y, m] = ym.split('-').map(Number);
  return new Date(y, m - 1, 1).toLocaleDateString('en-IN', { month: 'short' });
}

// "2026-10-08" -> "08 Oct 2026"
export function formatDate(iso) {
  if (!iso) return '';
  const [y, m, d] = iso.split('-').map(Number);
  return new Date(y, m - 1, d).toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
}

// Last `n` months ending with the current one, ascending, as "YYYY-MM".
// The summary endpoint only returns months that have data, so the trend chart
// pads the gaps with zero so it always shows a fixed 6-month window.
export function lastMonths(n = 6) {
  const out = [];
  const now = new Date();
  for (let i = n - 1; i >= 0; i -= 1) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    out.push(`${d.getFullYear()}-${pad(d.getMonth() + 1)}`);
  }
  return out;
}

// Mirrors backend validation so the user gets the same message instantly,
// before a round trip. The server remains the source of truth.
export function validateExpense(values) {
  const errors = {};
  const title = (values.title || '').trim();
  if (!title) errors.title = 'Title is required';
  else if (title.length > 120) errors.title = 'Title must be 120 characters or fewer';

  const amount = Number(values.amount);
  if (values.amount === '' || values.amount === null || values.amount === undefined) {
    errors.amount = 'Amount is required';
  } else if (!Number.isFinite(amount)) {
    errors.amount = 'Amount must be a number';
  } else if (amount <= 0) {
    errors.amount = 'Amount must be greater than 0';
  } else if (amount > 99999999.99) {
    errors.amount = 'Amount is too large';
  }

  if (!CATEGORIES.includes(values.category)) errors.category = 'Pick a category';
  if (!PAYMENT_METHODS.includes(values.payment_method)) {
    errors.payment_method = 'Pick a payment method';
  }
  if (!/^\d{4}-\d{2}-\d{2}$/.test(values.spent_on || '')) errors.spent_on = 'Enter a valid date';

  return errors;
}

// Convert FastAPI's 422 detail list into {field: message} so server-side
// rejections show up next to the right input.
export function serverErrorsToFields(details) {
  const out = {};
  if (!Array.isArray(details)) return out;
  details.forEach((d) => {
    const field = Array.isArray(d.loc) ? d.loc[d.loc.length - 1] : null;
    if (field && !out[field]) out[field] = d.msg.replace(/^Value error, /, '');
  });
  return out;
}
