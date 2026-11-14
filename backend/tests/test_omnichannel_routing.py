import pytest
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.core.database import Base
from backend.app.models.entities import (
    Customer, Channel, Skill, Language, Intent, Agent, AgentSkill, AgentLanguage,
    Ticket, Message, AssignmentEvent, SLAEvent, Resolution, PriorityRule
)
from backend.app.schemas.models import (
    TicketCreateRequest, TicketTransferRequest, TicketEscalateRequest,
    TicketReopenRequest, TicketResolveRequest
)
from backend.app.services.classification.classifier import ClassificationEngine
from backend.app.services.sla.sla_calculator import SLACalculator
from backend.app.services.routing.routing_engine import IntelligentRoutingEngine
from backend.app.services.tickets.ticket_service import TicketService
from backend.app.services.anomalies.anomaly_service import AnomalyDetectionService
from backend.app.services.analytics.analytics_service import AnalyticsService
from backend.app.services.evaluation.benchmark_service import EvaluationBenchmarkService

# Test Database Fixture
@pytest.fixture(scope="function")
def db_session():
    test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()

    # Seed minimal baseline fixtures
    ch_email = Channel(channel_id="email", name="Email", default_sla_factor=1.0, is_active=True)
    ch_phone = Channel(channel_id="phone", name="Phone", default_sla_factor=0.2, is_active=True)
    ch_chat = Channel(channel_id="chat", name="Chat", default_sla_factor=0.5, is_active=True)
    session.add_all([ch_email, ch_phone, ch_chat])

    l_en = Language(language_code="en", name="English", is_supported=True)
    l_te = Language(language_code="te", name="Telugu", is_supported=True)
    l_hi = Language(language_code="hi", name="Hindi", is_supported=True)
    session.add_all([l_en, l_te, l_hi])

    sk_sec = Skill(skill_id="SECURITY_FORENSICS", name="Security", tier_level=3)
    sk_pay = Skill(skill_id="PAYMENT_GATEWAY", name="Payment Gateway", tier_level=2)
    session.add_all([sk_sec, sk_pay])

    i_sec = Intent(intent_id="ACCOUNT_SECURITY", name="Security", category="SECURITY", default_priority="P1", required_skill_id="SECURITY_FORENSICS")
    i_pay = Intent(intent_id="PAYMENT_FAILURE", name="Payment", category="BILLING", default_priority="P2", required_skill_id="PAYMENT_GATEWAY")
    session.add_all([i_sec, i_pay])

    cus = Customer(customer_id="CUS-000001", name="Test Customer", email="test@example.com", tier="STANDARD")
    session.add(cus)

    # Agent 1: Payment + English + Telugu (Capacity 2)
    agt1 = Agent(agent_id="AGT-000001", name="Aarav Sharma", email="aarav@support.com", status="ACTIVE", max_concurrency=2, current_active_tickets=0, experience_score=0.90)
    session.add(agt1)
    session.flush()

    session.add(AgentSkill(agent_id="AGT-000001", skill_id="PAYMENT_GATEWAY", proficiency_level=0.95))
    session.add(AgentLanguage(agent_id="AGT-000001", language_code="en", fluency_score=1.0))
    session.add(AgentLanguage(agent_id="AGT-000001", language_code="te", fluency_score=0.90))

    # Agent 2: Security + English (Capacity 2)
    agt2 = Agent(agent_id="AGT-000002", name="Priya Rao", email="priya@support.com", status="ACTIVE", max_concurrency=2, current_active_tickets=0, experience_score=0.95)
    session.add(agt2)
    session.flush()

    session.add(AgentSkill(agent_id="AGT-000002", skill_id="SECURITY_FORENSICS", proficiency_level=1.0))
    session.add(AgentLanguage(agent_id="AGT-000002", language_code="en", fluency_score=1.0))

    session.commit()
    yield session
    session.close()

# 1. Normal Ticket Assignment
def test_normal_ticket_assignment(db_session):
    svc = TicketService(db_session)
    req = TicketCreateRequest(
        customer_id="CUS-000001",
        channel_id="email",
        subject="Payment failed at checkout UPI error",
        body="Money deducted from my account but order is pending."
    )
    ticket = svc.create_ticket(req)
    assert ticket.ticket_id.startswith("TKT-2026-")
    assert ticket.assigned_agent_id == "AGT-000001"
    assert ticket.status == "ASSIGNED"
    assert ticket.priority == "P2"
    # Agent capacity incremented
    agt = db_session.query(Agent).filter(Agent.agent_id == "AGT-000001").first()
    assert agt.current_active_tickets == 1

# 2. Language-Compatible Assignment
def test_language_compatible_assignment(db_session):
    svc = TicketService(db_session)
    # Telugu keyword triggers Telugu detection
    req = TicketCreateRequest(
        customer_id="CUS-000001",
        channel_id="chat",
        subject="UPI payment failure",
        body="Nenu payment chesanu kani failed ani vachindi sahayam cheyandi."
    )
    ticket = svc.create_ticket(req)
    assert ticket.language_code == "te"
    assert ticket.assigned_agent_id == "AGT-000001" # Only AGT-000001 speaks Telugu

