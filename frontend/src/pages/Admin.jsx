import { useState, useEffect } from 'react';
import { Shield, Users, Wallet, Zap, CheckCircle, ExternalLink, Loader2, History } from 'lucide-react';
import { getEmployees, getSpendingSummary, batchApprove } from '../api/client';
import ExpenseList from '../components/ExpenseList';

export default function Admin() {
  const [employees, setEmployees] = useState([]);
  const [selectedEmployee, setSelectedEmployee] = useState(null);
  const [spending, setSpending] = useState(null);
  const [batchLoading, setBatchLoading] = useState(false);
  const [batchResult, setBatchResult] = useState(null);

  useEffect(() => {
    loadEmployees();
  }, []);

  const loadEmployees = async () => {
    try {
      const res = await getEmployees();
      setEmployees(res.data);
    } catch (err) {
      console.error('Failed to load employees:', err);
    }
  };

  const loadSpending = async (employeeId) => {
    try {
      const res = await getSpendingSummary(employeeId);
      setSpending(res.data);
    } catch (err) {
      console.error('Failed to load spending:', err);
    }
  };

  const handleSelectEmployee = (emp) => {
    setSelectedEmployee(emp);
    loadSpending(emp.employee_id);
  };

  const handleBatchApprove = async () => {
    setBatchLoading(true);
    setBatchResult(null);
    try {
      const res = await batchApprove();
      setBatchResult(res.data);
    } catch (err) {
      setBatchResult({
        error: err.response?.data?.detail || 'Batch approval failed',
      });
    } finally {
      setBatchLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <Shield className="w-6 h-6 text-purple-400" />
          Admin Panel
        </h1>
        <p className="text-slate-400 mt-1">Manage employees, review flagged expenses, and oversee AgentFin decisions</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Employees list */}
        <div className="bg-slate-800 rounded-xl border border-slate-700 p-5">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2 mb-4">
            <Users className="w-5 h-5 text-blue-400" />
            Employees
          </h2>
          <div className="space-y-2">
            {employees.map((emp) => (
              <button
                key={emp.employee_id}
                onClick={() => handleSelectEmployee(emp)}
                className={`w-full text-left px-4 py-3 rounded-lg transition-all ${
                  selectedEmployee?.employee_id === emp.employee_id
                    ? 'bg-blue-600/20 border border-blue-500/30'
                    : 'bg-slate-700/50 hover:bg-slate-700 border border-transparent'
                }`}
              >
                <p className="text-white font-medium text-sm">{emp.name}</p>
                <p className="text-slate-400 text-xs">{emp.department} · {emp.role} · {emp.employee_id}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Employee details & spending */}
        <div className="lg:col-span-2 space-y-6">
          {selectedEmployee && spending ? (
            <>
              {/* Employee info card */}
              <div className="bg-slate-800 rounded-xl border border-slate-700 p-5">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="text-lg font-bold text-white">{spending.name}</h3>
                    <p className="text-slate-400 text-sm">{spending.department} · {selectedEmployee.employee_id}</p>
                  </div>
                  <div className="flex items-center gap-2 bg-slate-700 px-3 py-1.5 rounded-lg">
                    <Wallet className="w-4 h-4 text-blue-400" />
                    <span className="text-xs font-mono text-slate-300">
                      {selectedEmployee.tempo_wallet?.substring(0, 10)}...
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-5">
                  <div className="bg-slate-700/50 rounded-lg p-3 text-center">
                    <p className="text-xl font-bold text-white">{spending.total_expenses}</p>
                    <p className="text-xs text-slate-400">Total Expenses</p>
                  </div>
                  <div className="bg-slate-700/50 rounded-lg p-3 text-center">
                    <p className="text-xl font-bold text-blue-400">${spending.total_amount.toLocaleString()}</p>
                    <p className="text-xs text-slate-400">Total Spent</p>
                  </div>
                  <div className="bg-slate-700/50 rounded-lg p-3 text-center">
                    <p className={`text-xl font-bold ${
                      spending.avg_risk_score < 0.3 ? 'text-green-400' :
                      spending.avg_risk_score < 0.7 ? 'text-yellow-400' : 'text-red-400'
                    }`}>
                      {(spending.avg_risk_score * 100).toFixed(1)}%
                    </p>
                    <p className="text-xs text-slate-400">Avg Risk</p>
                  </div>
                  <div className="bg-slate-700/50 rounded-lg p-3 text-center">
                    <p className="text-xl font-bold text-green-400">
                      ${spending.monthly_remaining?.toLocaleString()}
                    </p>
                    <p className="text-xs text-slate-400">Monthly Remaining</p>
                  </div>
                </div>

                {/* Monthly spending bar */}
                <div className="mt-4">
                  <div className="flex justify-between text-xs text-slate-400 mb-1">
                    <span>Monthly Usage</span>
                    <span>${spending.monthly_spent?.toLocaleString()} / ${spending.monthly_limit?.toLocaleString()}</span>
                  </div>
                  <div className="w-full bg-slate-700 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full transition-all ${
                        (spending.monthly_spent / spending.monthly_limit) > 0.8
                          ? 'bg-red-500'
                          : (spending.monthly_spent / spending.monthly_limit) > 0.5
                          ? 'bg-yellow-500'
                          : 'bg-green-500'
                      }`}
                      style={{ width: `${Math.min((spending.monthly_spent / spending.monthly_limit) * 100, 100)}%` }}
                    />
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="bg-slate-800 rounded-xl border border-slate-700 p-12 text-center text-slate-500">
              <Users className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>Select an employee to view details</p>
            </div>
          )}

          {/* Expenses needing review */}
          <div className="bg-slate-800 rounded-xl border border-slate-700 p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white">⏳ Expenses Pending Review</h3>

              {/* Batch Approve Button */}
              <button
                onClick={handleBatchApprove}
                disabled={batchLoading}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all
                  ${batchLoading
                    ? 'bg-slate-600 text-slate-400 cursor-wait'
                    : 'bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 text-white shadow-lg shadow-green-500/20 hover:shadow-green-500/40'
                  }`}
              >
                {batchLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    <Zap className="w-4 h-4" />
                    Batch Approve All
                  </>
                )}
              </button>
            </div>

            {/* Batch Result */}
            {batchResult && !batchResult.error && (
              <div className="mb-4 bg-green-900/20 border border-green-800/30 rounded-xl p-4 animate-slideUp">
                <div className="flex items-center gap-2 mb-3">
                  <CheckCircle className="w-5 h-5 text-green-400" />
                  <span className="text-green-400 font-semibold">
                    Batch Approved: {batchResult.approved} expenses
                  </span>
                  <span className="text-slate-400 text-sm">
                    · ${batchResult.total_amount?.toLocaleString()} total
                  </span>
                </div>

                {/* Parallel execution badge */}
                {batchResult.parallel_execution && (
                  <div className="flex items-center gap-2 mb-3 text-xs">
                    <span className="flex items-center gap-1 bg-blue-500/10 text-blue-400 px-2 py-1 rounded-full">
                      <Zap className="w-3 h-3" /> Parallel Execution
                    </span>
                    <span className="flex items-center gap-1 bg-green-500/10 text-green-400 px-2 py-1 rounded-full">
                      <Shield className="w-3 h-3" /> Gas Fees Sponsored
                    </span>
                  </div>
                )}

                {/* Transaction list */}
                {batchResult.transactions?.length > 0 && (
                  <div className="space-y-2">
                    {batchResult.transactions.map((tx, i) => (
                      <div key={i} className="flex items-center justify-between bg-slate-800/60 rounded-lg px-3 py-2 text-xs">
                        <span className="font-mono text-slate-300">{tx.expense_id}</span>
                        <span className="text-green-400">${tx.amount?.toFixed(2)}</span>
                        <a
                          href={tx.tempo_tx_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1 text-blue-400 hover:text-blue-300"
                        >
                          <ExternalLink className="w-3 h-3" />
                          <span className="font-mono">{tx.tx_hash?.substring(0, 14)}...</span>
                        </a>
                      </div>
                    ))}
                  </div>
                )}

                {batchResult.approved === 0 && (
                  <p className="text-slate-400 text-sm">{batchResult.message}</p>
                )}
              </div>
            )}

            {batchResult?.error && (
              <div className="mb-4 bg-red-500/10 border border-red-500/30 rounded-lg p-3">
                <p className="text-red-400 text-sm">❌ {batchResult.error}</p>
              </div>
            )}

            <ExpenseList filterStatus="manager_review,disputed" showActions={true} />
          </div>

          {/* Past Activity for selected employee */}
          {selectedEmployee && (
            <div className="bg-slate-800 rounded-xl border border-slate-700 p-5">
              <h3 className="text-lg font-semibold text-white flex items-center gap-2 mb-4">
                <History className="w-5 h-5 text-blue-400" />
                Past Activity — {selectedEmployee.name}
              </h3>
              <p className="text-slate-400 text-xs mb-4">Last 10 expenses submitted by this employee</p>
              <ExpenseList
                employeeId={selectedEmployee.employee_id}
                limit={10}
                showActions={false}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
