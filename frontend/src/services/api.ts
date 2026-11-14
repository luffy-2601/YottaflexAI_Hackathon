import {
  OperationsOverview, Ticket, Agent, RoutingDecisionEvaluation,
  AnomalyItem, BenchmarkComparisonResponse
} from '../types';

const API_BASE = '/api/v1';

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const token = localStorage.getItem('omniroute_token');
  const headers = new Headers(options?.headers);
  if (!headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const res = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers,
  });

  if (res.status === 401) {
    // Unauthorized: token expired or missing
    localStorage.removeItem('omniroute_token');
    localStorage.removeItem('omniroute_user');
    window.dispatchEvent(new Event('omniroute_auth_expired'));
  }

  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`API Error ${res.status}: ${errorText}`);
  }
  return res.json();
}

export const api = {
  // Authentication & RBAC
  login: (payload: { email: string; password: string }) =>
    fetchJson<{ access_token: string; token_type: string; user_id: string; email: string; role: string; tenant_id: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  register: (payload: { email: string; password: string; role: string; tenant_id?: string }) =>
    fetchJson<any>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  getMe: () => fetchJson<{ user_id: string; email: string; role: string; tenant_id: string }>('/auth/me'),

  logout: () => {
    localStorage.removeItem('omniroute_token');
    localStorage.removeItem('omniroute_user');
    window.dispatchEvent(new Event('omniroute_auth_expired'));
  },

  // Machine Learning SLA Breach Prediction
  getMLPrediction: (ticketId: string) =>
    fetchJson<{ ticket_id: string; breach_probability: number; predicted_risk_level: string; top_risk_factors: string[]; model_version: string; model_evaluation?: any }>(`/sla/tickets/${ticketId}/predict`),

  // Autonomous Queue Dispatch
  dispatchQueue: (tenantId: string = 'default_tenant') =>
    fetchJson<{ status: string; total_dispatched: number; agents_serviced: number; dispatches: any[] }>(`/routing/dispatch-queue?tenant_id=${tenantId}`, {
      method: 'POST',
    }),

  // Analytics
  getOverview: () => fetchJson<OperationsOverview>('/analytics/overview'),

  // Tickets
  getTickets: (params?: { status?: string; priority?: string; channel_id?: string; search?: string }) => {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.append('status', params.status);
    if (params?.priority) searchParams.append('priority', params.priority);
    if (params?.channel_id) searchParams.append('channel_id', params.channel_id);
    if (params?.search) searchParams.append('search', params.search);
    return fetchJson<Ticket[]>(`/tickets?${searchParams.toString()}`);
  },

  getTicketDetail: (ticketId: string) => fetchJson<Ticket>(`/tickets/${ticketId}`),

  createTicket: (payload: { customer_id: string; channel_id: string; subject: string; body: string; language_code?: string; priority?: string }) =>
    fetchJson<Ticket>('/tickets', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  addMessage: (ticketId: string, payload: { sender_type: string; sender_id: string; body: string }) =>
    fetchJson(`/tickets/${ticketId}/messages`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  transferTicket: (ticketId: string, payload: { to_agent_id: string; reason: string }) =>
    fetchJson<Ticket>(`/tickets/${ticketId}/transfer`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  escalateTicket: (ticketId: string, payload: { reason: string }) =>
    fetchJson<Ticket>(`/tickets/${ticketId}/escalate`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  reopenTicket: (ticketId: string, payload: { reason: string }) =>
    fetchJson<Ticket>(`/tickets/${ticketId}/reopen`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  resolveTicket: (ticketId: string, payload: { agent_id: string; resolution_code: string; summary: string; csat_score?: number; csat_feedback?: string }) =>
    fetchJson(`/tickets/${ticketId}/resolve`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // Agents
  getAgents: (status?: string) =>
    fetchJson<Agent[]>(`/agents${status ? `?status=${status}` : ''}`),

  updateAgentStatus: (agentId: string, status: string) =>
    fetchJson<Agent>(`/agents/${agentId}/status?status=${status}`, { method: 'PUT' }),

  // Routing
  evaluateRouting: (ticketId: string) =>
    fetchJson<RoutingDecisionEvaluation>(`/routing/evaluate/${ticketId}`, { method: 'POST' }),

  classifyText: (payload: { subject: string; body: string }) =>
    fetchJson<{ intent_id: string; category: string; confidence: number; language_code: string; priority: string; applied_safety_rules: string[] }>('/routing/classify', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // SLA
  getSLASummary: () => fetchJson<{ total_monitored: number; breached_count: number; compliance_pct: number; approaching_breach_count: number }>('/sla/summary'),
  getActiveSLAs: () => fetchJson<any[]>('/sla/active'),

  // Anomalies
  getAnomalies: () => fetchJson<AnomalyItem[]>('/anomalies'),
  scanAnomalies: () => fetchJson<AnomalyItem[]>('/anomalies/scan', { method: 'POST' }),

  // Evaluation & Benchmark
  getBenchmarks: (sampleLimit: number = 200) =>
    fetchJson<BenchmarkComparisonResponse>(`/evaluation/benchmarks?sample_limit=${sampleLimit}`),

  runSimulation: (sampleLimit: number = 200) =>
    fetchJson<BenchmarkComparisonResponse>(`/evaluation/simulate?sample_limit=${sampleLimit}`, { method: 'POST' }),

  // Config
  getConfig: () => fetchJson<any>('/config'),
  updateWeights: (payload: { weight_skill: number; weight_language: number; weight_capacity: number; weight_experience: number }) =>
    fetchJson('/config/weights', {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),
};
