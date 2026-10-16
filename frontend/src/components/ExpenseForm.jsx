import { useEffect, useState } from 'react';
import { CATEGORIES, PAYMENT_METHODS, labelFor, todayISO, validateExpense, serverErrorsToFields } from '../utils.js';

function initialValues(expense) {
  if (expense) {
    return {
      title: expense.title || '',
      amount: expense.amount != null ? String(expense.amount) : '',
      category: expense.category || 'food',
      payment_method: expense.payment_method || 'upi',
      spent_on: expense.spent_on || todayISO(),
      note: expense.note || '',
    };
  }
  return { title: '', amount: '', category: 'food', payment_method: 'upi', spent_on: todayISO(), note: '' };
}

// Modal used for both "add" (expense === null) and "edit". Validation runs on
// the client with the same rules as the API; if the server still rejects the
// payload (422) its field errors are merged in so the user sees why.
export default function ExpenseForm({ expense, onCancel, onSave }) {
  const [values, setValues] = useState(() => initialValues(expense));
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState('');
  const isEdit = Boolean(expense);

  // Escape closes the dialog, like a native one would.
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape' && !submitting) onCancel();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onCancel, submitting]);

  const update = (key) => (e) => {
    setValues((v) => ({ ...v, [key]: e.target.value }));
    if (errors[key]) setErrors((er) => ({ ...er, [key]: undefined }));
  };

  const submit = async (e) => {
    e.preventDefault();
    const clientErrors = validateExpense(values);
    if (Object.keys(clientErrors).length) {
      setErrors(clientErrors);
      return;
    }
    const payload = {
      title: values.title.trim(),
      amount: Number(Number(values.amount).toFixed(2)),
      category: values.category,
      payment_method: values.payment_method,
      spent_on: values.spent_on,
      note: values.note.trim() ? values.note.trim() : null,
    };
    setSubmitting(true);
    setFormError('');
    try {
      await onSave(payload, expense);
    } catch (err) {
      const fieldErrors = serverErrorsToFields(err.details);
      if (Object.keys(fieldErrors).length) setErrors(fieldErrors);
      else setFormError(err.message || 'Could not save the expense');
      setSubmitting(false);
    }
  };

  const field = (key, label, control) => (
    <div className={`field${errors[key] ? ' has-error' : ''}`}>
      <label htmlFor={`f-${key}`}>{label}</label>
      {control}
      {errors[key] && (
        <span className="field-error" role="alert">
          {errors[key]}
        </span>
      )}
    </div>
  );

  return (
    <div className="veil" onMouseDown={(e) => e.target === e.currentTarget && !submitting && onCancel()}>
      <div className="dialog" role="dialog" aria-modal="true" aria-labelledby="dialog-title">
        <div className="dialog-head">
          <h2 id="dialog-title">{isEdit ? 'Edit expense' : 'New expense'}</h2>
          <button type="button" className="btn btn-icon" onClick={onCancel} aria-label="Close" disabled={submitting}>
            ×
          </button>
        </div>

        <form onSubmit={submit} noValidate>
          {formError && <div className="form-alert">{formError}</div>}

          {field(
            'title',
            'Title',
            <input
              id="f-title"
              type="text"
              maxLength={120}
              placeholder="e.g. Groceries at DMart"
              value={values.title}
              onChange={update('title')}
              autoFocus
            />,
          )}

          <div className="field-pair">
            {field(
              'amount',
              'Amount (₹)',
              <input
                id="f-amount"
                type="number"
                inputMode="decimal"
                min="0.01"
                step="0.01"
                placeholder="0.00"
                value={values.amount}
                onChange={update('amount')}
              />,
            )}
            {field(
              'spent_on',
              'Date',
              <input id="f-spent_on" type="date" value={values.spent_on} onChange={update('spent_on')} />,
            )}
          </div>

          <div className="field-pair">
            {field(
              'category',
              'Category',
              <select id="f-category" value={values.category} onChange={update('category')}>
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {labelFor(c)}
                  </option>
                ))}
              </select>,
            )}
            {field(
              'payment_method',
              'Payment method',
              <select id="f-payment_method" value={values.payment_method} onChange={update('payment_method')}>
                {PAYMENT_METHODS.map((m) => (
                  <option key={m} value={m}>
                    {labelFor(m)}
                  </option>
                ))}
              </select>,
            )}
          </div>

          {field(
            'note',
            'Note (optional)',
            <textarea id="f-note" rows={2} placeholder="Anything worth remembering" value={values.note} onChange={update('note')} />,
          )}

          <div className="dialog-foot">
            <button type="button" className="btn btn-ghost" onClick={onCancel} disabled={submitting}>
              Cancel
            </button>
            <button type="submit" className="btn btn-accent" disabled={submitting}>
              {submitting ? 'Saving…' : isEdit ? 'Save changes' : 'Add expense'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
