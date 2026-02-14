import { useState, useEffect } from 'react';
import { RefreshCw, ExternalLink, CheckCircle, Clock, XCircle, AlertTriangle, Zap, Shield, MessageSquare } from 'lucide-react';
import { getExpenses, approveExpense, rejectExpense, disputeExpense } from '../api/client';
import RiskGauge from './RiskGauge';

const statusConfig = {
  paid: { icon: CheckCircle, color: 'text-green-400', bg: 'bg-green-500/10', label: 'Paid' },
  auto_approved: { icon: CheckCircle, color: 'text-green-400', bg: 'bg-green-500/10', label: 'Auto-Approved' },
  approved: { icon: CheckCircle, color: 'text-green-400', bg: 'bg-green-500/10', label: 'Approved' },
  manager_review: { icon: Clock, color: 'text-yellow-400', bg: 'bg-yellow-500/10', label: 'Review' },
  pending: { icon: Clock, color: 'text-slate-400', bg: 'bg-slate-500/10', label: 'Pending' },
  rejected: { icon: XCircle, color: 'text-red-400', bg: 'bg-red-500/10', label: 'Rejected' },
  flagged: { icon: AlertTriangle, color: 'text-red-400', bg: 'bg-red-500/10', label: 'Flagged' },
  disputed: { icon: MessageSquare, color: 'text-orange-400', bg: 'bg-orange-500/10', label: 'Disputed' },
};

