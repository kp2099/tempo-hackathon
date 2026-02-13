import { useState, useEffect, useRef } from 'react';
import {
  Send, Loader2, CheckCircle, AlertTriangle, XCircle, Bot,
  Sparkles, Mic, Zap, Shield, ExternalLink, ArrowRight,
  DollarSign, Tag, Building, FileText, ReceiptText,
} from 'lucide-react';
import { submitExpense, getEmployees, parseExpenseText } from '../api/client';
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

const PROCESSING_STAGES = [
  { icon: '🔍', label: 'Analyzing expense data...', sublabel: 'Extracting features & behavioral patterns' },
  { icon: '🧠', label: 'Running AI risk scoring...', sublabel: 'XGBoost model + Isolation Forest anomaly detection' },
  { icon: '📋', label: 'Checking policy compliance...', sublabel: 'Spending limits, receipt rules, duplicate detection' },
  { icon: '⚖️', label: 'Making autonomous decision...', sublabel: 'Three-tier approval: auto-approve / review / reject' },
  { icon: '💰', label: 'Executing on Tempo blockchain...', sublabel: 'TIP-20 transferWithMemo with on-chain audit trail' },
];

export default function ExpenseForm() {
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [stage, setStage] = useState(-1);
  const [nlMode, setNlMode] = useState(false);
  const [nlText, setNlText] = useState('');
  const [nlParsing, setNlParsing] = useState(false);
  const [nlResult, setNlResult] = useState(null);
  const [showConfetti, setShowConfetti] = useState(false);
  const resultRef = useRef(null);
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

  // ─── Natural Language Parsing ────────────────────────
  const handleNLParse = async () => {
    if (!nlText.trim()) return;
    setNlParsing(true);
    setNlResult(null);
    try {
      const res = await parseExpenseText(nlText);
      const parsed = res.data;
      setNlResult(parsed);

      // Auto-fill form fields
      if (parsed.amount) setForm(f => ({ ...f, amount: String(parsed.amount) }));
      if (parsed.merchant) setForm(f => ({ ...f, merchant: parsed.merchant }));
      if (parsed.category) setForm(f => ({ ...f, category: parsed.category }));
      if (parsed.description) setForm(f => ({ ...f, description: parsed.description }));
    } catch (err) {
      console.error('NL parse failed:', err);
    } finally {
      setNlParsing(false);
    }
  };

  // ─── Animated Submission ─────────────────────────────
  const handleSubmit = async (e) => {
    e.preventDefault();
    const amount = parseFloat(form.amount);
    if (!amount || amount <= 0 || isNaN(amount)) {
      setResult({ error: 'Please enter a valid amount greater than 0' });
      return;
    }
    setLoading(true);
    setResult(null);
    setStage(0);
    setShowConfetti(false);

    // Animate through stages while API processes
    const stageTimers = [];
    for (let i = 1; i < PROCESSING_STAGES.length; i++) {
      stageTimers.push(
        setTimeout(() => setStage(i), i * 700)
      );
    }

    try {
      const res = await submitExpense({ ...form, amount });
      // Clear stage timers if response comes back early
      stageTimers.forEach(clearTimeout);
      setStage(PROCESSING_STAGES.length); // done

      // Short delay for final animation
      await new Promise(r => setTimeout(r, 400));
      setResult(res.data);

      // Confetti for auto-approved!
      if (res.data.status === 'paid' || res.data.status === 'auto_approved') {
        setShowConfetti(true);
        setTimeout(() => setShowConfetti(false), 3000);
      }

      // Scroll to result
      setTimeout(() => {
        resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }, 200);
    } catch (err) {
      stageTimers.forEach(clearTimeout);
      const detail = err.response?.data?.detail;
      let errorMsg = 'Submission failed';
      if (typeof detail === 'string') errorMsg = detail;
      else if (Array.isArray(detail)) errorMsg = detail.map(d => d.msg || JSON.stringify(d)).join('; ');
      setResult({ error: errorMsg });
    } finally {
      setLoading(false);
      setStage(-1);
    }
  };

  const getStatusConfig = (status) => {
    switch (status) {
      case 'paid':
      case 'auto_approved':
        return { icon: CheckCircle, color: 'text-green-400', bg: 'bg-green-500/10 border-green-500/30', label: '✅ Auto-Approved & Paid on Tempo', glow: 'glow-green' };
      case 'manager_review':
        return { icon: AlertTriangle, color: 'text-yellow-400', bg: 'bg-yellow-500/10 border-yellow-500/30', label: '⏳ Sent to Manager Review', glow: 'glow-yellow' };
      case 'rejected':
      case 'flagged':
        return { icon: XCircle, color: 'text-red-400', bg: 'bg-red-500/10 border-red-500/30', label: '🚨 Flagged / Rejected', glow: 'glow-red' };
      default:
        return { icon: Bot, color: 'text-blue-400', bg: 'bg-blue-500/10 border-blue-500/30', label: 'Processing...', glow: '' };
    }
  };

  const handleReset = () => {
    setResult(null);
    setNlResult(null);
    setNlText('');
    setForm({
      employee_id: employees[0]?.employee_id || '',
      amount: '',
      category: 'meals',
      merchant: '',
      description: '',
      receipt_attached: true,
    });
  };

  return (
    <div className="max-w-2xl mx-auto">
      {/* ─── Confetti Effect ─── */}
      {showConfetti && (
        <div className="fixed inset-0 pointer-events-none z-50 overflow-hidden">
          {[...Array(50)].map((_, i) => (
            <div
              key={i}
              className="confetti-piece"
              style={{
                left: `${Math.random() * 100}%`,
                animationDelay: `${Math.random() * 2}s`,
                backgroundColor: ['#10b981', '#3b82f6', '#8b5cf6', '#f59e0b', '#ec4899'][i % 5],
              }}
            />
          ))}
        </div>
      )}

      {/* ─── Processing Overlay ─── */}
      {loading && (
        <div className="mb-6 bg-slate-800 rounded-xl border border-blue-500/30 p-6 glow-blue animate-fadeIn">
          <div className="flex items-center gap-3 mb-5">
            <div className="relative">
              <Bot className="w-8 h-8 text-blue-400" />
              <div className="absolute -top-1 -right-1 w-3 h-3 bg-blue-400 rounded-full animate-ping" />
            </div>
            <div>
              <h3 className="text-white font-bold">AgentFin Processing</h3>
              <p className="text-slate-400 text-xs">Autonomous AI evaluation in progress...</p>
            </div>
          </div>

          <div className="space-y-3">
            {PROCESSING_STAGES.map((s, i) => (
              <div
                key={i}
                className={`flex items-center gap-3 px-4 py-2.5 rounded-lg transition-all duration-500 ${
                  i < stage ? 'bg-green-500/10 border border-green-500/20' :
                  i === stage ? 'bg-blue-500/10 border border-blue-500/30 scale-[1.02]' :
                  'bg-slate-700/30 border border-transparent opacity-40'
                }`}
              >
                <span className="text-lg w-6 text-center">
                  {i < stage ? '✅' : i === stage ? s.icon : '⬜'}
                </span>
                <div className="flex-1 min-w-0">
                  <p className={`text-sm font-medium ${
                    i < stage ? 'text-green-400' :
                    i === stage ? 'text-blue-300' : 'text-slate-500'
                  }`}>
                    {s.label}
                  </p>
                  <p className={`text-xs ${
                    i <= stage ? 'text-slate-400' : 'text-slate-600'
                  }`}>
                    {s.sublabel}
                  </p>
                </div>
                {i === stage && (
                  <Loader2 className="w-4 h-4 text-blue-400 animate-spin flex-shrink-0" />
                )}
                {i < stage && (
                  <CheckCircle className="w-4 h-4 text-green-400 flex-shrink-0" />
                )}
              </div>
            ))}
          </div>

          {/* Progress bar */}
          <div className="mt-4 w-full bg-slate-700 rounded-full h-1.5">
            <div
              className="bg-gradient-to-r from-blue-500 to-purple-500 h-1.5 rounded-full transition-all duration-700 ease-out"
              style={{ width: `${Math.min(((stage + 1) / PROCESSING_STAGES.length) * 100, 100)}%` }}
            />
          </div>
        </div>
      )}

      {/* ─── Form Card ─── */}
      {!result && (
        <div className="bg-slate-800 rounded-xl border border-slate-700 p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <Send className="w-5 h-5 text-blue-400" />
              Submit New Expense
            </h2>

            {/* NL Toggle */}
            <button
              type="button"
              onClick={() => { setNlMode(!nlMode); setNlResult(null); }}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                nlMode
                  ? 'bg-purple-600/20 text-purple-400 border border-purple-500/30'
                  : 'bg-slate-700/50 text-slate-400 hover:text-white hover:bg-slate-700'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              {nlMode ? 'AI Mode Active' : 'Try AI Input'}
            </button>
          </div>

          {/* ─── Natural Language Input ─── */}
          {nlMode && (
            <div className="mb-6 bg-purple-900/10 border border-purple-800/30 rounded-xl p-4">
              <p className="text-sm text-purple-300 mb-3 flex items-center gap-2">
                <Sparkles className="w-4 h-4" />
                Describe the expense in plain English — AI will parse it for you
              </p>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={nlText}
                  onChange={(e) => setNlText(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleNLParse()}
                  className="flex-1 bg-slate-700 border border-purple-500/30 rounded-lg px-4 py-2.5 text-white focus:ring-2 focus:ring-purple-500 focus:border-transparent placeholder-slate-400"
                  placeholder='e.g. "Spent $120 at Marriott for Chicago conference"'
                />
                <button
                  type="button"
                  onClick={handleNLParse}
                  disabled={nlParsing || !nlText.trim()}
                  className="px-4 py-2.5 bg-purple-600 hover:bg-purple-500 text-white rounded-lg font-medium transition-colors disabled:opacity-50 flex items-center gap-2"
                >
                  {nlParsing ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Sparkles className="w-4 h-4" />
                  )}
                  Parse
                </button>
              </div>

              {/* Parse result */}
              {nlResult && (
                <div className="mt-3 bg-slate-800/60 rounded-lg p-3 animate-fadeIn">
                  <div className="flex items-center gap-2 mb-2">
                    <CheckCircle className="w-4 h-4 text-green-400" />
                    <span className="text-sm text-green-400 font-medium">
                      Parsed! Confidence: {(nlResult.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    {nlResult.amount && (
                      <div className="flex items-center gap-1.5 text-slate-300">
                        <DollarSign className="w-3 h-3 text-green-400" />
                        ${nlResult.amount.toFixed(2)}
                      </div>
                    )}
                    {nlResult.merchant && (
                      <div className="flex items-center gap-1.5 text-slate-300">
                        <Building className="w-3 h-3 text-blue-400" />
                        {nlResult.merchant}
                      </div>
                    )}
                    <div className="flex items-center gap-1.5 text-slate-300">
                      <Tag className="w-3 h-3 text-purple-400" />
                      {nlResult.category}
                    </div>
                    {nlResult.description && (
                      <div className="flex items-center gap-1.5 text-slate-300 col-span-2">
                        <FileText className="w-3 h-3 text-slate-400" />
                        {nlResult.description}
                      </div>
                    )}
                  </div>
                  <p className="text-xs text-slate-500 mt-2">
                    ↓ Fields auto-filled below. Review and submit.
                  </p>
                </div>
              )}
            </div>
          )}

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
              className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white font-semibold py-3 rounded-lg flex items-center justify-center gap-2 transition-all disabled:opacity-50 shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40"
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
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>
        </div>
      )}

      {/* ─── Result Card ─── */}
      <div ref={resultRef}>
        {result && !result.error && (
          <div className={`mt-6 rounded-xl border p-6 animate-slideUp ${getStatusConfig(result.status).bg} ${getStatusConfig(result.status).glow}`}>
            {/* Status Header */}
            <div className="flex items-start gap-4">
              <RiskGauge score={result.risk_score || 0} size={90} />
              <div className="flex-1">
                <h3 className={`text-lg font-bold ${getStatusConfig(result.status).color}`}>
                  {getStatusConfig(result.status).label}
                </h3>
                <p className="text-slate-300 text-sm mt-1">{result.approval_reason}</p>

                {/* Risk Explanation (Plain English) */}
                {result.risk_explanation && (
                  <div className="mt-3 bg-slate-900/40 rounded-lg p-3 border border-slate-700/50">
                    <p className="text-xs text-slate-400 mb-1 flex items-center gap-1">
                      <Bot className="w-3 h-3" /> AgentFin's Analysis
                    </p>
                    <p className="text-sm text-slate-200 leading-relaxed">
                      {result.risk_explanation}
                    </p>
                  </div>
                )}

                {/* Quick Stats */}
                <div className="grid grid-cols-2 gap-3 mt-4 text-sm">
                  <div className="bg-slate-900/30 rounded-lg px-3 py-2">
                    <span className="text-slate-400 text-xs">Expense ID</span>
                    <p className="text-white font-mono text-xs mt-0.5">{result.expense_id}</p>
                  </div>
                  <div className="bg-slate-900/30 rounded-lg px-3 py-2">
                    <span className="text-slate-400 text-xs">Risk Score</span>
                    <p className="text-white mt-0.5">{((result.risk_score || 0) * 100).toFixed(1)}%</p>
                  </div>
                  <div className="bg-slate-900/30 rounded-lg px-3 py-2">
                    <span className="text-slate-400 text-xs">AI Category</span>
                    <p className="text-white mt-0.5">{result.ai_category}</p>
                  </div>
                  <div className="bg-slate-900/30 rounded-lg px-3 py-2">
                    <span className="text-slate-400 text-xs">Anomaly Score</span>
                    <p className="text-white mt-0.5">{((result.anomaly_score || 0) * 100).toFixed(1)}%</p>
                  </div>
                </div>

                {/* Fee Sponsorship Badge */}
                {result.fee_sponsored && (
                  <div className="mt-4 flex items-center gap-2 bg-green-900/20 border border-green-800/30 rounded-lg px-3 py-2">
                    <Zap className="w-4 h-4 text-green-400" />
                    <div>
                      <p className="text-xs text-green-400 font-medium">Gas-Free Transaction</p>
                      <p className="text-xs text-green-300/60">
                        Fees sponsored by {result.fee_sponsor_label || 'AgentFin'} — employee pays $0 in gas
                      </p>
                    </div>
                  </div>
                )}

                {/* On-Chain Memo */}
                {result.memo && (
                  <div className="mt-3 bg-slate-900/50 rounded-lg p-3">
                    <p className="text-xs text-slate-400 mb-1">📝 Programmable Memo (On-Chain)</p>
                    <code className="text-xs text-blue-300 font-mono break-all">{result.memo}</code>
                  </div>
                )}

                {/* Transaction hash — Tempo blockchain */}
                {result.tx_hash && (
                  <div className="mt-3 bg-slate-900/50 rounded-lg p-3">
                    <p className="text-xs text-slate-400 mb-1">⛓️ Tempo Blockchain Transaction</p>
                    <a
                      href={result.tempo_tx_url || `https://explore.tempo.xyz/tx/${result.tx_hash}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300 font-mono break-all underline"
                    >
                      <ExternalLink className="w-3 h-3 flex-shrink-0" />
                      {result.tx_hash}
                    </a>
                    <p className="text-xs text-slate-500 mt-1">
                      Verified on Tempo L1 • Chain ID 42431 • Instant Settlement
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Submit Another */}
            <button
              onClick={handleReset}
              className="mt-5 w-full py-2.5 bg-slate-700/50 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2"
            >
              <Send className="w-4 h-4" />
              Submit Another Expense
            </button>
          </div>
        )}

        {/* Error */}
        {result?.error && (
          <div className="mt-6 bg-red-500/10 border border-red-500/30 rounded-xl p-4 animate-slideUp">
            <p className="text-red-400 font-medium">❌ {result.error}</p>
            <button
              onClick={handleReset}
              className="mt-3 text-sm text-red-300 hover:text-white underline"
            >
              Try again
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
