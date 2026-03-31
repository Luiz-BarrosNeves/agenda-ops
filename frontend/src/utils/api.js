import axios from 'axios';

const API_URL = process.env.REACT_APP_BACKEND_URL + '/api';

const api = axios.create({
  baseURL: API_URL,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (process.env.NODE_ENV === 'development') {
    // Log temporário para debug de autenticação
    const masked = token ? (token.slice(0, 12) + '...') : null;
    // eslint-disable-next-line no-console
    console.log('[api.js] Auth debug:', {
      tokenExists: !!token,
      authorizationHeader: token ? `Bearer ${masked}` : undefined
    });
  }
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const usersAPI = {
  getAll: (params) => api.get('/users', { params }),
  getById: (id) => api.get(`/users/${id}`),
  getMe: () => api.get('/auth/me'),
  getAttendants: () => api.get('/users/attendants'),
  getTeamStats: () => api.get('/users/stats/team'),
  getWithPermission: (system) => api.get(`/users/with-permission/${system}`),
  approve: (id) => api.put(`/users/${id}/approve`),
  updateRole: (id, role) => api.put(`/users/${id}/role`, { role }),
  updatePermissions: (id, permissions) => api.put(`/users/${id}/permissions`, permissions),
  delete: (id) => api.delete(`/users/${id}`),

  // Altera a própria senha
  changeMyPassword: (current_password, new_password, confirm_password) =>
    api.put('/users/me/password', { current_password, new_password, confirm_password }),

  // Supervisor reseta senha de outro usuário
  resetUserPassword: (user_id, new_password, confirm_password) =>
    api.put(`/users/${user_id}/password`, { new_password, confirm_password }),
};

export const appointmentsAPI = {
  create: (data) => api.post('/appointments', data),
  createRecurring: (data) => api.post('/appointments/recurring', data),
  getAll: (params) => api.get('/appointments', { params }),
  getPaginated: (page = 1, pageSize = 20, params = {}) => 
    api.get('/appointments/paginated', { params: { page, page_size: pageSize, ...params } }),
  getFiltered: (params) => api.get('/appointments/filtered', { params }),
  getPending: () => api.get('/appointments/pending'),
  getById: (id) => api.get(`/appointments/${id}`),
  getHistory: (id) => api.get(`/appointments/${id}/history`),
  getRecurringInfo: (id) => api.get(`/appointments/${id}/recurring-info`),
  update: (id, data) => api.put(`/appointments/${id}`, data),
  assign: (id, userId) => api.put(`/appointments/${id}/assign`, { user_id: userId }),
  delete: (id) => api.delete(`/appointments/${id}`),
  uploadDocuments: (id, files) => {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));
    return api.post(`/appointments/${id}/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },
  downloadDocument: (id, filename) => api.get(`/appointments/${id}/download/${filename}`, { responseType: 'blob' }),
  deleteDocument: (id, filename) => api.delete(`/appointments/${id}/document/${filename}`),
  getAvailableSlots: (date, emissionSystem = null) => api.get('/appointments/available-slots', { 
    params: { date, emission_system: emissionSystem } 
  }),
  redistribute: (targetAppointmentId) => api.post('/appointments/redistribute', { 
    target_appointment_id: targetAppointmentId 
  }),
  checkRedistribution: (aptId) => api.get(`/appointments/check-redistribution/${aptId}`),
  // Meus Agendamentos
  getMyAppointments: (date) => api.get('/my-appointments', { params: { date } }),
  getMyAppointmentsStats: () => api.get('/my-appointments/stats'),
  // Solicitações de alteração
  createChangeRequest: (data) => api.post('/change-requests', data),
  getChangeRequests: (status) => api.get('/change-requests', { params: { status } }),
  reviewChangeRequest: (id, approved, notes) => api.put(`/change-requests/${id}/review`, null, { 
    params: { approved, review_notes: notes } 
  }),
};

export const blockedSlotsAPI = {
  create: (data) => api.post('/blocked-slots', data),
  getAll: (userId) => api.get('/blocked-slots', { params: { user_id: userId } }),
  delete: (id) => api.delete(`/blocked-slots/${id}`),
};

export const notificationsAPI = {
  getAll: (read) => api.get('/notifications', { params: { read } }),
  markRead: (id) => api.put(`/notifications/${id}/read`),
  markAllRead: () => api.put('/notifications/read-all'),
  delete: (id) => api.delete(`/notifications/${id}`),
  deleteAllRead: () => api.delete('/notifications'),
};

export const statsAPI = {
  getDashboard: (date) => api.get('/stats/dashboard', { params: { date } }),
};

export const presenceAPI = {
  sendHeartbeat: () => api.post('/presence/heartbeat'),
  goOffline: () => api.post('/presence/offline'),
  getAgentsPresence: () => api.get('/presence/agents'),
};

export const reportsAPI = {
  getDaily: (date) => api.get('/reports/daily', { params: { date } }),
  getWeeklyHours: () => api.get('/reports/weekly-hours'),
  exportDailyCSV: (date) => api.get('/reports/daily/csv', { 
    params: { date }, 
    responseType: 'blob' 
  }),
  exportWeeklyHoursCSV: () => api.get('/reports/weekly-hours/csv', { 
    responseType: 'blob' 
  }),
};

// ============== TEMPLATES API ==============

export const templatesAPI = {
  create: (data) => api.post('/templates', data),
  getAll: (params = {}) => api.get('/templates', { params }),
  getById: (id) => api.get(`/templates/${id}`),
  update: (id, data) => api.put(`/templates/${id}`, data),
  delete: (id) => api.delete(`/templates/${id}`),
  use: (id) => api.post(`/templates/${id}/use`),
  createFromAppointment: (aptId, templateName) => 
    api.post(`/templates/from-appointment/${aptId}?template_name=${encodeURIComponent(templateName)}`),
};

export const slotsAPI = {
  getAll: (date) => api.get('/slots/all', { params: { date } }),
  getExtraHours: (date) => api.get('/extra-hours', { params: { date } }),
  updateExtraHours: (date, slots) => api.put('/extra-hours', null, { params: { date, slots } }),
};

export default api;
