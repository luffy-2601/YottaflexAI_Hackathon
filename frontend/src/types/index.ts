export interface Customer {
  customer_id: string;
  name: string;
  email: string;
  phone?: string;
  tier: string;
  created_at: string;
}

export interface Message {
  message_id: string;
  ticket_id: string;
  sender_type: 'CUSTOMER' | 'AGENT' | 'SYSTEM';
  sender_id: string;
  body: string;
  sentiment_score?: number;
  created_at: string;
}

export interface AssignmentEvent {
  assignment_id: string;
  ticket_id: string;
  agent_id: string;
  event_type: string;
  actor_id: string;
  reason: string;
  created_at: string;
}

export interface SLAEvent {
  sla_id: string;
  ticket_id: string;
  first_response_due_at: string;
  resolution_due_at: string;
  first_response_actual_at?: string;
  resolution_actual_at?: string;
  is_first_response_breached: boolean;
  is_resolution_breached: boolean;
  status: string;
}

export interface Resolution {
  resolution_id: string;
  ticket_id: string;
  agent_id: string;
  resolution_code: string;
  summary: string;
  csat_score?: number;
  csat_feedback?: string;
  created_at: string;
}

export interface Ticket {
  ticket_id: string;
  customer_id: string;
  channel_id: string;
  subject: string;
  status: string;
  priority: 'P1' | 'P2' | 'P3' | 'P4';
  intent_id: string;
  language_code: string;
  assigned_agent_id?: string;
  queue_id?: string;
  created_at: string;
  updated_at: string;
  first_response_at?: string;
  resolved_at?: string;
  customer?: Customer;
  messages?: Message[];
  assignment_events?: AssignmentEvent[];
  sla_events?: SLAEvent[];
  resolution?: Resolution;
}

export interface Agent {
  agent_id: string;
  name: string;
  email: string;
  status: 'ACTIVE' | 'ON_BREAK' | 'INACTIVE';
  max_concurrency: number;
  current_active_tickets: number;
  experience_score: number;
  skills: { skill_id: string; proficiency_level: number }[];
  languages: { language_code: string; fluency_score: number }[];
  shifts: { day_of_week: number; start_hour: number; end_hour: number; timezone: string }[];
  utilization_rate: number;
}

export interface RoutingCandidateScore {
  agent_id: string;
  agent_name: string;
  skill_score: number;
  language_score: number;
  capacity_score: number;
  experience_score: number;
  total_score: number;
}

export interface RoutingRejectedCandidate {
  agent_id: string;
  agent_name: string;
  reasons: string[];
}

export interface RoutingDecisionEvaluation {
  ticket_id: string;
  eligible_count: number;
  selected_agent_id?: string;
  final_score?: number;
  explanation: string;
  candidate_scores: RoutingCandidateScore[];
  rejected_candidates: RoutingRejectedCandidate[];
}

export interface AnomalyItem {
  anomaly_id: string;
  ticket_id?: string;
  agent_id?: string;
  category: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  description: string;
  expected_behavior: string;
  actual_behavior: string;
  detected_at: string;
}

export interface OperationsOverview {
  total_tickets: number;
  open_tickets: number;
  resolved_tickets: number;
  unassigned_tickets: number;
  critical_incidents: number;
  active_agents: number;
  overall_utilization_pct: number;
  sla_compliance_pct: number;
  sla_breaches_count: number;
  avg_first_response_minutes: number;
  avg_resolution_minutes: number;
  avg_csat: number;
  distributions: {
    channel: { channel: string; count: number }[];
    priority: { priority: string; count: number }[];
    intent: { intent: string; count: number }[];
    status: { status: string; count: number }[];
  };
}

export interface StrategyBenchmarkMetrics {
  strategy_name: string;
  total_tickets: number;
  skill_match_rate: number;
  language_match_rate: number;
  capacity_violation_rate: number;
  sla_compliance_rate: number;
  average_wait_time_minutes: number;
  unassigned_ticket_rate: number;
  agent_workload_std_dev: number;
}

export interface BenchmarkComparisonResponse {
  timestamp: string;
  sample_size: number;
  strategies: Record<string, StrategyBenchmarkMetrics>;
}