# 3. Missing Required Skill
def test_missing_required_skill_rejects(db_session):
    # Disable Agent 2 who has SECURITY_FORENSICS
    agt2 = db_session.query(Agent).filter(Agent.agent_id == "AGT-000002").first()
    agt2.status = "INACTIVE"
    db_session.commit()

    svc = TicketService(db_session)
    req = TicketCreateRequest(
        customer_id="CUS-000001",
        channel_id="email",
        subject="Account security stolen credentials",
        body="Hacked account credentials stolen password compromised."
    )
    ticket = svc.create_ticket(req)
    # AGT-000001 lacks SECURITY_FORENSICS skill, so ticket must be QUEUED
    assert ticket.assigned_agent_id is None
    assert ticket.status == "QUEUED"

# 4. Agent At Capacity
def test_agent_at_capacity(db_session):
    agt1 = db_session.query(Agent).filter(Agent.agent_id == "AGT-000001").first()
    agt1.current_active_tickets = 2 # Max is 2
    db_session.commit()

    svc = TicketService(db_session)
    req = TicketCreateRequest(
        customer_id="CUS-000001",
        channel_id="email",
        subject="Payment failed again",
        body="Card rejected transaction error."
    )
    ticket = svc.create_ticket(req)
    # AGT-000001 is full, AGT-000002 lacks skill -> QUEUED
    assert ticket.assigned_agent_id is None
    assert ticket.status == "QUEUED"

# 5. No Eligible Agent Handling
def test_no_eligible_agent_recorded(db_session):
    for agt in db_session.query(Agent).all():
        agt.status = "INACTIVE"
    db_session.commit()

    svc = TicketService(db_session)
    req = TicketCreateRequest(
        customer_id="CUS-000001",
        channel_id="email",
        subject="Payment failed",
        body="Payment declined."
    )
    ticket = svc.create_ticket(req)
    assert ticket.status == "QUEUED"
    assert ticket.assigned_agent_id is None

# 6. Critical Security Incident Forces P1
def test_critical_security_incident_priority(db_session):
    svc = TicketService(db_session)
    req = TicketCreateRequest(
        customer_id="CUS-000001",
        channel_id="email",
        subject="Urgent: Account hacked and credentials stolen",
        body="Unauthorized login from foreign country, stolen password, data breach."
    )
    ticket = svc.create_ticket(req)
    assert ticket.priority == "P1"
    assert ticket.intent_id == "ACCOUNT_SECURITY"
    assert ticket.assigned_agent_id == "AGT-000002"

# 7. After-Hours Ticket SLA
def test_after_hours_ticket_sla(db_session):
    # Sunday at 22:00 UTC
    sunday_dt = datetime.datetime(2026, 11, 15, 22, 0, 0, tzinfo=datetime.timezone.utc)
    first_resp_due, resol_due = SLACalculator.calculate_deadlines(
        priority="P2",
        channel_id="email",
        created_at=sunday_dt
    )
    # For P2, must jump weekend to Monday 09:00+
    assert first_resp_due.weekday() == 0 # Monday
    assert first_resp_due.hour >= 9

# 8. SLA Warning & Countdown
def test_sla_active_countdown(db_session):
    svc = TicketService(db_session)
    req = TicketCreateRequest(
        customer_id="CUS-000001",
        channel_id="email",
        subject="Payment failed",
        body="Declined transaction."
    )
    ticket = svc.create_ticket(req)
    sla = db_session.query(SLAEvent).filter(SLAEvent.ticket_id == ticket.ticket_id).first()
    assert sla is not None
    assert sla.status == "RUNNING"
    assert sla.first_response_due_at > ticket.created_at

# 9. SLA Breach Recording
def test_sla_breach_recording(db_session):
    svc = TicketService(db_session)
    req = TicketCreateRequest(
        customer_id="CUS-000001",
        channel_id="email",
        subject="Payment duplicate",
        body="Charged twice double debit."
    )
    ticket = svc.create_ticket(req)
    sla = db_session.query(SLAEvent).filter(SLAEvent.ticket_id == ticket.ticket_id).first()
    # Backdate SLA due date to simulate breach
    sla.first_response_due_at = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=2)
    db_session.commit()

    # Agent responds now
    svc.add_message(ticket.ticket_id, "AGENT", "AGT-000001", "Hello, I am checking your double charge.")
    db_session.refresh(sla)
    assert sla.is_first_response_breached is True

