import { Bot, Info } from 'lucide-react';
import ExpenseForm from '../components/ExpenseForm';

export default function Submit() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <Bot className="w-6 h-6 text-blue-400" />
          Submit Expense to AgentFin
        </h1>
        <p className="text-slate-400 mt-1">
          Submit an expense and watch the AI agent evaluate it in real-time
        </p>
      </div>

      {/* Info banner */}
      <div className="bg-blue-900/20 border border-blue-800/30 rounded-xl p-4 flex items-start gap-3">
        <Info className="w-5 h-5 text-blue-400 mt-0.5 flex-shrink-0" />
        <div className="text-sm text-blue-200">
          <p className="font-medium mb-1">How it works:</p>
          <ol className="list-decimal list-inside space-y-1 text-blue-300/80">
            <li>You submit an expense with details below</li>
            <li>AgentFin runs <strong>XGBoost risk scoring</strong> and <strong>anomaly detection</strong></li>
            <li>Policy rules are checked (spending limits, receipt requirements)</li>
            <li>AI makes an autonomous decision: <span className="text-green-400">Auto-Approve</span>, <span className="text-yellow-400">Manager Review</span>, or <span className="text-red-400">Reject</span></li>
            <li>If approved, instant payment via <strong>Tempo stablecoin rails</strong> with on-chain memo</li>
          </ol>
        </div>
      </div>

      <ExpenseForm />

      {/* Demo scenarios */}
      <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6">
        <h3 className="text-lg font-semibold text-white mb-4">🎯 Try These Demo Scenarios</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-green-500/5 border border-green-500/20 rounded-lg p-4">
            <h4 className="text-green-400 font-medium text-sm mb-2">✅ Normal Expense</h4>
            <ul className="text-xs text-slate-400 space-y-1">
              <li>Amount: $45.00</li>
              <li>Category: Meals</li>
              <li>Merchant: Chipotle</li>
              <li>Receipt: Yes</li>
            </ul>
            <p className="text-green-400/60 text-xs mt-2">→ Should auto-approve</p>
          </div>

          <div className="bg-yellow-500/5 border border-yellow-500/20 rounded-lg p-4">
            <h4 className="text-yellow-400 font-medium text-sm mb-2">⏳ Borderline Expense</h4>
            <ul className="text-xs text-slate-400 space-y-1">
              <li>Amount: $450.00</li>
              <li>Category: Client Entertainment</li>
              <li>Merchant: Restaurant</li>
              <li>Receipt: No</li>
            </ul>
            <p className="text-yellow-400/60 text-xs mt-2">→ Should need review</p>
          </div>

          <div className="bg-red-500/5 border border-red-500/20 rounded-lg p-4">
            <h4 className="text-red-400 font-medium text-sm mb-2">🚨 Suspicious Expense</h4>
            <ul className="text-xs text-slate-400 space-y-1">
              <li>Amount: $3,000.00</li>
              <li>Category: Office Supplies</li>
              <li>Merchant: Unknown</li>
              <li>Receipt: No</li>
            </ul>
            <p className="text-red-400/60 text-xs mt-2">→ Should get flagged</p>
          </div>
        </div>
      </div>
    </div>
  );
}

