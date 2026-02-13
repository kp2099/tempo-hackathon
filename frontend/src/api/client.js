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

// ---- Employees ----
export const getEmployees = () => api.get('/employees/');
export const getEmployee = (id) => api.get(`/employees/${id}`);
export const getSpendingSummary = (id) => api.get(`/employees/${id}/spending`);

// ---- Audit ----
export const getAuditTrail = (params) => api.get('/audit/', { params });
export const getAuditStats = () => api.get('/audit/stats');

export default api;

