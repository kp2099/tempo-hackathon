import { useState } from 'react';
import { Bot, Zap, Shield, Brain, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import Dashboard from '../components/Dashboard';
import ExpenseList from '../components/ExpenseList';

export default function Home() {
  const [activeTab, setActiveTab] = useState('all');

  const tabs = [
    { key: 'all', label: 'All Expenses', filter: null },
    { key: 'approved', label: '✅ Auto-Approved', filter: 'paid' },
    { key: 'review', label: '⏳ Needs Review', filter: 'manager_review' },
    { key: 'flagged', label: '🚨 Flagged', filter: 'flagged' },
  ];

  return (
    <div className="space-y-8">
      {/* Hero */}
      <div className="bg-gradient-to-r from-blue-900/50 to-purple-900/50 rounded-2xl border border-blue-800/30 p-8">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3 mb-3">
              <div className="bg-gradient-to-br from-blue-500 to-purple-600 p-3 rounded-xl">
                <Bot className="w-8 h-8 text-white" />
              </div>
              <div>
                <h1 className="text-3xl font-bold text-white">TempoExpenseAI</h1>
                <p className="text-blue-300 text-sm">Autonomous Expense Approval Agent</p>
              </div>
            </div>
            <p className="text-slate-300 max-w-2xl mt-2">
              AI-powered expense processing that detects fraud, makes autonomous approval decisions,
              and instantly pays employees via Tempo's programmable stablecoin infrastructure.
            </p>

            <div className="flex items-center gap-6 mt-6">
              <div className="flex items-center gap-2 text-sm text-slate-300">
                <Brain className="w-4 h-4 text-blue-400" />
                XGBoost Risk Scoring
              </div>
              <div className="flex items-center gap-2 text-sm text-slate-300">
                <Zap className="w-4 h-4 text-yellow-400" />
                Instant Settlement
              </div>
              <div className="flex items-center gap-2 text-sm text-slate-300">
                <Shield className="w-4 h-4 text-green-400" />
                On-Chain Audit Trail
              </div>
            </div>

            <Link
              to="/submit"
              className="inline-flex items-center gap-2 mt-6 bg-blue-600 hover:bg-blue-500 text-white font-medium px-6 py-2.5 rounded-lg transition-colors"
            >
              Submit an Expense
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>

          {/* Agent status card */}
          <div className="bg-slate-800/50 backdrop-blur rounded-xl border border-slate-700 p-5 min-w-[200px]">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-3 h-3 bg-green-400 rounded-full pulse-dot" />
              <span className="text-green-400 text-sm font-medium">Agent Online</span>
            </div>
            <div className="space-y-3 text-sm">
              <div>
                <p className="text-slate-400">Agent Name</p>
                <p className="text-white font-medium">AgentFin v1.0</p>
              </div>
              <div>
                <p className="text-slate-400">Decision Model</p>
                <p className="text-white font-medium">XGBoost + IsolationForest</p>
              </div>
              <div>
                <p className="text-slate-400">Payment Rail</p>
                <p className="text-white font-medium">Tempo L1 Blockchain</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Dashboard Stats */}
      <Dashboard />

      {/* Expense List */}
      <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6">
        <div className="flex items-center gap-1 mb-6 border-b border-slate-700 pb-3 overflow-x-auto">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-all ${
                activeTab === tab.key
                  ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30'
                  : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <ExpenseList
          filterStatus={tabs.find(t => t.key === activeTab)?.filter}
          showActions={false}
        />
      </div>
    </div>
  );
}

