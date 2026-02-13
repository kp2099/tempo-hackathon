import { Bot, Info, Sparkles, Zap, Shield, Brain } from 'lucide-react';
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
          <p className="font-medium mb-2">How AgentFin works:</p>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-2 text-xs">
            <div className="flex items-center gap-1.5 bg-blue-500/10 rounded-lg px-2 py-1.5">
              <Brain className="w-3.5 h-3.5 text-blue-400 flex-shrink-0" />
              <span>XGBoost Risk Scoring</span>
            </div>
            <div className="flex items-center gap-1.5 bg-purple-500/10 rounded-lg px-2 py-1.5">
              <Shield className="w-3.5 h-3.5 text-purple-400 flex-shrink-0" />
              <span>Anomaly Detection</span>
            </div>
            <div className="flex items-center gap-1.5 bg-green-500/10 rounded-lg px-2 py-1.5">
              <Shield className="w-3.5 h-3.5 text-green-400 flex-shrink-0" />
              <span>Policy Compliance</span>
            </div>
            <div className="flex items-center gap-1.5 bg-yellow-500/10 rounded-lg px-2 py-1.5">
              <Sparkles className="w-3.5 h-3.5 text-yellow-400 flex-shrink-0" />
              <span>AI Decision</span>
            </div>
            <div className="flex items-center gap-1.5 bg-green-500/10 rounded-lg px-2 py-1.5">
              <Zap className="w-3.5 h-3.5 text-green-400 flex-shrink-0" />
              <span>Tempo Payment</span>
            </div>
          </div>
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
            <p className="text-green-400/60 text-xs mt-2">→ Should auto-approve + pay on Tempo</p>
          </div>

          <div className="bg-yellow-500/5 border border-yellow-500/20 rounded-lg p-4">
            <h4 className="text-yellow-400 font-medium text-sm mb-2">⏳ Borderline Expense</h4>
            <ul className="text-xs text-slate-400 space-y-1">
              <li>Amount: $450.00</li>
              <li>Category: Client Entertainment</li>
              <li>Merchant: Restaurant</li>
              <li>Receipt: No</li>
            </ul>
            <p className="text-yellow-400/60 text-xs mt-2">→ Should need manager review</p>
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

        {/* NL Examples */}
        <div className="mt-6 pt-4 border-t border-slate-700">
          <h4 className="text-sm font-medium text-purple-400 flex items-center gap-2 mb-3">
            <Sparkles className="w-4 h-4" />
            Try AI Input Mode — speak naturally:
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs text-slate-400">
            <div className="bg-purple-500/5 rounded-lg px-3 py-2 border border-purple-800/20">
              "Spent $120 at Marriott for the Chicago conference"
            </div>
            <div className="bg-purple-500/5 rounded-lg px-3 py-2 border border-purple-800/20">
              "$45 lunch at Chipotle with clients"
            </div>
            <div className="bg-purple-500/5 rounded-lg px-3 py-2 border border-purple-800/20">
              "Flight to NYC, Delta Airlines, $850"
            </div>
            <div className="bg-purple-500/5 rounded-lg px-3 py-2 border border-purple-800/20">
              "Uber ride to airport $42"
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
