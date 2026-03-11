const API_BASE = '/api';

async function request(endpoint, options = {}) {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || 'Request failed');
  }

  return response.json();
}

export const api = {
  // Dashboard
  getDashboard: () => request('/dashboard'),

  // Projects
  getProjects: () => request('/projects/'),
  getProject: (id) => request(`/projects/${id}`),
  createProject: (data) => request('/projects/', { method: 'POST', body: JSON.stringify(data) }),
  updateProject: (id, data) => request(`/projects/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteProject: (id) => request(`/projects/${id}`, { method: 'DELETE' }),

  // Tasks
  getTasks: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/tasks/${query ? `?${query}` : ''}`);
  },
  getTask: (id) => request(`/tasks/${id}`),
  createTask: (data) => request('/tasks/', { method: 'POST', body: JSON.stringify(data) }),
  updateTask: (id, data) => request(`/tasks/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteTask: (id) => request(`/tasks/${id}`, { method: 'DELETE' }),
  reorderTasks: (orders) => request('/tasks/reorder', { method: 'POST', body: JSON.stringify(orders) }),

  // Comments
  addComment: (taskId, data) => request(`/tasks/${taskId}/comments`, { method: 'POST', body: JSON.stringify(data) }),
  deleteComment: (taskId, commentId) => request(`/tasks/${taskId}/comments/${commentId}`, { method: 'DELETE' }),

  // Time tracking
  logTime: (taskId, data) => request(`/tasks/${taskId}/time`, { method: 'POST', body: JSON.stringify(data) }),
  getTimeEntries: (taskId) => request(`/tasks/${taskId}/time`),

  // Epics
  getEpics: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/epics/${query ? `?${query}` : ''}`);
  },
  createEpic: (data) => request('/epics/', { method: 'POST', body: JSON.stringify(data) }),
  updateEpic: (id, data) => request(`/epics/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteEpic: (id) => request(`/epics/${id}`, { method: 'DELETE' }),

  // Sprints
  getSprints: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/sprints/${query ? `?${query}` : ''}`);
  },
  createSprint: (data) => request('/sprints/', { method: 'POST', body: JSON.stringify(data) }),
  updateSprint: (id, data) => request(`/sprints/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteSprint: (id) => request(`/sprints/${id}`, { method: 'DELETE' }),
  startSprint: (id) => request(`/sprints/${id}/start`, { method: 'POST' }),
  completeSprint: (id) => request(`/sprints/${id}/complete`, { method: 'POST' }),

  // Labels
  getLabels: () => request('/labels/'),
  createLabel: (data) => request('/labels/', { method: 'POST', body: JSON.stringify(data) }),
  deleteLabel: (id) => request(`/labels/${id}`, { method: 'DELETE' }),

  // GitHub
  getGitHubStatus: () => request('/github/status'),
  getGitHubRepos: () => request('/github/repos'),
  getGitHubIssues: (owner, repo) => request(`/github/repos/${owner}/${repo}/issues`),

  // Gmail
  getGmailStatus: () => request('/gmail/status'),
  getGmailAuth: () => request('/gmail/auth'),
  getEmailFilters: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/gmail/filters${query ? `?${query}` : ''}`);
  },
  createEmailFilter: (data) => request('/gmail/filters', { method: 'POST', body: JSON.stringify(data) }),
  deleteEmailFilter: (id) => request(`/gmail/filters/${id}`, { method: 'DELETE' }),
  syncEmails: (projectId) => request(`/gmail/sync${projectId ? `?project_id=${projectId}` : ''}`, { method: 'POST' }),
  getEmails: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/gmail/emails${query ? `?${query}` : ''}`);
  },
  deleteEmail: (id, blockSender = false) => request(`/gmail/emails/${id}?block_sender=${blockSender}`, { method: 'DELETE' }),

  // Calendar
  syncCalendar: () => request('/gmail/sync-calendar', { method: 'POST' }),
  getCalendarEvents: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/gmail/calendar${query ? `?${query}` : ''}`);
  },

  // WhatsApp
  getWhatsAppStatus: () => request('/whatsapp/status'),
  getWhatsAppGroups: () => request('/whatsapp/groups'),
  createWhatsAppGroup: (data) => request('/whatsapp/groups', { method: 'POST', body: JSON.stringify(data) }),
  deleteWhatsAppGroup: (id) => request(`/whatsapp/groups/${id}`, { method: 'DELETE' }),
  syncWhatsApp: () => request('/whatsapp/sync', { method: 'POST' }),
  getWhatsAppMessages: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/whatsapp/messages${query ? `?${query}` : ''}`);
  },

  // AI
  getAIStatus: () => request('/ai/status'),
  summarizeEmail: (emailId) => request(`/ai/summarize-email/${emailId}`, { method: 'POST' }),
  parseWhatsApp: (content) => request('/ai/parse-whatsapp', { method: 'POST', body: JSON.stringify({ content }) }),
  planSprint: (epicId, numTasks = 5) => request(`/ai/plan-sprint/${epicId}?num_tasks=${numTasks}`, { method: 'POST' }),
  getDailyDigest: () => request('/ai/daily-digest'),
  categorizeTask: (taskId) => request(`/ai/categorize-task/${taskId}`, { method: 'POST' }),
  autoCategorizeAll: (projectId) => request(`/ai/auto-categorize-all?project_id=${projectId}`, { method: 'POST' }),
  createTaskFromText: (text, projectId) => request('/ai/create-task-from-text', {
    method: 'POST',
    body: JSON.stringify({ text, project_id: projectId })
  }),
  createTasksFromUrl: (url, projectId) => request('/ai/tasks-from-url', {
    method: 'POST',
    body: JSON.stringify({ url, project_id: projectId })
  }),

  // Logs
  getLogs: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/logs/${query ? `?${query}` : ''}`);
  },
  logError: (data) => request('/logs/', { method: 'POST', body: JSON.stringify(data) }),
  analyzeError: (id) => request(`/logs/${id}/analyze`, { method: 'POST' }),
  updateErrorStatus: (id, status) => request(`/logs/${id}/status?status=${status}`, { method: 'PUT' }),
  deleteError: (id) => request(`/logs/${id}`, { method: 'DELETE' }),
  clearAllErrors: () => request('/logs/clear-all', { method: 'DELETE' }),
};
