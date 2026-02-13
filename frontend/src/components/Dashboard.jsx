import { useState, useEffect } from 'react';
import {
  DollarSign, TrendingUp, CheckCircle, AlertTriangle,
  XCircle, Clock, Zap, Shield
} from 'lucide-react';
import { getExpenseStats } from '../api/client';

function StatCard({ icon: Icon, label, value, subtext, color, glowClass }) {
  return (
    <div className={`bg-slate-800 rounded-xl border border-slate-700 p-5 ${glowClass || ''} hover:border-slate-600 transition-all`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-slate-400 text-sm">{label}</p>
          <p className={`text-2xl font-bold mt-1 ${color || 'text-white'}`}>{value}</p>
          {subtext && <p className="text-slate-500 text-xs mt-1">{subtext}</p>}
        </div>
        <div className={`p-2 rounded-lg ${color ? 'bg-opacity-10' : 'bg-slate-700'}`}
          style={{ backgroundColor: `${color === 'text-green-400' ? 'rgba(16,185,129,0.1)' : color === 'text-yellow-400' ? 'rgba(245,158,11,0.1)' : color === 'text-red-400' ? 'rgba(239,68,68,0.1)' : 'rgba(59,130,246,0.1)'}` }}>
          <Icon className={`w-5 h-5 ${color || 'text-blue-400'}`} />
        </div>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      const res = await getExpenseStats();
      setStats(res.data);
    } catch (err) {
      console.error('Failed to load stats:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(8)].map((_, i) => (
          <div key={i} className="bg-slate-800 rounded-xl border border-slate-700 p-5 animate-pulse">
            <div className="h-4 bg-slate-700 rounded w-24 mb-3" />
            <div className="h-8 bg-slate-700 rounded w-16" />
          </div>
        ))}
      </div>
    );
  }

  if (!stats) return null;

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-xl font-bold text-white flex items-center gap-2">
          <Zap className="w-5 h-5 text-yellow-400" />
          Real-Time Agent Dashboard
        </h2>
        <p className="text-slate-400 text-sm mt-1">AgentFin's autonomous expense processing overview</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={DollarSign}
          label="Total Processed"
          value={`$${stats.total_amount.toLocaleString()}`}
          subtext={`${stats.total_expenses} expenses`}
          color="text-blue-400"
        />
        <StatCard
          icon={CheckCircle}
          label="Auto-Approved"
          value={stats.auto_approved}
          subtext="By AgentFin"
          color="text-green-400"
          glowClass="glow-green"
        />
        <StatCard
          icon={Clock}
          label="Pending Review"
          value={stats.manager_review}
          subtext="Needs manager approval"
          color="text-yellow-400"
          glowClass="glow-yellow"
        />
        <StatCard
          icon={XCircle}
          label="Flagged / Rejected"
          value={stats.flagged + stats.rejected}
          subtext="Anomaly or policy violation"
          color="text-red-400"
          glowClass="glow-red"
        />
        <StatCard
          icon={Zap}
          label="Instant Payments"
          value={stats.paid}
          subtext="Via Tempo stablecoin"
          color="text-green-400"
        />
        <StatCard
          icon={Shield}
          label="Avg Risk Score"
          value={(stats.avg_risk_score * 100).toFixed(1) + '%'}
          subtext="Lower is safer"
          color="text-blue-400"
        />
        <StatCard
          icon={TrendingUp}
          label="Time Saved"
          value={`${stats.total_saved_time_hours}h`}
          subtext="vs manual processing"
          color="text-green-400"
        />
        <StatCard
          icon={AlertTriangle}
          label="Fraud Prevention"
          value={stats.flagged}
          subtext="Anomalies caught by AI"
          color="text-yellow-400"
        />
      </div>
    </div>
  );
}

