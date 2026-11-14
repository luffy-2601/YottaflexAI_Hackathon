import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON,
    UniqueConstraint, Index, CheckConstraint
)
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)

# -------------------------------------------------------------
# MASTER ENTITIES
# -------------------------------------------------------------

class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(String(32), primary_key=True, index=True) # e.g. CUS-000001
    tenant_id = Column(String(32), nullable=False, default="default_tenant", index=True)
    name = Column(String(128), nullable=False)
    email = Column(String(128), nullable=False, index=True)
    phone = Column(String(32), nullable=True)
    tier = Column(String(20), nullable=False, default="STANDARD") # STANDARD, VIP, ENTERPRISE
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    tickets = relationship("Ticket", back_populates="customer")

class Channel(Base):
    __tablename__ = "channels"

    channel_id = Column(String(20), primary_key=True) # email, chat, phone
    name = Column(String(64), nullable=False)
    default_sla_factor = Column(Float, nullable=False, default=1.0)
    is_active = Column(Boolean, nullable=False, default=True)

    tickets = relationship("Ticket", back_populates="channel")

class Skill(Base):
    __tablename__ = "skills"

    skill_id = Column(String(64), primary_key=True) # e.g. PAYMENT_PROCESSING, LINUX_SYSADMIN
    name = Column(String(128), nullable=False)
    description = Column(String(256), nullable=True)
    tier_level = Column(Integer, nullable=False, default=1)

    agent_skills = relationship("AgentSkill", back_populates="skill")

class Language(Base):
    __tablename__ = "languages"

    language_code = Column(String(10), primary_key=True) # en, te, hi, ta, kn
    name = Column(String(64), nullable=False)
    is_supported = Column(Boolean, nullable=False, default=True)

    agent_languages = relationship("AgentLanguage", back_populates="language")

class Intent(Base):
    __tablename__ = "intents"

    intent_id = Column(String(64), primary_key=True) # PAYMENT_FAILURE, REFUND_REQUEST, etc.
    name = Column(String(128), nullable=False)
    category = Column(String(64), nullable=False) # BILLING, AUTH, TECH, GENERAL
    default_priority = Column(String(10), nullable=False, default="P3") # P1, P2, P3, P4
    required_skill_id = Column(String(64), ForeignKey("skills.skill_id"), nullable=True)

    required_skill = relationship("Skill")
    priority_rules = relationship("PriorityRule", back_populates="intent")

class PriorityRule(Base):
    __tablename__ = "priority_rules"

    rule_id = Column(String(64), primary_key=True)
    rule_name = Column(String(128), nullable=False)
    intent_id = Column(String(64), ForeignKey("intents.intent_id"), nullable=True)
    trigger_keyword = Column(String(128), nullable=True)
    enforced_priority = Column(String(10), nullable=False) # P1, P2, P3, P4
    is_safety_critical = Column(Boolean, nullable=False, default=False)

    intent = relationship("Intent", back_populates="priority_rules")

class Queue(Base):
    __tablename__ = "queues"

    queue_id = Column(String(64), primary_key=True) # Q_EMAIL_VIP, Q_TECH_SUPPORT
    tenant_id = Column(String(32), nullable=False, default="default_tenant", index=True)
    name = Column(String(128), nullable=False)
    channel_id = Column(String(20), ForeignKey("channels.channel_id"), nullable=False)
    priority_min = Column(String(10), nullable=False, default="P4")
    routing_strategy = Column(String(64), nullable=False, default="INTELLIGENT")

    agent_queues = relationship("AgentQueue", back_populates="queue")

# -------------------------------------------------------------
# AGENT & CAPACITY ENTITIES
# -------------------------------------------------------------

