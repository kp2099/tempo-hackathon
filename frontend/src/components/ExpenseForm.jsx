import { useState, useEffect } from 'react';
import { Send, Loader2, CheckCircle, AlertTriangle, XCircle, Bot } from 'lucide-react';
import { submitExpense, getEmployees } from '../api/client';
import RiskGauge from './RiskGauge';

const CATEGORIES = [
  { value: 'meals', label: '🍽️ Meals' },
  { value: 'travel', label: '✈️ Travel' },
  { value: 'accommodation', label: '🏨 Accommodation' },
  { value: 'office_supplies', label: '📎 Office Supplies' },
  { value: 'software', label: '💻 Software' },
  { value: 'equipment', label: '🖥️ Equipment' },
  { value: 'training', label: '📚 Training' },
  { value: 'client_entertainment', label: '🎭 Client Entertainment' },
  { value: 'transportation', label: '🚗 Transportation' },
  { value: 'miscellaneous', label: '📦 Miscellaneous' },
];

export default function ExpenseForm() {
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [form, setForm] = useState({
    employee_id: '',
    amount: '',
    category: 'meals',
    merchant: '',
    description: '',
    receipt_attached: true,
  });

  useEffect(() => {
    loadEmployees();
  }, []);

  const loadEmployees = async () => {
    try {
      const res = await getEmployees();
      setEmployees(res.data);
      if (res.data.length > 0) {
        setForm(f => ({ ...f, employee_id: res.data[0].employee_id }));
      }
    } catch (err) {
      console.error('Failed to load employees:', err);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const amount = parseFloat(form.amount);
    if (!amount || amount <= 0 || isNaN(amount)) {
      setResult({ error: 'Please enter a valid amount greater than 0' });
      return;
    }
    setLoading(true);
    setResult(null);

    try {
      const res = await submitExpense({
        ...form,
        amount,
      });
      setResult(res.data);
    } catch (err) {
      const detail = err.response?.data?.detail;
      let errorMsg = 'Submission failed';
      if (typeof detail === 'string') {
        errorMsg = detail;
      } else if (Array.isArray(detail)) {
        errorMsg = detail.map(d => d.msg || JSON.stringify(d)).join('; ');
      }
      setResult({ error: errorMsg });
    } finally {
      setLoading(false);
    }
  };

  const getStatusConfig = (status) => {
    switch (status) {
      case 'paid':
      case 'auto_approved':
        return { icon: CheckCircle, color: 'text-green-400', bg: 'bg-green-500/10 border-green-500/30', label: '✅ Auto-Approved & Paid' };
      case 'manager_review':
        return { icon: AlertTriangle, color: 'text-yellow-400', bg: 'bg-yellow-500/10 border-yellow-500/30', label: '⏳ Sent to Manager Review' };
      case 'rejected':
      case 'flagged':
        return { icon: XCircle, color: 'text-red-400', bg: 'bg-red-500/10 border-red-500/30', label: '🚨 Flagged / Rejected' };
      default:
        return { icon: Bot, color: 'text-blue-400', bg: 'bg-blue-500/10 border-blue-500/30', label: 'Processing...' };
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-slate-800 rounded-xl border border-slate-700 p-6">
        <h2 className="text-xl font-bold text-white flex items-center gap-2 mb-6">
          <Send className="w-5 h-5 text-blue-400" />
          Submit New Expense
        </h2>

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Employee */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">Employee</label>
            <select
              value={form.employee_id}
              onChange={(e) => setForm({ ...form, employee_id: e.target.value })}
              className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2.5 text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
            >
              {employees.map((emp) => (
                <option key={emp.employee_id} value={emp.employee_id}>
                  {emp.name} ({emp.department}) — {emp.employee_id}
                </option>
              ))}
            </select>
          </div>

          {/* Amount + Category */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Amount (USD)</label>
              <input
                type="text"
                inputMode="decimal"
                pattern="[0-9]*\.?[0-9]*"
                value={form.amount}
                onChange={(e) => {
                  const val = e.target.value;
                  if (val === '' || /^\d*\.?\d*$/.test(val)) {
                    setForm({ ...form, amount: val });
                  }
                }}
                className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2.5 text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="0.00"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Category</label>
              <select
                value={form.category}
                onChange={(e) => setForm({ ...form, category: e.target.value })}
                className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2.5 text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                {CATEGORIES.map((cat) => (
                  <option key={cat.value} value={cat.value}>{cat.label}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Merchant */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">Merchant / Vendor</label>
            <input
              type="text"
              value={form.merchant}
              onChange={(e) => setForm({ ...form, merchant: e.target.value })}
              className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2.5 text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="e.g. Chipotle, Delta Airlines"
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">Description</label>
            <textarea
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              rows={2}
              className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2.5 text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              placeholder="Business lunch with client..."
            />
          </div>

          {/* Receipt toggle */}
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setForm({ ...form, receipt_attached: !form.receipt_attached })}
              className={`relative w-12 h-6 rounded-full transition-colors ${
                form.receipt_attached ? 'bg-blue-600' : 'bg-slate-600'
              }`}
            >
              <span className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white transition-transform ${
                form.receipt_attached ? 'translate-x-6' : ''
              }`} />
            </button>
            <span className="text-sm text-slate-300">Receipt attached</span>
          </div>

          {/* Submit button */}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white font-semibold py-3 rounded-lg flex items-center justify-center gap-2 transition-all disabled:opacity-50"
          >
            {loading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                AgentFin is processing...
              </>
            ) : (
              <>
                <Bot className="w-5 h-5" />
                Submit to AgentFin
              </>
            )}
          </button>
        </form>
      </div>

      {/* Result */}
      {result && !result.error && (
        <div className={`mt-6 rounded-xl border p-6 ${getStatusConfig(result.status).bg}`}>
          <div className="flex items-start gap-4">
            <RiskGauge score={result.risk_score || 0} size={80} />
            <div className="flex-1">
              <h3 className={`text-lg font-bold ${getStatusConfig(result.status).color}`}>
                {getStatusConfig(result.status).label}
              </h3>
              <p className="text-slate-300 text-sm mt-1">{result.approval_reason}</p>

              <div className="grid grid-cols-2 gap-3 mt-4 text-sm">
                <div>
                  <span className="text-slate-400">Expense ID:</span>
                  <span className="text-white ml-2 font-mono">{result.expense_id}</span>
                </div>
                <div>
                  <span className="text-slate-400">Risk Score:</span>
                  <span className="text-white ml-2">{((result.risk_score || 0) * 100).toFixed(1)}%</span>
                </div>
                <div>
                  <span className="text-slate-400">AI Category:</span>
                  <span className="text-white ml-2">{result.ai_category}</span>
                </div>
                <div>
                  <span className="text-slate-400">Anomaly:</span>
                  <span className="text-white ml-2">{((result.anomaly_score || 0) * 100).toFixed(1)}%</span>
                </div>
              </div>

              {/* Memo */}
              {result.memo && (
                <div className="mt-4 bg-slate-900/50 rounded-lg p-3">
                  <p className="text-xs text-slate-400 mb-1">📝 Programmable Memo (On-Chain)</p>
                  <code className="text-xs text-blue-300 font-mono break-all">{result.memo}</code>
                </div>
              )}

              {/* Transaction hash — Tempo blockchain */}
              {result.tx_hash && (
                <div className="mt-3 bg-slate-900/50 rounded-lg p-3">
                  <p className="text-xs text-slate-400 mb-1">⛓️ Tempo Transaction</p>
                  <a
                    href={result.tempo_tx_url || `https://explore.tempo.xyz/tx/${result.tx_hash}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-blue-400 hover:text-blue-300 font-mono break-all underline"
                  >
                    {result.tx_hash}
                  </a>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Error */}
      {result?.error && (
        <div className="mt-6 bg-red-500/10 border border-red-500/30 rounded-xl p-4">
          <p className="text-red-400 font-medium">❌ {result.error}</p>
        </div>
      )}
    </div>
  );
}

