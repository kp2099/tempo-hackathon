import { useState, useEffect } from 'react';
import { Settings, Plus, Trash2, ToggleLeft, ToggleRight, ChevronRight, ArrowDown, Save, X, Pencil } from 'lucide-react';
import { getApprovalRules, createApprovalRule, updateApprovalRule, deleteApprovalRule, toggleApprovalRule } from '../api/client';

const CATEGORIES = [
  { value: '', label: 'Any Category' },
  { value: 'meals', label: 'Meals' },
  { value: 'travel', label: 'Travel' },
  { value: 'accommodation', label: 'Accommodation' },
  { value: 'office_supplies', label: 'Office Supplies' },
  { value: 'software', label: 'Software' },
  { value: 'equipment', label: 'Equipment' },
  { value: 'training', label: 'Training' },
  { value: 'client_entertainment', label: 'Client Entertainment' },
  { value: 'transportation', label: 'Transportation' },
  { value: 'miscellaneous', label: 'Miscellaneous' },
];

const DEPARTMENTS = [
  { value: '', label: 'Any Department' },
  { value: 'sales', label: 'Sales' },
  { value: 'engineering', label: 'Engineering' },
  { value: 'marketing', label: 'Marketing' },
  { value: 'finance', label: 'Finance' },
  { value: 'executive', label: 'Executive' },
];

const APPROVER_ROLES = [
  { value: 'direct_manager', label: 'Direct Manager' },
  { value: 'finance', label: 'Finance' },
  { value: 'department_head', label: 'Department Head' },
  { value: 'vp', label: 'VP' },
  { value: 'cfo', label: 'CFO' },
];

const emptyRule = {
  name: '',
  description: '',
  category: '',
  department: '',
  amount_min: '',
  amount_max: '',
  required_approvers: ['direct_manager'],
  approval_type: 'sequential',
  priority: 100,
};

