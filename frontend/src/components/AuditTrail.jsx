import { useState, useEffect } from 'react';
import { FileText, Bot, User, ExternalLink, Shield } from 'lucide-react';
import { getAuditTrail, getAuditStats } from '../api/client';

export default function AuditTrail() {
  const [logs, setLogs] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [logsRes, statsRes] = await Promise.all([
        getAuditTrail({ limit: 100 }),
        getAuditStats(),
      ]);
      setLogs(logsRes.data.logs);
      setStats(statsRes.data);
    } catch (err) {
      console.error('Failed to load audit data:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="animate-pulse space-y-3">
      {[...Array(5)].map((_, i) => (
        <div key={i} className="bg-slate-800 rounded-lg p-4 h-16" />
      ))}
    </div>;
  }

  return (
    <div>
      {/* Stats bar */}
      {stats && (
        <div className="grid grid-cols-4 gap-3 mb-6">
          <div className="bg-slate-800 rounded-lg border border-slate-700 px-4 py-3 text-center">
            <p className="text-2xl font-bold text-white">{stats.total_actions}</p>
            <p className="text-xs text-slate-400">Total Actions</p>
          </div>
          <div className="bg-slate-800 rounded-lg border border-slate-700 px-4 py-3 text-center">
            <p className="text-2xl font-bold text-blue-400">{stats.agent_actions}</p>
            <p className="text-xs text-slate-400">AgentFin Decisions</p>
          </div>
          <div className="bg-slate-800 rounded-lg border border-slate-700 px-4 py-3 text-center">
            <p className="text-2xl font-bold text-green-400">{stats.on_chain_records}</p>
            <p className="text-xs text-slate-400">On-Chain Records</p>
          </div>
          <div className="bg-slate-800 rounded-lg border border-slate-700 px-4 py-3 text-center">
            <p className="text-2xl font-bold text-purple-400">{stats.transparency_rate}%</p>
            <p className="text-xs text-slate-400">Transparency Rate</p>
          </div>
        </div>
      )}

      {/* Audit log timeline */}
      <div className="space-y-2">
        {logs.map((log) => (
          <div key={log.id} className="bg-slate-800 rounded-lg border border-slate-700 px-4 py-3 hover:border-slate-600 transition-all">
            <div className="flex items-start gap-3">
              {/* Actor icon */}
              <div className={`p-1.5 rounded-lg mt-0.5 ${
                log.actor === 'AgentFin'
                  ? 'bg-blue-500/10'
                  : 'bg-slate-700'
              }`}>
                {log.actor === 'AgentFin' ? (
                  <Bot className="w-4 h-4 text-blue-400" />
                ) : (
                  <User className="w-4 h-4 text-slate-400" />
                )}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-sm text-white">{log.actor}</span>
                  <span className="text-slate-500 text-xs">•</span>
                  <span className="text-sm text-slate-300">{log.action.replace(/_/g, ' ')}</span>
                  <span className="text-xs text-slate-500 ml-auto">
                    {log.timestamp ? new Date(log.timestamp).toLocaleString() : ''}
                  </span>
                </div>

                <div className="flex items-center gap-3 mt-1">
                  <span className="font-mono text-xs text-slate-400">{log.expense_id}</span>
                  {log.risk_score != null && (
                    <span className={`text-xs ${
                      log.risk_score < 0.3 ? 'text-green-400' :
                      log.risk_score < 0.7 ? 'text-yellow-400' : 'text-red-400'
                    }`}>
                      Risk: {(log.risk_score * 100).toFixed(1)}%
                    </span>
                  )}
                  {log.tx_hash && (
                    <a
                      href={log.tempo_tx_url || `https://explore.tempo.xyz/tx/${log.tx_hash}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300"
                    >
                      <ExternalLink className="w-3 h-3" />
                      <span className="font-mono">{log.tx_hash.substring(0, 12)}...</span>
                    </a>
                  )}
                </div>

                {/* Memo */}
                {log.memo && (
                  <div className="mt-2 bg-slate-900/60 rounded px-3 py-1.5">
                    <code className="text-[11px] text-blue-300/80 font-mono break-all">{log.memo}</code>
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}

        {logs.length === 0 && (
          <div className="text-center py-12 text-slate-500">
            <Shield className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>No audit records yet</p>
          </div>
        )}
      </div>
    </div>
  );
}

