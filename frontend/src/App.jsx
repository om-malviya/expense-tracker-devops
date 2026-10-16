import { useCallback, useEffect, useRef, useState } from 'react';
import { listExpenses, getSummary, createExpense, updateExpense, deleteExpense } from './api.js';
import Header from './components/Header.jsx';
import KpiCards from './components/KpiCards.jsx';
import CategoryBreakdown from './components/CategoryBreakdown.jsx';
import MonthlyTrend from './components/MonthlyTrend.jsx';
import Filters from './components/Filters.jsx';
import ExpenseTable from './components/ExpenseTable.jsx';
import ExpenseForm from './components/ExpenseForm.jsx';
import EmptyState from './components/EmptyState.jsx';
import ErrorBanner from './components/ErrorBanner.jsx';

const EMPTY_FILTERS = { category: '', month: '', q: '' };

export default function App() {
  const [expenses, setExpenses] = useState([]);
  const [summary, setSummary] = useState(null);
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  // null = closed, { expense: null } = create, { expense: {...} } = edit
  const [modal, setModal] = useState(null);
  const [busyId, setBusyId] = useState(null);
  const requestSeq = useRef(0);

  const load = useCallback(async (activeFilters, { silent = false } = {}) => {
    const seq = ++requestSeq.current;
    if (silent) setRefreshing(true);
    try {
      const [list, stats] = await Promise.all([listExpenses(activeFilters), getSummary()]);
      // Ignore responses from a request that was superseded by a newer filter change.
      if (seq !== requestSeq.current) return;
      setExpenses(list || []);
      setSummary(stats);
      setError(null);
    } catch (err) {
      if (seq !== requestSeq.current) return;
      // Keep whatever we already had on screen; just surface the banner.
      setError(err.message || 'Something went wrong');
    } finally {
      if (seq === requestSeq.current) {
        setLoading(false);
        setRefreshing(false);
      }
    }
  }, []);

  // Initial load and every filter change. Text search is debounced lightly so
  // we do not hit the API on every keystroke.
  useEffect(() => {
    const t = setTimeout(() => load(filters, { silent: !loading }), filters.q ? 250 : 0);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters, load]);

  const retry = () => {
    setLoading(true);
    load(filters);
  };

  // Mutations update local state immediately (optimistic) and then re-fetch so
  // the KPI cards and charts, which come from the summary endpoint, catch up.
  const handleSave = async (values, existing) => {
    if (existing) {
      const saved = await updateExpense(existing.id, values);
      setExpenses((prev) => prev.map((e) => (e.id === saved.id ? saved : e)));
    } else {
      const saved = await createExpense(values);
      setExpenses((prev) => [saved, ...prev]);
    }
    setModal(null);
    load(filters, { silent: true });
  };

  const handleDelete = async (expense) => {
    if (!window.confirm(`Delete "${expense.title}" (${expense.amount})?`)) return;
    setBusyId(expense.id);
    const snapshot = expenses;
    setExpenses((prev) => prev.filter((e) => e.id !== expense.id));
    try {
      await deleteExpense(expense.id);
      load(filters, { silent: true });
    } catch (err) {
      setExpenses(snapshot);
      setError(err.message || 'Delete failed');
    } finally {
      setBusyId(null);
    }
  };

  const hasFilters = Boolean(filters.category || filters.month || filters.q);

  return (
    <div className="shell">
      <Header onAdd={() => setModal({ expense: null })} refreshing={refreshing} />

      <main className="shell-body">
        {error && <ErrorBanner message={error} onRetry={retry} onDismiss={() => setError(null)} />}

        <KpiCards summary={summary} loading={loading} />

        <section className="insight-row">
          <CategoryBreakdown summary={summary} loading={loading} />
          <MonthlyTrend summary={summary} loading={loading} />
        </section>

        <section className="ledger">
          <div className="ledger-head">
            <div>
              <h2>Expenses</h2>
              <p className="ledger-sub">
                {loading ? 'Loading…' : `${expenses.length} ${expenses.length === 1 ? 'entry' : 'entries'}`}
                {hasFilters && !loading ? ' matching your filters' : ''}
              </p>
            </div>
            <Filters
              filters={filters}
              onChange={setFilters}
              onClear={() => setFilters(EMPTY_FILTERS)}
              hasFilters={hasFilters}
            />
          </div>

          {loading ? (
            <ExpenseTable loading />
          ) : expenses.length === 0 ? (
            <EmptyState
              filtered={hasFilters}
              onAdd={() => setModal({ expense: null })}
              onClear={() => setFilters(EMPTY_FILTERS)}
            />
          ) : (
            <ExpenseTable
              expenses={expenses}
              busyId={busyId}
              onEdit={(expense) => setModal({ expense })}
              onDelete={handleDelete}
            />
          )}
        </section>
      </main>

      <footer className="shell-footer">Expense Tracker · DevOps capstone · Om Malviya</footer>

      {modal && (
        <ExpenseForm
          expense={modal.expense}
          onCancel={() => setModal(null)}
          onSave={handleSave}
        />
      )}
    </div>
  );
}
