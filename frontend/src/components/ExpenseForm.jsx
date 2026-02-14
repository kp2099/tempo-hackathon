import { useState, useEffect, useRef } from 'react';
import {
  Send, Loader2, CheckCircle, AlertTriangle, XCircle, Bot,
  Sparkles, Mic, Zap, Shield, ExternalLink, ArrowRight,
  DollarSign, Tag, Building, FileText, ReceiptText, Upload, X,
  Paperclip,
} from 'lucide-react';
import { submitExpense, getEmployees, parseExpenseText, uploadReceipt } from '../api/client';
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
  const [receiptFile, setReceiptFile] = useState(null);
  const [receiptPreview, setReceiptPreview] = useState(null);
  const [uploadingReceipt, setUploadingReceipt] = useState(false);
  const fileInputRef = useRef(null);
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

  // ─── Receipt Upload ─────────────────────────────────
  const handleReceiptSelect = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Preview for images
    if (file.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = (ev) => setReceiptPreview(ev.target.result);
      reader.readAsDataURL(file);
    } else {
      setReceiptPreview(null);
    }

    setReceiptFile(file);
    setUploadingReceipt(true);

    try {
      const res = await uploadReceipt(file);
      setForm(f => ({
        ...f,
        receipt_attached: true,
        receipt_file_path: res.data.filepath,
      }));
    } catch (err) {
      console.error('Receipt upload failed:', err);
      // Still mark as attached even if upload fails
      setForm(f => ({ ...f, receipt_attached: true }));
    } finally {
      setUploadingReceipt(false);
    }
  };

  const removeReceipt = () => {
    setReceiptFile(null);
    setReceiptPreview(null);
    setForm(f => ({ ...f, receipt_attached: false, receipt_file_path: '' }));
    if (fileInputRef.current) fileInputRef.current.value = '';
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
    setReceiptFile(null);
    setReceiptPreview(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
    setForm({
      employee_id: employees[0]?.employee_id || '',
      amount: '',
      category: 'meals',
      merchant: '',
      description: '',
      receipt_attached: true,
      receipt_file_path: '',
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

            {/* Receipt Upload */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Receipt</label>
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleReceiptSelect}
                accept="image/*,.pdf"
                className="hidden"
              />
              {!receiptFile ? (
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="flex items-center gap-2 px-4 py-2.5 bg-slate-700 hover:bg-slate-600 border border-slate-600 hover:border-slate-500 rounded-lg text-slate-300 text-sm transition-all"
                  >
                    <Upload className="w-4 h-4" />
                    Upload Receipt
                  </button>
                  <button
                    type="button"
                    onClick={() => setForm({ ...form, receipt_attached: !form.receipt_attached })}
                    className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium transition-all border ${
                      form.receipt_attached
                        ? 'bg-green-600/20 text-green-400 border-green-500/30'
                        : 'bg-slate-700/50 text-slate-400 border-slate-600 hover:text-white hover:bg-slate-700'
                    }`}
                  >
                    <Paperclip className="w-3 h-3" />
                    {form.receipt_attached ? 'Receipt Attached' : 'No Receipt'}
                  </button>
                </div>
              ) : (
                <div className="flex items-center gap-3 bg-green-900/20 border border-green-800/30 rounded-lg px-3 py-2.5">
                  {receiptPreview ? (
                    <img src={receiptPreview} alt="Receipt" className="w-10 h-10 object-cover rounded" />
                  ) : (
                    <FileText className="w-10 h-10 text-green-400" />
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-green-400 font-medium truncate">{receiptFile.name}</p>
                    <p className="text-xs text-green-300/60">
                      {(receiptFile.size / 1024).toFixed(0)} KB
                      {uploadingReceipt && ' • Uploading...'}
                      {!uploadingReceipt && ' • ✅ Uploaded'}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={removeReceipt}
                    className="p-1 text-slate-400 hover:text-red-400 transition-colors"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              )}
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
                    <span className="text-slate-400 text-xs">AI Suggestion</span>
                    <p className="text-white mt-0.5">
                      {result.ai_category}
                      {result.ai_category && result.category && result.ai_category !== result.category && (
                        <span className="text-yellow-400 text-[10px] ml-1">(you chose: {result.category})</span>
                      )}
                      {result.ai_category && result.category && result.ai_category === result.category && (
                        <span className="text-green-400 text-[10px] ml-1">✓ matches</span>
                      )}
                    </p>
                  </div>
                  <div className="bg-slate-900/30 rounded-lg px-3 py-2">
                    <span className="text-slate-400 text-xs">Anomaly Score</span>
                    <p className="text-white mt-0.5">{((result.anomaly_score || 0) * 100).toFixed(1)}%</p>
                  </div>
                </div>

                {/* Ensemble Model Breakdown */}
                {result.layer_scores && (
                  <div className="mt-4 bg-slate-900/40 rounded-lg p-3 border border-slate-700/50">
                    <p className="text-xs text-slate-400 mb-2 flex items-center gap-1">
                      🧠 AI Ensemble Breakdown
                      <span className="text-slate-500 ml-1">
                        (trained on 284K real transactions)
                      </span>
                    </p>
                    <div className="space-y-2">
                      {Object.entries(result.layer_scores).map(([layer, score]) => (
                        <div key={layer} className="flex items-center gap-2">
                          <span className="text-xs text-slate-400 w-36 truncate">
                            {layer.replace(/_/g, ' ')}
                          </span>
                          <div className="flex-1 bg-slate-800 rounded-full h-2">
                            <div
                              className={`h-2 rounded-full transition-all ${
                                score < 0.3 ? 'bg-green-500' :
                                score < 0.6 ? 'bg-yellow-500' : 'bg-red-500'
                              }`}
                              style={{ width: `${Math.min(score * 100, 100)}%` }}
                            />
                          </div>
                          <span className="text-xs text-slate-300 w-12 text-right">
                            {(score * 100).toFixed(1)}%
                          </span>
                        </div>
                      ))}
                    </div>
                    {result.model_used && (
                      <p className="text-xs text-slate-500 mt-2 font-mono">
                        Model: {result.model_used}
                      </p>
                    )}
                  </div>
                )}

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