class Agent(Base):
    __tablename__ = "agents"

    agent_id = Column(String(32), primary_key=True, index=True) # e.g. AGT-000001
    tenant_id = Column(String(32), nullable=False, default="default_tenant", index=True)
    name = Column(String(128), nullable=False)
    email = Column(String(128), nullable=False, unique=True)
    status = Column(String(20), nullable=False, default="ACTIVE") # ACTIVE, INACTIVE, ON_BREAK
    max_concurrency = Column(Integer, nullable=False, default=3)
    current_active_tickets = Column(Integer, nullable=False, default=0)
    experience_score = Column(Float, nullable=False, default=0.80) # 0.0 - 1.0
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    skills = relationship("AgentSkill", back_populates="agent", cascade="all, delete-orphan")
    languages = relationship("AgentLanguage", back_populates="agent", cascade="all, delete-orphan")
    shifts = relationship("AgentShift", back_populates="agent", cascade="all, delete-orphan")
    queues = relationship("AgentQueue", back_populates="agent", cascade="all, delete-orphan")
    assigned_tickets = relationship("Ticket", back_populates="assigned_agent", foreign_keys="Ticket.assigned_agent_id")

class AgentSkill(Base):
    __tablename__ = "agent_skills"

    agent_id = Column(String(32), ForeignKey("agents.agent_id", ondelete="CASCADE"), primary_key=True)
    skill_id = Column(String(64), ForeignKey("skills.skill_id", ondelete="CASCADE"), primary_key=True)
    proficiency_level = Column(Float, nullable=False, default=1.0) # 0.0 - 1.0

    agent = relationship("Agent", back_populates="skills")
    skill = relationship("Skill", back_populates="agent_skills")

class AgentLanguage(Base):
    __tablename__ = "agent_languages"

    agent_id = Column(String(32), ForeignKey("agents.agent_id", ondelete="CASCADE"), primary_key=True)
    language_code = Column(String(10), ForeignKey("languages.language_code", ondelete="CASCADE"), primary_key=True)
    fluency_score = Column(Float, nullable=False, default=1.0) # 0.0 - 1.0

    agent = relationship("Agent", back_populates="languages")
    language = relationship("Language", back_populates="agent_languages")

class AgentShift(Base):
    __tablename__ = "agent_shifts"

    shift_id = Column(String(64), primary_key=True)
    agent_id = Column(String(32), ForeignKey("agents.agent_id", ondelete="CASCADE"), nullable=False)
    day_of_week = Column(Integer, nullable=False) # 0=Monday, 6=Sunday
    start_hour = Column(Integer, nullable=False, default=9)
    end_hour = Column(Integer, nullable=False, default=18)
    timezone = Column(String(32), nullable=False, default="Asia/Kolkata")

    agent = relationship("Agent", back_populates="shifts")

class AgentQueue(Base):
    __tablename__ = "agent_queues"

    agent_id = Column(String(32), ForeignKey("agents.agent_id", ondelete="CASCADE"), primary_key=True)
    queue_id = Column(String(64), ForeignKey("queues.queue_id", ondelete="CASCADE"), primary_key=True)

    agent = relationship("Agent", back_populates="queues")
    queue = relationship("Queue", back_populates="agent_queues")

# -------------------------------------------------------------
# TRANSACTIONAL & EVENT ENTITIES
# -------------------------------------------------------------