# 10. Agent Transfer
def test_agent_transfer(db_session):
    svc = TicketService(db_session)
    req = TicketCreateRequest(
        customer_id="CUS-000001",
        channel_id="email",
        subject="Payment failed at checkout transaction declined",
        body="Money deducted from my account but order is pending."
    )
    ticket = svc.create_ticket(req)
    assert ticket.assigned_agent_id == "AGT-000001"

    # Transfer to AGT-000002
    svc.transfer_ticket(ticket.ticket_id, TicketTransferRequest(to_agent_id="AGT-000002", reason="Need senior review"))
    db_session.refresh(ticket)
    assert ticket.assigned_agent_id == "AGT-000002"
    # Event logged
    asns = db_session.query(AssignmentEvent).filter(AssignmentEvent.ticket_id == ticket.ticket_id).all()
    assert len(asns) == 2
    assert asns[1].event_type == "TRANSFER"

# 11. Transfer Loop Anomaly Flagging
def test_transfer_loop_anomaly(db_session):
    svc = TicketService(db_session)
    req = TicketCreateRequest(customer_id="CUS-000001", channel_id="email", subject="Payment failed loop", body="Transaction declined error.")
    ticket = svc.create_ticket(req)

    # Ping-pong transfers: 1 -> 2 -> 1 -> 2
    svc.transfer_ticket(ticket.ticket_id, TicketTransferRequest(to_agent_id="AGT-000002", reason="to 2"))
    svc.transfer_ticket(ticket.ticket_id, TicketTransferRequest(to_agent_id="AGT-000001", reason="back to 1"))
    svc.transfer_ticket(ticket.ticket_id, TicketTransferRequest(to_agent_id="AGT-000002", reason="back to 2"))

    anom_svc = AnomalyDetectionService(db_session)
    anoms = anom_svc.scan_anomalies()
    loop_anoms = [a for a in anoms if a.category == "TRANSFER_LOOP"]
    assert len(loop_anoms) >= 1

# 12. Ticket Reopening Preserves History
def test_ticket_reopening_preserves_history(db_session):
    svc = TicketService(db_session)
    req = TicketCreateRequest(customer_id="CUS-000001", channel_id="email", subject="Payment failed fix", body="Please fix payment failed.")
    ticket = svc.create_ticket(req)
    svc.add_message(ticket.ticket_id, "AGENT", "AGT-000001", "Fixed your payment.")
    svc.resolve_ticket(ticket.ticket_id, TicketResolveRequest(agent_id="AGT-000001", summary="Resolved", csat_score=5))

    # Reopen ticket
    svc.reopen_ticket(ticket.ticket_id, TicketReopenRequest(reason="Issue recurred today!"))
    db_session.refresh(ticket)
    assert ticket.status == "REOPENED"
    # Historical messages and resolutions preserved!
    assert len(ticket.messages) == 2
    assert ticket.resolution is not None
    assert ticket.resolution.csat_score == 5

# 13. Priority Safety Override Invariant
def test_priority_safety_override_invariant(db_session):
    # Attempting to create an Account Compromise ticket with P4 priority override
    svc = TicketService(db_session)
    req = TicketCreateRequest(
        customer_id="CUS-000001",
        channel_id="email",
        subject="Account hacked and password stolen",
        body="Unauthorized login credentials stolen.",
        priority="P4" # Downgrade attempt
    )
    ticket = svc.create_ticket(req)
    # Safety invariant must enforce P1 regardless of request override
    assert ticket.priority == "P1"

# 14. Resolution and CSAT Tracking
def test_ticket_resolution_and_csat(db_session):
    svc = TicketService(db_session)
    req = TicketCreateRequest(customer_id="CUS-000001", channel_id="email", subject="Payment failed transaction declined", body="Money deducted.")
    ticket = svc.create_ticket(req)
    agt = db_session.query(Agent).filter(Agent.agent_id == "AGT-000001").first()
    assert agt.current_active_tickets == 1

    svc.resolve_ticket(ticket.ticket_id, TicketResolveRequest(
        agent_id="AGT-000001",
        resolution_code="SOLVED",
        summary="Transaction reprocessed",
        csat_score=5,
        csat_feedback="Fast service!"
    ))
    db_session.refresh(ticket)
    db_session.refresh(agt)
    assert ticket.status == "RESOLVED"
    assert agt.current_active_tickets == 0 # Capacity released

# 15. Operational Analytics Correctness
def test_operational_analytics_correctness(db_session):
    analytics = AnalyticsService(db_session)
    res = analytics.get_operations_overview()
    assert "total_tickets" in res
    assert "open_tickets" in res
    assert "sla_compliance_pct" in res
    assert res["active_agents"] == 2

# 16. Benchmark Comparison Strategy
def test_benchmark_comparison_strategy(db_session):
    bench = EvaluationBenchmarkService(db_session)
    res = bench.run_benchmark(sample_limit=10)
    assert "round_robin" in res.strategies
    assert "skill_based" in res.strategies
    assert "intelligent" in res.strategies
    # Intelligent routing must yield 0% capacity violations
    assert res.strategies["intelligent"].capacity_violation_rate == 0.0
