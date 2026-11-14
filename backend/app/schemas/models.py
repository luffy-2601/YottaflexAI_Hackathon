import datetime
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any

class CustomerBase(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    tier: str = "STANDARD"

class CustomerCreate(CustomerBase):
    customer_id: Optional[str] = None

class CustomerResponse(CustomerBase):
    customer_id: str
    created_at: datetime.datetime
    class Config:
        from_attributes = True

class MessageBase(BaseModel):
    sender_type: str # CUSTOMER, AGENT, SYSTEM
    sender_id: str
    body: str

class MessageCreate(MessageBase):
    pass

class MessageResponse(MessageBase):
    message_id: str
    ticket_id: str
    sentiment_score: Optional[float] = None
    created_at: datetime.datetime
    class Config:
        from_attributes = True

class TicketCreateRequest(BaseModel):
    customer_id: str
    channel_id: str # email, chat, phone
    subject: str
    body: str
    tenant_id: str = "default_tenant"
    language_code: Optional[str] = None # Optional override, otherwise auto-detected
    priority: Optional[str] = None # Optional override, otherwise auto-determined

class TicketResponse(BaseModel):
    ticket_id: str
    tenant_id: str = "default_tenant"
    customer_id: str
    channel_id: str
    subject: str
    status: str
    priority: str
    intent_id: str
    language_code: str
    assigned_agent_id: Optional[str] = None
    queue_id: Optional[str] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    first_response_at: Optional[datetime.datetime] = None
    resolved_at: Optional[datetime.datetime] = None
    class Config:
        from_attributes = True

class AssignmentEventResponse(BaseModel):
    assignment_id: str
    ticket_id: str
    agent_id: str
    event_type: str
    actor_id: str
    reason: str
    created_at: datetime.datetime
    class Config:
        from_attributes = True

class SLAEventResponse(BaseModel):
    sla_id: str
    ticket_id: str
    first_response_due_at: datetime.datetime
    resolution_due_at: datetime.datetime
    first_response_actual_at: Optional[datetime.datetime] = None
    resolution_actual_at: Optional[datetime.datetime] = None
    is_first_response_breached: bool
    is_resolution_breached: bool
    status: str
    class Config:
        from_attributes = True

class ResolutionResponse(BaseModel):
    resolution_id: str
    ticket_id: str
    agent_id: str
    resolution_code: str
    summary: str
    csat_score: Optional[int] = None
    csat_feedback: Optional[str] = None
    created_at: datetime.datetime
    class Config:
        from_attributes = True

class TicketDetailResponse(TicketResponse):
    customer: Optional[CustomerResponse] = None
    messages: List[MessageResponse] = []
    assignment_events: List[AssignmentEventResponse] = []
    sla_events: List[SLAEventResponse] = []
    resolution: Optional[ResolutionResponse] = None

class TicketTransferRequest(BaseModel):
    to_agent_id: str
    reason: str

class TicketEscalateRequest(BaseModel):
    reason: str

class TicketReopenRequest(BaseModel):
    reason: str

class TicketResolveRequest(BaseModel):
    agent_id: str
    resolution_code: str = "SOLVED"
    summary: str
    csat_score: Optional[int] = Field(default=None, ge=1, le=5)
    csat_feedback: Optional[str] = None

class AgentSkillItem(BaseModel):
    skill_id: str
    proficiency_level: float

class AgentLanguageItem(BaseModel):
    language_code: str
    fluency_score: float

class AgentShiftItem(BaseModel):
    day_of_week: int
    start_hour: int
    end_hour: int
    timezone: str

class AgentResponse(BaseModel):
    agent_id: str
    name: str
    email: str
    status: str
    max_concurrency: int
    current_active_tickets: int
    experience_score: float
    skills: List[AgentSkillItem] = []
    languages: List[AgentLanguageItem] = []
    shifts: List[AgentShiftItem] = []
    utilization_rate: float = 0.0
    class Config:
        from_attributes = True

class ClassificationRequest(BaseModel):
    subject: str
    body: str

class ClassificationResult(BaseModel):
    intent_id: str
    category: str
    confidence: float
    language_code: str
    priority: str
    required_skill_id: str = "CUSTOMER_SUCCESS"
    all_detected_intents: List[str] = []
    duration_text: Optional[str] = None
    is_recurring: bool = False
    customer_impact: str = "MEDIUM"
    needs_manual_review: bool = False
    applied_safety_rules: List[str] = []
    classification_method: str = "HYBRID_RULE_ENGINE"

class RoutingCandidateScore(BaseModel):
    agent_id: str
    agent_name: str
    skill_score: float
    language_score: float
    capacity_score: float
    experience_score: float
    total_score: float

class RoutingRejectedCandidate(BaseModel):
    agent_id: str
    agent_name: str
    reasons: List[str]

class RoutingEvaluationResponse(BaseModel):
    ticket_id: str
    eligible_count: int
    selected_agent_id: Optional[str]
    final_score: Optional[float]
    explanation: str
    candidate_scores: List[RoutingCandidateScore] = []
    rejected_candidates: List[RoutingRejectedCandidate] = []

class AnomalyResponse(BaseModel):
    anomaly_id: str
    ticket_id: Optional[str] = None
    agent_id: Optional[str] = None
    category: str
    severity: str
    description: str
    expected_behavior: str
    actual_behavior: str
    detected_at: datetime.datetime
    class Config:
        from_attributes = True

class BenchmarkStrategyMetrics(BaseModel):
    strategy_name: str
    total_tickets: int
    skill_match_rate: float
    language_match_rate: float
    capacity_violation_rate: float
    sla_compliance_rate: float
    average_wait_time_minutes: float
    unassigned_ticket_rate: float
    agent_workload_std_dev: float

class BenchmarkComparisonResponse(BaseModel):
    timestamp: datetime.datetime
    sample_size: int
    strategies: Dict[str, BenchmarkStrategyMetrics]

class SLAPauseRequest(BaseModel):
    reason: str # WAITING_FOR_CUSTOMER, WAITING_FOR_THIRD_PARTY, WAITING_FOR_EXTERNAL_DEPENDENCY
    authorized_by: str = "SUPERVISOR"

class SLAResumeRequest(BaseModel):
    authorized_by: str = "SUPERVISOR"
    reason: Optional[str] = "Customer replied / external dependency resolved"

class SLAPolicyCreate(BaseModel):
    policy_id: str
    tenant_id: str = "default_tenant"
    name: str
    channel_id: Optional[str] = None
    priority: Optional[str] = None
    category: Optional[str] = None
    customer_tier: Optional[str] = None
    first_response_minutes: int = 15
    resolution_minutes: int = 240
    business_hours_only: bool = True
    timezone: str = "Asia/Kolkata"
    work_start_hour: int = 9
    work_end_hour: int = 18
    work_days: str = "0,1,2,3,4"
    escalation_level_1_ratio: float = 0.70
    escalation_level_2_ratio: float = 0.90
    is_active: bool = True

class SLAPolicyResponse(SLAPolicyCreate):
    created_at: datetime.datetime
    class Config:
        from_attributes = True

class SLAHistoryEventResponse(BaseModel):
    history_id: str
    ticket_id: str
    sla_id: str
    event_type: str
    actor: str
    reason: Optional[str] = None
    idempotency_key: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    created_at: datetime.datetime
    class Config:
        from_attributes = True

class SLATicketDetailResponse(BaseModel):
    sla_id: str
    ticket_id: str
    policy_id: Optional[str] = None
    status: str
    risk_level: str
    escalation_level: int
    is_paused: bool
    pause_reason: Optional[str] = None
    total_paused_seconds: int
    
    first_response_due_at: datetime.datetime
    first_response_actual_at: Optional[datetime.datetime] = None
    is_first_response_breached: bool
    first_response_remaining_business_minutes: Optional[float] = None
    
    resolution_due_at: datetime.datetime
    resolution_actual_at: Optional[datetime.datetime] = None
    is_resolution_breached: bool
    resolution_remaining_business_minutes: Optional[float] = None
    
    history_events: List[SLAHistoryEventResponse] = []
    class Config:
        from_attributes = True

# -------------------------------------------------------------
# AUTH & RBAC SCHEMAS
# -------------------------------------------------------------

class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str
    role: str = "AGENT" # ADMIN, SUPERVISOR, AGENT, ANALYST
    tenant_id: str = "default_tenant"
    agent_id: Optional[str] = None

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    role: str
    tenant_id: str

class UserResponse(BaseModel):
    user_id: str
    email: str
    role: str
    tenant_id: str
    agent_id: Optional[str] = None
    is_active: bool
    created_at: datetime.datetime
    class Config:
        from_attributes = True