class Ticket(Base):
    __tablename__ = "tickets"

    ticket_id = Column(String(32), primary_key=True, index=True) # e.g. TKT-2026-000001
    tenant_id = Column(String(32), nullable=False, default="default_tenant", index=True)
    customer_id = Column(String(32), ForeignKey("customers.customer_id"), nullable=False)
    channel_id = Column(String(20), ForeignKey("channels.channel_id"), nullable=False)
    subject = Column(String(256), nullable=False)
    status = Column(String(32), nullable=False, default="NEW") 
    # NEW, OPEN, QUEUED, ASSIGNED, IN_PROGRESS, WAITING_FOR_CUSTOMER, WAITING_FOR_EXTERNAL_DEPENDENCY, PENDING_CUSTOMER, ESCALATED, RESOLVED, REOPENED, CLOSED
    priority = Column(String(10), nullable=False, default="P3") # P1, P2, P3, P4
    intent_id = Column(String(64), ForeignKey("intents.intent_id"), nullable=False)
    language_code = Column(String(10), ForeignKey("languages.language_code"), nullable=False, default="en")
    assigned_agent_id = Column(String(32), ForeignKey("agents.agent_id"), nullable=True, index=True)
    queue_id = Column(String(64), ForeignKey("queues.queue_id"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    first_response_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    customer = relationship("Customer", back_populates="tickets")
    channel = relationship("Channel", back_populates="tickets")
    intent = relationship("Intent")
    language = relationship("Language")
    assigned_agent = relationship("Agent", back_populates="assigned_tickets", foreign_keys=[assigned_agent_id])
    
    messages = relationship("Message", back_populates="ticket", cascade="all, delete-orphan", order_by="Message.created_at")
    assignment_events = relationship("AssignmentEvent", back_populates="ticket", cascade="all, delete-orphan", order_by="AssignmentEvent.created_at")
    sla_events = relationship("SLAEvent", back_populates="ticket", cascade="all, delete-orphan")
    sla_history = relationship("SLAHistoryEvent", back_populates="ticket", cascade="all, delete-orphan", order_by="SLAHistoryEvent.created_at")
    status_events = relationship("TicketStatusEvent", back_populates="ticket", cascade="all, delete-orphan", order_by="TicketStatusEvent.created_at")
    routing_decisions = relationship("RoutingDecision", back_populates="ticket", cascade="all, delete-orphan")
    resolution = relationship("Resolution", back_populates="ticket", uselist=False, cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"

    message_id = Column(String(64), primary_key=True) # MSG-TKT-2026-000001-001
    ticket_id = Column(String(32), ForeignKey("tickets.ticket_id", ondelete="CASCADE"), nullable=False, index=True)
    sender_type = Column(String(20), nullable=False) # CUSTOMER, AGENT, SYSTEM
    sender_id = Column(String(64), nullable=False)
    body = Column(Text, nullable=False)
    sentiment_score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    ticket = relationship("Ticket", back_populates="messages")

class RoutingDecision(Base):
    __tablename__ = "routing_decisions"

    decision_id = Column(String(64), primary_key=True) # DEC-TKT-2026-000001-001
    ticket_id = Column(String(32), ForeignKey("tickets.ticket_id", ondelete="CASCADE"), nullable=False, index=True)
    selected_agent_id = Column(String(32), ForeignKey("agents.agent_id"), nullable=True)
    final_score = Column(Float, nullable=True)
    eligible_count = Column(Integer, nullable=False, default=0)
    candidate_scores = Column(JSON, nullable=True) # List of candidate scoring breakdowns
    rejected_candidates = Column(JSON, nullable=True) # List of agents and rejection reasons
    reason = Column(Text, nullable=False)
    policy_version = Column(String(32), nullable=False, default="v1.0-weighted")
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    ticket = relationship("Ticket", back_populates="routing_decisions")
    selected_agent = relationship("Agent")

class AssignmentEvent(Base):
    __tablename__ = "assignment_events"

    assignment_id = Column(String(64), primary_key=True) # ASN-TKT-2026-000001-001
    ticket_id = Column(String(32), ForeignKey("tickets.ticket_id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(String(32), ForeignKey("agents.agent_id"), nullable=False)
    event_type = Column(String(32), nullable=False, default="INITIAL_ASSIGN") # INITIAL_ASSIGN, TRANSFER, ESCALATION, REOPEN
    actor_id = Column(String(64), nullable=False, default="SYSTEM_ROUTER")
    reason = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    ticket = relationship("Ticket", back_populates="assignment_events")
    agent = relationship("Agent")

class SLAPolicy(Base):
    __tablename__ = "sla_policies"

    policy_id = Column(String(64), primary_key=True) # e.g. POL-JIO-P1, POL-DEFAULT-STANDARD
    tenant_id = Column(String(32), nullable=False, default="default_tenant", index=True)
    name = Column(String(128), nullable=False)
    channel_id = Column(String(20), nullable=True) # None = all channels
    priority = Column(String(10), nullable=True) # None = all priorities
    category = Column(String(64), nullable=True)
    customer_tier = Column(String(20), nullable=True) # STANDARD, VIP, ENTERPRISE
    first_response_minutes = Column(Integer, nullable=False, default=15)
    resolution_minutes = Column(Integer, nullable=False, default=240)
    business_hours_only = Column(Boolean, nullable=False, default=True)
    timezone = Column(String(64), nullable=False, default="Asia/Kolkata")
    work_start_hour = Column(Integer, nullable=False, default=9)
    work_end_hour = Column(Integer, nullable=False, default=18)
    work_days = Column(String(32), nullable=False, default="0,1,2,3,4")
    escalation_level_1_ratio = Column(Float, nullable=False, default=0.70)
    escalation_level_2_ratio = Column(Float, nullable=False, default=0.90)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

class SLAEvent(Base):
    __tablename__ = "sla_events"

    sla_id = Column(String(64), primary_key=True) # SLA-TKT-2026-000001
    ticket_id = Column(String(32), ForeignKey("tickets.ticket_id", ondelete="CASCADE"), nullable=False, index=True)
    policy_id = Column(String(64), ForeignKey("sla_policies.policy_id"), nullable=True)
    
    # Dual Independent Clocks
    first_response_clock_started_at = Column(DateTime(timezone=True), nullable=True)
    first_response_clock_stopped_at = Column(DateTime(timezone=True), nullable=True)
    first_response_due_at = Column(DateTime(timezone=True), nullable=False)
    first_response_actual_at = Column(DateTime(timezone=True), nullable=True)
    is_first_response_breached = Column(Boolean, nullable=False, default=False)
    
    resolution_clock_started_at = Column(DateTime(timezone=True), nullable=True)
    resolution_clock_stopped_at = Column(DateTime(timezone=True), nullable=True)
    resolution_due_at = Column(DateTime(timezone=True), nullable=False)
    resolution_actual_at = Column(DateTime(timezone=True), nullable=True)
    is_resolution_breached = Column(Boolean, nullable=False, default=False)
    
    # Risk and Escalation State
    status = Column(String(20), nullable=False, default="RUNNING") # RUNNING, PAUSED, MET, BREACHED
    risk_level = Column(String(20), nullable=False, default="ON_TRACK") # ON_TRACK, AT_RISK, CRITICAL, BREACHED, MET, PAUSED
    escalation_level = Column(Integer, nullable=False, default=0) # 0=Normal, 1=Warning, 2=Supervisor, 3=Manager
    
    # Pause tracking
    is_paused = Column(Boolean, nullable=False, default=False)
    paused_at = Column(DateTime(timezone=True), nullable=True)
    pause_reason = Column(String(128), nullable=True) # WAITING_FOR_CUSTOMER, WAITING_FOR_THIRD_PARTY, WAITING_FOR_EXTERNAL_DEPENDENCY
    paused_by = Column(String(64), nullable=True)
    total_paused_seconds = Column(Integer, nullable=False, default=0)
    
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    ticket = relationship("Ticket", back_populates="sla_events")

class SLAHistoryEvent(Base):
    __tablename__ = "sla_history_events"

    history_id = Column(String(64), primary_key=True) # SLAHIST-TKT-2026-000001-001
    ticket_id = Column(String(32), ForeignKey("tickets.ticket_id", ondelete="CASCADE"), nullable=False, index=True)
    sla_id = Column(String(64), nullable=False, index=True)
    event_type = Column(String(64), nullable=False)
    # SLA_CREATED, FIRST_RESPONSE_CLOCK_STARTED, FIRST_RESPONSE_MET, RESOLUTION_CLOCK_STARTED,
    # SLA_AT_RISK, SLA_CRITICAL, SLA_PAUSED, SLA_RESUMED, SLA_BREACHED, SLA_ESCALATED, SLA_RESOLVED, SLA_RECALCULATED
    actor = Column(String(64), nullable=False, default="SYSTEM")
    reason = Column(Text, nullable=True)
    idempotency_key = Column(String(128), nullable=True, unique=True, index=True)
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    ticket = relationship("Ticket", back_populates="sla_history")

class Resolution(Base):
    __tablename__ = "resolutions"

    resolution_id = Column(String(64), primary_key=True) # RES-TKT-2026-000001
    ticket_id = Column(String(32), ForeignKey("tickets.ticket_id", ondelete="CASCADE"), nullable=False, unique=True)
    agent_id = Column(String(32), ForeignKey("agents.agent_id"), nullable=False)
    resolution_code = Column(String(64), nullable=False, default="SOLVED") # SOLVED, WORKAROUND, DUPLICATE
    summary = Column(Text, nullable=False)
    csat_score = Column(Integer, nullable=True) # 1 to 5
    csat_feedback = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    ticket = relationship("Ticket", back_populates="resolution")
    agent = relationship("Agent")

class TicketStatusEvent(Base):
    __tablename__ = "ticket_status_events"

    event_id = Column(String(64), primary_key=True)
    ticket_id = Column(String(32), ForeignKey("tickets.ticket_id", ondelete="CASCADE"), nullable=False, index=True)
    old_status = Column(String(32), nullable=True)
    new_status = Column(String(32), nullable=False)
    changed_by = Column(String(64), nullable=False, default="SYSTEM")
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    ticket = relationship("Ticket", back_populates="status_events")

class Anomaly(Base):
    __tablename__ = "anomalies"

    anomaly_id = Column(String(64), primary_key=True)
    ticket_id = Column(String(32), ForeignKey("tickets.ticket_id", ondelete="SET NULL"), nullable=True)
    agent_id = Column(String(32), ForeignKey("agents.agent_id", ondelete="SET NULL"), nullable=True)
    category = Column(String(64), nullable=False) # CAPACITY_VIOLATION, CALENDAR_MISMATCH, HISTORY_LOSS, TRANSFER_LOOP, SAFETY_VIOLATION
    severity = Column(String(20), nullable=False, default="HIGH") # CRITICAL, HIGH, MEDIUM, LOW
    description = Column(Text, nullable=False)
    expected_behavior = Column(Text, nullable=False)
    actual_behavior = Column(Text, nullable=False)
    detected_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

class BusinessCalendar(Base):
    __tablename__ = "business_calendars"

    calendar_id = Column(String(32), primary_key=True, default="DEFAULT_CALENDAR")
    name = Column(String(128), nullable=False)
    timezone = Column(String(64), nullable=False, default="Asia/Kolkata")
    work_start_hour = Column(Integer, nullable=False, default=9)
    work_end_hour = Column(Integer, nullable=False, default=18)
    work_days = Column(String(32), nullable=False, default="0,1,2,3,4") # Mon-Fri

class BusinessCalendarHoliday(Base):
    __tablename__ = "business_calendar_holidays"

    holiday_id = Column(String(64), primary_key=True)
    calendar_id = Column(String(32), ForeignKey("business_calendars.calendar_id"), nullable=False)
    holiday_date = Column(String(10), nullable=False) # YYYY-MM-DD
    name = Column(String(128), nullable=False)

class SystemConfiguration(Base):
    __tablename__ = "system_configurations"

    key = Column(String(64), primary_key=True)
    value = Column(String(256), nullable=False)
    description = Column(String(256), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class User(Base):
    __tablename__ = "users"

    user_id = Column(String(64), primary_key=True) # e.g. USR-000001
    email = Column(String(128), unique=True, nullable=False, index=True)
    hashed_password = Column(String(256), nullable=False)
    role = Column(String(32), nullable=False, default="AGENT") # ADMIN, SUPERVISOR, AGENT, ANALYST
    tenant_id = Column(String(64), nullable=False, default="default_tenant", index=True)
    agent_id = Column(String(32), ForeignKey("agents.agent_id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
