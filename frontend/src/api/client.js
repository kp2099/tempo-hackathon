import axios from 'axios';

const API_BASE = '/api';

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

// ---- Expenses ----
export const submitExpense = (data) => api.post('/expenses/submit', data);
export const getExpenses = (params) => api.get('/expenses/', { params });
export const getExpenseStats = () => api.get('/expenses/stats');
export const getExpense = (id) => api.get(`/expenses/${id}`);
export const approveExpense = (id) => api.post(`/expenses/${id}/approve`);
export const rejectExpense = (id) => api.post(`/expenses/${id}/reject`);
export const disputeExpense = (id, reason) => api.post(`/expenses/${id}/dispute`, { reason });
export const overrideExpense = (id, reason) => api.post(`/expenses/${id}/override`, { reason: reason || null });
export const parseExpenseText = (text) => api.post('/expenses/parse', { text });
export const batchApprove = () => api.post('/expenses/batch-approve');
export const uploadReceipt = (file) => {
  const formData = new FormData();
  formData.append('file', file);
  return api.post('/expenses/upload-receipt', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

// ---- Multi-Step Approval ----
export const getApprovalSteps = (expenseId) => api.get(`/expenses/${expenseId}/steps`);
export const approveStep = (expenseId, approverId, comments) =>
  api.post(`/expenses/${expenseId}/step/approve`, { approver_id: approverId, comments });
export const rejectStep = (expenseId, approverId, comments) =>
  api.post(`/expenses/${expenseId}/step/reject`, { approver_id: approverId, comments });
export const escalateStep = (expenseId, approverId, comments) =>
  api.post(`/expenses/${expenseId}/step/escalate`, { approver_id: approverId, comments });
export const getPendingForApprover = (approverId) => api.get(`/expenses/pending-for/${approverId}`);

// ---- Employees ----
export const getEmployees = () => api.get('/employees/');
export const getEmployee = (id) => api.get(`/employees/${id}`);
export const getSpendingSummary = (id) => api.get(`/employees/${id}/spending`);

// ---- Approval Rules ----
export const getApprovalRules = (activeOnly = true) =>
  api.get('/approval/rules', { params: { active_only: activeOnly } });
export const createApprovalRule = (data) => api.post('/approval/rules', data);
export const updateApprovalRule = (id, data) => api.put(`/approval/rules/${id}`, data);
export const deleteApprovalRule = (id) => api.delete(`/approval/rules/${id}`);
export const toggleApprovalRule = (id) => api.patch(`/approval/rules/${id}/toggle`);

// ---- Org Hierarchy ----
export const getOrgTree = () => api.get('/approval/org-tree');
export const getOrgFlat = () => api.get('/approval/org-flat');

// ---- Audit ----
export const getAuditTrail = (params) => api.get('/audit/', { params });
export const getAuditStats = () => api.get('/audit/stats');

export default api;
