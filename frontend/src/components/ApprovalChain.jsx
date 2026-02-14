import { useState, useEffect } from 'react';
import { CheckCircle, Clock, XCircle, ArrowUpCircle, SkipForward, ChevronRight, User, Shield } from 'lucide-react';
import { getApprovalSteps, approveStep, rejectStep, escalateStep } from '../api/client';

const stepStatusConfig = {
  pending: { icon: Clock, color: 'text-yellow-400', bg: 'bg-yellow-500/10', ring: 'ring-yellow-500/30', label: 'Pending' },
  waiting: { icon: Clock, color: 'text-slate-500', bg: 'bg-slate-500/10', ring: 'ring-slate-500/20', label: 'Waiting' },
  approved: { icon: CheckCircle, color: 'text-green-400', bg: 'bg-green-500/10', ring: 'ring-green-500/30', label: 'Approved' },
  rejected: { icon: XCircle, color: 'text-red-400', bg: 'bg-red-500/10', ring: 'ring-red-500/30', label: 'Rejected' },
  escalated: { icon: ArrowUpCircle, color: 'text-purple-400', bg: 'bg-purple-500/10', ring: 'ring-purple-500/30', label: 'Escalated' },
  skipped: { icon: SkipForward, color: 'text-slate-500', bg: 'bg-slate-500/10', ring: 'ring-slate-500/20', label: 'Skipped' },
};

const roleLabels = {
  direct_manager: 'Direct Manager',
  finance: 'Finance',
  department_head: 'Dept. Head',
  vp: 'VP',
  cfo: 'CFO',
  escalated_manager: 'Escalated Manager',
};

export default function ApprovalChain({ expenseId, currentApproverId, isAdmin = false, onAction }) {
  const [steps, setSteps] = useState([]);
  const [expenseStatus, setExpenseStatus] = useState('');
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(null);
  const [comments, setComments] = useState('');

  useEffect(() => {
    if (expenseId) loadSteps();
  }, [expenseId]);

  const loadSteps = async () => {
    try {
      const res = await getApprovalSteps(expenseId);
      setSteps(res.data.steps || []);
      setExpenseStatus(res.data.expense_status);
    } catch (err) {
      console.error('Failed to load steps:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (step) => {
    setActionLoading(`approve-${step.step_order}`);
    try {
      await approveStep(expenseId, step.approver_id, comments || null);
      setComments('');
      loadSteps();
      onAction?.();
    } catch (err) {
      alert(err.response?.data?.detail || 'Approval failed');
    } finally {
      setActionLoading(null);
    }
  };

  const handleReject = async (step) => {
    setActionLoading(`reject-${step.step_order}`);
    try {
      await rejectStep(expenseId, step.approver_id, comments || 'Rejected');
      setComments('');
      loadSteps();
      onAction?.();
    } catch (err) {
      alert(err.response?.data?.detail || 'Rejection failed');
    } finally {
      setActionLoading(null);
    }
  };

  const handleEscalate = async (step) => {
    setActionLoading(`escalate-${step.step_order}`);
    try {
      await escalateStep(expenseId, step.approver_id, comments || 'Escalated to higher authority');
      setComments('');
      loadSteps();
      onAction?.();
    } catch (err) {
      alert(err.response?.data?.detail || 'Escalation failed');
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) {
    return <div className="animate-pulse h-12 bg-slate-700 rounded-lg" />;
  }

  if (steps.length === 0) return null;

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 mb-2">
        <Shield className="w-4 h-4 text-purple-400" />
        <span className="text-xs font-semibold text-purple-400 uppercase tracking-wide">
          Approval Chain ({steps.length} step{steps.length !== 1 ? 's' : ''})
        </span>
      </div>

      {/* Visual pipeline */}
      <div className="flex items-center gap-1 flex-wrap">
        {steps.map((step, idx) => {
          const sc = stepStatusConfig[step.status] || stepStatusConfig.waiting;
          const Icon = sc.icon;
          return (
            <div key={step.step_order} className="flex items-center gap-1">
              <div className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg ring-1 ${sc.bg} ${sc.ring}`}>
                <Icon className={`w-3.5 h-3.5 ${sc.color}`} />
                <div className="text-xs">
                  <span className={`font-medium ${sc.color}`}>
                    {step.approver_name || roleLabels[step.approver_role] || step.approver_role}
                  </span>
                  <span className="text-slate-500 ml-1">
                    ({roleLabels[step.approver_role] || step.approver_role})
                  </span>
                </div>
              </div>
              {idx < steps.length - 1 && (
                <ChevronRight className="w-3.5 h-3.5 text-slate-600 flex-shrink-0" />
              )}
            </div>
          );
        })}
      </div>

      {/* Actions for the current approver or admin */}
      {(() => {
        const pendingStep = isAdmin
          ? steps.find(s => s.status === 'pending')
          : currentApproverId
            ? steps.find(s => s.approver_id === currentApproverId && s.status === 'pending')
            : null;
        if (!pendingStep) return null;
        return (
          <div className="bg-slate-900/50 border border-slate-700 rounded-lg p-3 space-y-2 mt-2">
            <p className="text-xs text-slate-400 flex items-center gap-1">
              <User className="w-3 h-3" />
              {isAdmin
                ? `Action as ${pendingStep.approver_name || pendingStep.approver_role} (Step ${pendingStep.step_order})`
                : 'Your action required'}
            </p>
            <input
              type="text"
              value={comments}
              onChange={(e) => setComments(e.target.value)}
              placeholder="Optional comments..."
              className="w-full bg-slate-800 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white placeholder-slate-500 focus:ring-1 focus:ring-blue-500"
            />
            <div className="flex gap-2">
              <button
                onClick={() => handleApprove(pendingStep)}
                disabled={!!actionLoading}
                className="px-3 py-1.5 bg-green-600 hover:bg-green-500 text-white text-xs rounded font-medium transition-colors disabled:opacity-50 flex items-center gap-1"
              >
                {actionLoading?.startsWith('approve') ? (
                  <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <CheckCircle className="w-3 h-3" />
                )}
                Approve
              </button>
              <button
                onClick={() => handleReject(pendingStep)}
                disabled={!!actionLoading}
                className="px-3 py-1.5 bg-red-600 hover:bg-red-500 text-white text-xs rounded font-medium transition-colors disabled:opacity-50 flex items-center gap-1"
              >
                <XCircle className="w-3 h-3" />
                Reject
              </button>
              <button
                onClick={() => handleEscalate(pendingStep)}
                disabled={!!actionLoading}
                className="px-3 py-1.5 bg-purple-600 hover:bg-purple-500 text-white text-xs rounded font-medium transition-colors disabled:opacity-50 flex items-center gap-1"
              >
                <ArrowUpCircle className="w-3 h-3" />
                Escalate
              </button>
            </div>
          </div>
        );
      })()}

      {/* Step details (timeline) */}
      <div className="space-y-1">
        {steps.filter(s => s.acted_at).map(step => {
          const sc = stepStatusConfig[step.status] || stepStatusConfig.waiting;
          return (
            <div key={`detail-${step.step_order}`} className="flex items-center gap-2 text-xs text-slate-400">
              <span className={sc.color}>●</span>
              <span className="font-medium text-slate-300">{step.approver_name || step.approver_role}</span>
              <span>{sc.label}</span>
              {step.comments && <span className="text-slate-500">— "{step.comments}"</span>}
              {step.acted_at && (
                <span className="text-slate-600">{new Date(step.acted_at).toLocaleString()}</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