export default function ExpenseList({ filterStatus, showActions }) {
  const [expenses, setExpenses] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [selectedExpense, setSelectedExpense] = useState(null);
  const [actionLoading, setActionLoading] = useState(null);
  const [disputeText, setDisputeText] = useState('');
  const [showDisputeForm, setShowDisputeForm] = useState(null);

  useEffect(() => {
    loadExpenses();
  }, [filterStatus]);

  const loadExpenses = async () => {
    setLoading(true);
    try {
      const params = {};
      if (filterStatus) params.status = filterStatus;
      const res = await getExpenses(params);
      setExpenses(res.data.expenses);
      setTotal(res.data.total);
    } catch (err) {
      console.error('Failed to load expenses:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (expenseId) => {
    setActionLoading(expenseId);
    try {
      await approveExpense(expenseId);
      loadExpenses();
    } catch (err) {
      alert(err.response?.data?.detail || 'Approval failed');
    } finally {
      setActionLoading(null);
    }
  };

  const handleReject = async (expenseId) => {
    setActionLoading(expenseId);
    try {
      await rejectExpense(expenseId);
      loadExpenses();
    } catch (err) {
      alert(err.response?.data?.detail || 'Rejection failed');
    } finally {
      setActionLoading(null);
    }
  };

  const handleDispute = async (expenseId) => {
    if (!disputeText.trim()) {
      alert('Please provide a reason for your dispute.');
      return;
    }
    setActionLoading(expenseId);
    try {
      await disputeExpense(expenseId, disputeText);
      setShowDisputeForm(null);
      setDisputeText('');
      loadExpenses();
    } catch (err) {
      alert(err.response?.data?.detail || 'Dispute failed');
    } finally {
      setActionLoading(null);
    }
  };

  const config = (status) => statusConfig[status] || statusConfig.pending;

  if (loading) {
    return (
      <div className="space-y-3">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="bg-slate-800 rounded-lg border border-slate-700 p-4 animate-pulse">
            <div className="h-4 bg-slate-700 rounded w-48 mb-2" />
            <div className="h-3 bg-slate-700 rounded w-32" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <p className="text-slate-400 text-sm">{total} expense(s)</p>
        <button
          onClick={loadExpenses}
          className="text-slate-400 hover:text-white transition-colors p-1.5 rounded-lg hover:bg-slate-700"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      <div className="space-y-3">
        {expenses.map((expense) => {
          const sc = config(expense.status);
          const Icon = sc.icon;

          return (
            <div
              key={expense.expense_id}
              className="bg-slate-800 rounded-lg border border-slate-700 p-4 hover:border-slate-600 transition-all cursor-pointer"
              onClick={() => setSelectedExpense(
                selectedExpense?.expense_id === expense.expense_id ? null : expense
              )}
            >
              <div className="flex items-center gap-4">
                {/* Risk gauge */}
                <RiskGauge score={expense.risk_score || 0} size={56} />

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs text-slate-400">{expense.expense_id}</span>
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${sc.bg} ${sc.color}`}>
                      <Icon className="w-3 h-3" />
                      {sc.label}
                    </span>
                    {/* Fee sponsored badge */}
                    {expense.tx_hash && (
                      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10px] font-medium bg-green-500/10 text-green-400">
                        <Zap className="w-2.5 h-2.5" />
                        Gas-Free
                      </span>
                    )}
                  </div>
                  <p className="text-white font-medium mt-1">
                    ${expense.amount.toFixed(2)}
                    <span className="text-slate-400 font-normal ml-2">
                      {expense.category} {expense.merchant && `· ${expense.merchant}`}
                    </span>
                  </p>
                  <p className="text-slate-500 text-xs mt-1">{expense.employee_id} · {new Date(expense.submitted_at).toLocaleString()}</p>
                </div>

                {/* Actions */}
                {showActions && (expense.status === 'manager_review' || expense.status === 'disputed') && (
                  <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={() => handleApprove(expense.expense_id)}
                      disabled={actionLoading === expense.expense_id}
                      className="px-3 py-1.5 bg-green-600 hover:bg-green-500 text-white text-xs rounded-lg font-medium transition-colors disabled:opacity-50 flex items-center gap-1"
                    >
                      {actionLoading === expense.expense_id ? (
                        <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      ) : (
                        <CheckCircle className="w-3 h-3" />
                      )}
                      Approve
                    </button>
                    <button
                      onClick={() => handleReject(expense.expense_id)}
                      disabled={actionLoading === expense.expense_id}
                      className="px-3 py-1.5 bg-red-600 hover:bg-red-500 text-white text-xs rounded-lg font-medium transition-colors disabled:opacity-50"
                    >
                      Reject
                    </button>
                  </div>
                )}

                {/* TX link */}
                {expense.tx_hash && (
                  <a
                    href={expense.tempo_tx_url || `https://explore.tempo.xyz/tx/${expense.tx_hash}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-400 hover:text-blue-300"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <ExternalLink className="w-4 h-4" />
                  </a>
                )}
              </div>

              {/* Expanded details */}
              {selectedExpense?.expense_id === expense.expense_id && (
                <div className="mt-4 pt-4 border-t border-slate-700 space-y-3 animate-fadeIn">
                  {/* AI Reason */}
                  {expense.approval_reason && (
                    <div className="bg-slate-900/60 rounded-lg p-3">
                      <p className="text-xs text-slate-400 mb-1 flex items-center gap-1">
                        <Shield className="w-3 h-3" /> AgentFin's Decision
                      </p>
                      <p className="text-sm text-slate-200">{expense.approval_reason}</p>
                    </div>
                  )}

                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <span className="text-slate-400">AI Category: </span>
                      <span className="text-slate-200">{expense.ai_category || 'N/A'}</span>
                    </div>
                    <div>
                      <span className="text-slate-400">Anomaly Score: </span>
                      <span className="text-slate-200">{((expense.anomaly_score || 0) * 100).toFixed(1)}%</span>
                    </div>
                    <div>
                      <span className="text-slate-400">Approved By: </span>
                      <span className="text-slate-200">{expense.approved_by || 'Pending'}</span>
                    </div>
                    <div>
                      <span className="text-slate-400">Receipt: </span>
                      <span className="text-slate-200">{expense.receipt_attached ? '✅ Attached' : '❌ Missing'}</span>
                    </div>
                  </div>

                  {/* Memo */}
                  {expense.memo && (
                    <div className="bg-slate-900 rounded-lg p-3">
                      <p className="text-xs text-slate-400 mb-1">📝 On-Chain Memo</p>
                      <code className="text-xs text-blue-300 font-mono break-all">{expense.memo}</code>
                    </div>
                  )}

                  {/* Risk factors */}
                  {expense.risk_factors && expense.risk_factors !== '[]' && (
                    <div>
                      <span className="text-slate-400 text-sm">Risk Factors: </span>
                      <span className="text-orange-300 text-xs">{expense.risk_factors}</span>
                    </div>
                  )}

                  {/* Fee Sponsorship info */}
                  {expense.tx_hash && (
                    <div className="flex items-center gap-2 bg-green-900/10 border border-green-800/20 rounded-lg px-3 py-2">
                      <Zap className="w-3.5 h-3.5 text-green-400" />
                      <p className="text-xs text-green-300/80">
                        Transaction fees sponsored by AgentFin — employee paid $0 in gas fees
                      </p>
                    </div>
                  )}

                  {/* Raise Exception / Dispute Button */}
                  {(expense.status === 'rejected' || expense.status === 'flagged') && (
                    <div className="mt-2" onClick={(e) => e.stopPropagation()}>
                      {showDisputeForm === expense.expense_id ? (
                        <div className="bg-orange-900/15 border border-orange-800/30 rounded-lg p-3 space-y-2 animate-fadeIn">
                          <p className="text-xs text-orange-400 font-medium flex items-center gap-1">
                            <MessageSquare className="w-3 h-3" /> Raise Exception
                          </p>
                          <textarea
                            value={disputeText}
                            onChange={(e) => setDisputeText(e.target.value)}
                            placeholder="Explain why this expense should be reconsidered..."
                            className="w-full bg-slate-800 border border-orange-700/30 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:ring-1 focus:ring-orange-500 resize-none"
                            rows={2}
                          />
                          <div className="flex gap-2">
                            <button
                              onClick={() => handleDispute(expense.expense_id)}
                              disabled={actionLoading === expense.expense_id || !disputeText.trim()}
                              className="px-3 py-1.5 bg-orange-600 hover:bg-orange-500 text-white text-xs rounded-lg font-medium transition-colors disabled:opacity-50 flex items-center gap-1"
                            >
                              {actionLoading === expense.expense_id ? (
                                <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                              ) : (
                                <MessageSquare className="w-3 h-3" />
                              )}
                              Submit Exception
                            </button>
                            <button
                              onClick={() => { setShowDisputeForm(null); setDisputeText(''); }}
                              className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-slate-300 text-xs rounded-lg font-medium transition-colors"
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      ) : (
                        <button
                          onClick={() => setShowDisputeForm(expense.expense_id)}
                          className="flex items-center gap-2 px-3 py-2 bg-orange-900/20 hover:bg-orange-900/30 border border-orange-800/30 hover:border-orange-700/50 rounded-lg text-orange-400 text-xs font-medium transition-all w-full justify-center"
                        >
                          <MessageSquare className="w-3.5 h-3.5" />
                          Raise Exception — Contest This Decision
                        </button>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}

        {expenses.length === 0 && (
          <div className="text-center py-12 text-slate-500">
            <p>No expenses found</p>
          </div>
        )}
      </div>
    </div>
  );
}