export default function ApprovalRulesManager() {
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingRuleId, setEditingRuleId] = useState(null); // null = creating, number = editing
  const [form, setForm] = useState({ ...emptyRule });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadRules();
  }, []);

  const loadRules = async () => {
    try {
      const res = await getApprovalRules(false);
      setRules(res.data.rules || []);
    } catch (err) {
      console.error('Failed to load rules:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!form.name.trim() || form.required_approvers.length === 0) {
      alert('Rule name and at least one approver are required');
      return;
    }
    setSaving(true);
    const payload = {
      ...form,
      category: form.category || null,
      department: form.department || null,
      amount_min: form.amount_min ? parseFloat(form.amount_min) : null,
      amount_max: form.amount_max ? parseFloat(form.amount_max) : null,
    };
    try {
      if (editingRuleId) {
        await updateApprovalRule(editingRuleId, payload);
      } else {
        await createApprovalRule(payload);
      }
      setShowForm(false);
      setEditingRuleId(null);
      setForm({ ...emptyRule });
      loadRules();
    } catch (err) {
      alert(err.response?.data?.detail || `Failed to ${editingRuleId ? 'update' : 'create'} rule`);
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = (rule) => {
    setEditingRuleId(rule.id);
    setForm({
      name: rule.name,
      description: rule.description || '',
      category: rule.category || '',
      department: rule.department || '',
      amount_min: rule.amount_min != null ? String(rule.amount_min) : '',
      amount_max: rule.amount_max != null ? String(rule.amount_max) : '',
      required_approvers: rule.required_approvers || ['direct_manager'],
      approval_type: rule.approval_type || 'sequential',
      priority: rule.priority || 100,
    });
    setShowForm(true);
  };

  const handleCancelForm = () => {
    setShowForm(false);
    setEditingRuleId(null);
    setForm({ ...emptyRule });
  };

  const handleDelete = async (id) => {
    if (!confirm('Delete this rule?')) return;
    try {
      await deleteApprovalRule(id);
      loadRules();
    } catch (err) {
      alert('Failed to delete rule');
    }
  };

  const handleToggle = async (id) => {
    try {
      await toggleApprovalRule(id);
      loadRules();
    } catch (err) {
      alert('Failed to toggle rule');
    }
  };

  const addApprover = () => {
    setForm({ ...form, required_approvers: [...form.required_approvers, 'finance'] });
  };

  const removeApprover = (idx) => {
    setForm({
      ...form,
      required_approvers: form.required_approvers.filter((_, i) => i !== idx),
    });
  };

  const updateApproverRole = (idx, value) => {
    const updated = [...form.required_approvers];
    updated[idx] = value;
    setForm({ ...form, required_approvers: updated });
  };

  if (loading) {
    return (
      <div className="space-y-3">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-16 bg-slate-700 rounded-lg animate-pulse" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Settings className="w-5 h-5 text-purple-400" />
          <h3 className="text-sm font-semibold text-white">Approval Routing Rules</h3>
          <span className="text-xs text-slate-500">({rules.length} rules)</span>
        </div>
        <button
          onClick={() => {
            if (showForm) {
              handleCancelForm();
            } else {
              setEditingRuleId(null);
              setForm({ ...emptyRule });
              setShowForm(true);
            }
          }}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-purple-600 hover:bg-purple-500 text-white text-xs rounded-lg font-medium transition-colors"
        >
          {showForm ? <X className="w-3 h-3" /> : <Plus className="w-3 h-3" />}
          {showForm ? 'Cancel' : 'Add Rule'}
        </button>
      </div>

      {/* Create Form */}
      {showForm && (
        <div className="bg-slate-900/60 border border-purple-500/20 rounded-xl p-4 space-y-3 animate-fadeIn">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-semibold text-purple-400 uppercase tracking-wide">
              {editingRuleId ? '✏️ Edit Rule' : '➕ New Rule'}
            </span>
          </div>
          <input
            type="text"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="Rule name (e.g. Travel — Manager + Finance)"
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:ring-1 focus:ring-purple-500"
          />
          <input
            type="text"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            placeholder="Description (optional)"
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:ring-1 focus:ring-purple-500"
          />

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Category</label>
              <select
                value={form.category}
                onChange={(e) => setForm({ ...form, category: e.target.value })}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:ring-1 focus:ring-purple-500"
              >
                {CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Department</label>
              <select
                value={form.department}
                onChange={(e) => setForm({ ...form, department: e.target.value })}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:ring-1 focus:ring-purple-500"
              >
                {DEPARTMENTS.map(d => <option key={d.value} value={d.value}>{d.label}</option>)}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Min Amount ($)</label>
              <input
                type="number"
                value={form.amount_min}
                onChange={(e) => setForm({ ...form, amount_min: e.target.value })}
                placeholder="Any"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:ring-1 focus:ring-purple-500"
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Max Amount ($)</label>
              <input
                type="number"
                value={form.amount_max}
                onChange={(e) => setForm({ ...form, amount_max: e.target.value })}
                placeholder="No limit"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:ring-1 focus:ring-purple-500"
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Priority</label>
              <input
                type="number"
                value={form.priority}
                onChange={(e) => setForm({ ...form, priority: parseInt(e.target.value) || 100 })}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:ring-1 focus:ring-purple-500"
              />
            </div>
          </div>

          {/* Approver chain builder */}
          <div>
            <label className="text-xs text-slate-400 mb-2 block">Approval Chain (sequential)</label>
            <div className="flex items-center gap-1 flex-wrap">
              {form.required_approvers.map((role, idx) => (
                <div key={idx} className="flex items-center gap-1">
                  <div className="flex items-center gap-1 bg-slate-800 border border-slate-700 rounded-lg overflow-hidden">
                    <select
                      value={role}
                      onChange={(e) => updateApproverRole(idx, e.target.value)}
                      className="bg-transparent text-sm text-white px-2 py-1.5 focus:ring-0 border-0"
                    >
                      {APPROVER_ROLES.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
                    </select>
                    {form.required_approvers.length > 1 && (
                      <button
                        onClick={() => removeApprover(idx)}
                        className="px-1.5 text-red-400 hover:text-red-300"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    )}
                  </div>
                  {idx < form.required_approvers.length - 1 && (
                    <ChevronRight className="w-3 h-3 text-slate-600" />
                  )}
                </div>
              ))}
              <button
                onClick={addApprover}
                className="px-2 py-1.5 bg-slate-800 border border-dashed border-slate-600 rounded-lg text-slate-400 hover:text-white hover:border-slate-500 text-xs transition-colors"
              >
                + Add
              </button>
            </div>
          </div>

          <button
            onClick={handleSave}
            disabled={saving || !form.name.trim()}
            className="flex items-center gap-1.5 px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white text-xs rounded-lg font-medium transition-colors disabled:opacity-50"
          >
            <Save className="w-3 h-3" />
            {saving ? 'Saving...' : editingRuleId ? 'Update Rule' : 'Create Rule'}
          </button>
        </div>
      )}

      {/* Rules list */}
      <div className="space-y-2">
        {rules.map((rule) => (
          <div
            key={rule.id}
            className={`bg-slate-800/60 border rounded-lg p-3 transition-all ${
              rule.active ? 'border-slate-700' : 'border-slate-700/50 opacity-60'
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-white">{rule.name}</span>
                  <span className="text-[10px] text-slate-500 bg-slate-700/50 px-1.5 py-0.5 rounded">
                    P{rule.priority}
                  </span>
                </div>
                {rule.description && (
                  <p className="text-xs text-slate-500 mt-0.5">{rule.description}</p>
                )}
                <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                  {rule.category && (
                    <span className="text-[10px] bg-blue-500/10 text-blue-400 px-1.5 py-0.5 rounded">
                      {rule.category}
                    </span>
                  )}
                  {rule.department && (
                    <span className="text-[10px] bg-green-500/10 text-green-400 px-1.5 py-0.5 rounded">
                      {rule.department}
                    </span>
                  )}
                  {rule.amount_min != null && (
                    <span className="text-[10px] bg-yellow-500/10 text-yellow-400 px-1.5 py-0.5 rounded">
                      ≥ ${rule.amount_min}
                    </span>
                  )}
                  {rule.amount_max != null && (
                    <span className="text-[10px] bg-yellow-500/10 text-yellow-400 px-1.5 py-0.5 rounded">
                      ≤ ${rule.amount_max}
                    </span>
                  )}
                  <span className="text-slate-600 mx-0.5">→</span>
                  {rule.required_approvers.map((role, i) => (
                    <span key={i} className="flex items-center gap-0.5">
                      <span className="text-[10px] bg-purple-500/10 text-purple-400 px-1.5 py-0.5 rounded font-medium">
                        {role.replace('_', ' ')}
                      </span>
                      {i < rule.required_approvers.length - 1 && (
                        <ChevronRight className="w-2.5 h-2.5 text-slate-600" />
                      )}
                    </span>
                  ))}
                </div>
              </div>

              <div className="flex items-center gap-2 ml-3">
                <button
                  onClick={() => handleEdit(rule)}
                  className="text-slate-400 hover:text-blue-400 transition-colors"
                  title="Edit rule"
                >
                  <Pencil className="w-4 h-4" />
                </button>
                <button
                  onClick={() => handleToggle(rule.id)}
                  className="text-slate-400 hover:text-white transition-colors"
                  title={rule.active ? 'Deactivate' : 'Activate'}
                >
                  {rule.active ? (
                    <ToggleRight className="w-5 h-5 text-green-400" />
                  ) : (
                    <ToggleLeft className="w-5 h-5 text-slate-500" />
                  )}
                </button>
                <button
                  onClick={() => handleDelete(rule.id)}
                  className="text-slate-500 hover:text-red-400 transition-colors"
                  title="Delete rule"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        ))}

        {rules.length === 0 && (
          <p className="text-center text-slate-500 py-8 text-sm">
            No approval rules configured. Add one to enable multi-step approvals.
          </p>
        )}
      </div>
    </div>
  );
}
