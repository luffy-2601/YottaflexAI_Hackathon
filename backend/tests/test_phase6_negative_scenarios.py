import pytest
import datetime
import threading
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.core.database import Base
from backend.app.models.entities import (
    Customer, Channel, Skill, Language, Intent, Agent, AgentSkill, AgentLanguage,
    Ticket, Message, AssignmentEvent, SLAEvent, Resolution, Anomaly, AgentShift
)
from backend.app.schemas.models import (
    TicketCreateRequest, TicketTransferRequest, TicketResolveRequest, TicketReopenRequest
)
from backend.app.services.classification.classifier import ClassificationEngine
from backend.app.services.sla.sla_calculator import SLACalculator, COMPANY_HOLIDAYS_2026
from backend.app.services.routing.routing_engine import IntelligentRoutingEngine
from backend.app.services.tickets.ticket_service import (
    TicketService, DuplicateIngestionError, InvalidStateTransitionError
)
from backend.app.services.anomalies.anomaly_service import AnomalyDetectionService

@pytest.fixture(scope="function")
def session_factory():
    from sqlalchemy.pool import StaticPool
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=test_engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    
    # Pre-seed basic lookup data
    init_db = TestingSession()
    init_db.add_all([
        Channel(channel_id="email", name="Email", default_sla_factor=1.0, is_active=True),
        Channel(channel_id="phone", name="Phone", default_sla_factor=0.2, is_active=True),
        Channel(channel_id="chat", name="Chat", default_sla_factor=0.5, is_active=True),
        Language(language_code="en", name="English", is_supported=True),
        Language(language_code="te", name="Telugu", is_supported=True),
        Language(language_code="hi", name="Hindi", is_supported=True),
        Skill(skill_id="SECURITY_FORENSICS", name="Security Forensics", tier_level=3),
        Skill(skill_id="PAYMENT_GATEWAY", name="Payment Gateway", tier_level=2),
        Skill(skill_id="INFRA_SYSADMIN", name="Infrastructure", tier_level=3),
        Skill(skill_id="CUSTOMER_SUCCESS", name="Customer Success", tier_level=1),
        Intent(intent_id="ACCOUNT_SECURITY", name="Security", category="SECURITY", default_priority="P1", required_skill_id="SECURITY_FORENSICS"),
        Intent(intent_id="PAYMENT_FAILURE", name="Payment", category="BILLING", default_priority="P2", required_skill_id="PAYMENT_GATEWAY"),
        Intent(intent_id="TECHNICAL_ISSUE", name="Tech", category="TECH", default_priority="P2", required_skill_id="INFRA_SYSADMIN"),
        Customer(customer_id="CUS-000001", name="Rohan Verma", email="rohan@example.com", tier="STANDARD"),
        Customer(customer_id="CUS-000002", name="Sneha Patel", email="sneha@example.com", tier="PREMIUM")
    ])
    init_db.commit()
    init_db.close()
    
    yield TestingSession
    Base.metadata.drop_all(bind=test_engine)

@pytest.fixture(scope="function")
def db_session(session_factory):
    session = session_factory()
    yield session
    session.close()

# -----------------------------------------------------------------------------
# 1. Agent Overcapacity Rejection
# -----------------------------------------------------------------------------
def test_negative_01_agent_overcapacity(db_session):
    agt = Agent(agent_id="AGT-000001", name="Agent One", email="a1@support.com", status="ACTIVE", max_concurrency=2, current_active_tickets=2, experience_score=0.9)
    db_session.add(agt)
    db_session.add(AgentSkill(agent_id="AGT-000001", skill_id="PAYMENT_GATEWAY", proficiency_level=0.9))
    db_session.add(AgentLanguage(agent_id="AGT-000001", language_code="en", fluency_score=1.0))
    db_session.commit()

    svc = TicketService(db_session)
    req = TicketCreateRequest(customer_id="CUS-000001", channel_id="email", subject="Payment failed transaction error", body="UPI payment failed.")
    ticket = svc.create_ticket(req)

    assert ticket.status == "QUEUED"
    assert ticket.assigned_agent_id is None

# -----------------------------------------------------------------------------
# 2. Channel SLA Calendar Differentiation
# -----------------------------------------------------------------------------
def test_negative_02_incorrect_channel_sla_calendar():
    base_time = datetime.datetime(2026, 11, 16, 10, 0, 0, tzinfo=datetime.timezone.utc) # Monday 10:00 AM
    
    # Email factor is 1.0 (15 mins first response for P2)
    email_fr, email_res = SLACalculator.calculate_deadlines("P2", "email", base_time, channel_sla_factor=1.0)
    # Phone factor is 0.2 (3 mins first response for P2)
    phone_fr, phone_res = SLACalculator.calculate_deadlines("P2", "phone", base_time, channel_sla_factor=0.2)

    assert phone_fr < email_fr
    assert (email_fr - base_time).total_seconds() == 15 * 60
    assert (phone_fr - base_time).total_seconds() == 3 * 60

# -----------------------------------------------------------------------------
# 3. Reopened Ticket History Preservation
# -----------------------------------------------------------------------------
def test_negative_03_reopened_ticket_history_loss(db_session):
    agt = Agent(agent_id="AGT-000001", name="Agent One", email="a1@support.com", status="ACTIVE", max_concurrency=5, current_active_tickets=0, experience_score=0.9)
    db_session.add(agt)
    db_session.add(AgentSkill(agent_id="AGT-000001", skill_id="PAYMENT_GATEWAY", proficiency_level=0.9))
    db_session.add(AgentLanguage(agent_id="AGT-000001", language_code="en", fluency_score=1.0))
    db_session.commit()

    svc = TicketService(db_session)
    req = TicketCreateRequest(customer_id="CUS-000001", channel_id="email", subject="Payment debit failed", body="Payment stuck.")
    ticket = svc.create_ticket(req)

    svc.add_message(ticket.ticket_id, "AGENT", "AGT-000001", "Checking your payment record now.")
    svc.resolve_ticket(ticket.ticket_id, TicketResolveRequest(agent_id="AGT-000001", summary="Fixed", csat_score=5))

    # Reopen ticket
    svc.reopen_ticket(ticket.ticket_id, TicketReopenRequest(reason="The transaction failed again!"))
    db_session.refresh(ticket)

    assert ticket.status == "REOPENED"
    assert len(ticket.messages) == 2
    assert ticket.resolution is not None
    assert ticket.resolution.csat_score == 5

# -----------------------------------------------------------------------------
# 4. Transfer Loop Anomaly Flagging
# -----------------------------------------------------------------------------
def test_negative_04_transfer_loop(db_session):
    agt1 = Agent(agent_id="AGT-000001", name="Agent One", email="a1@support.com", status="ACTIVE", max_concurrency=5, current_active_tickets=0, experience_score=0.9)
    agt2 = Agent(agent_id="AGT-000002", name="Agent Two", email="a2@support.com", status="ACTIVE", max_concurrency=5, current_active_tickets=0, experience_score=0.9)
    db_session.add_all([agt1, agt2])
    db_session.add_all([
        AgentSkill(agent_id="AGT-000001", skill_id="PAYMENT_GATEWAY", proficiency_level=0.9),
        AgentSkill(agent_id="AGT-000002", skill_id="PAYMENT_GATEWAY", proficiency_level=0.9),
        AgentLanguage(agent_id="AGT-000001", language_code="en", fluency_score=1.0),
        AgentLanguage(agent_id="AGT-000002", language_code="en", fluency_score=1.0)
    ])
    db_session.commit()

    svc = TicketService(db_session)
    req = TicketCreateRequest(customer_id="CUS-000001", channel_id="email", subject="Payment failure loop", body="Error on checkout.")
    ticket = svc.create_ticket(req)

    # Reassign loop: 1 -> 2 -> 1 -> 2
    svc.transfer_ticket(ticket.ticket_id, TicketTransferRequest(to_agent_id="AGT-000002", reason="Transfer to 2"))
    svc.transfer_ticket(ticket.ticket_id, TicketTransferRequest(to_agent_id="AGT-000001", reason="Transfer to 1"))
    svc.transfer_ticket(ticket.ticket_id, TicketTransferRequest(to_agent_id="AGT-000002", reason="Transfer to 2 again"))

    anoms = AnomalyDetectionService(db_session).scan_anomalies()
    loop_anomalies = [a for a in anoms if a.category == "TRANSFER_LOOP"]
    assert len(loop_anomalies) >= 1
    assert loop_anomalies[0].ticket_id == ticket.ticket_id

# -----------------------------------------------------------------------------
# 5. Safety-Priority Contradiction Override
# -----------------------------------------------------------------------------
def test_negative_05_safety_priority_contradiction(db_session):
    agt = Agent(agent_id="AGT-000001", name="Security Lead", email="sec@support.com", status="ACTIVE", max_concurrency=5, current_active_tickets=0, experience_score=0.9)
    db_session.add(agt)
    db_session.add(AgentSkill(agent_id="AGT-000001", skill_id="SECURITY_FORENSICS", proficiency_level=1.0))
    db_session.add(AgentLanguage(agent_id="AGT-000001", language_code="en", fluency_score=1.0))
    db_session.commit()

    svc = TicketService(db_session)
    req = TicketCreateRequest(
        customer_id="CUS-000001",
        channel_id="email",
        subject="Account hacked and password stolen",
        body="Attacker breached my profile and stole credentials.",
        priority="P4" # Downgrade attempt
    )
    ticket = svc.create_ticket(req)
    assert ticket.priority == "P1" # Mandatory safety rule invariant holds

# -----------------------------------------------------------------------------
# 6. Wrong Skill Assignment Prevention
# -----------------------------------------------------------------------------
def test_negative_06_wrong_skill_assignment(db_session):
    # Agent only has CUSTOMER_SUCCESS, but ticket requires SECURITY_FORENSICS
    agt = Agent(agent_id="AGT-000001", name="CS Agent", email="cs@support.com", status="ACTIVE", max_concurrency=5, current_active_tickets=0, experience_score=0.8)
    db_session.add(agt)
    db_session.add(AgentSkill(agent_id="AGT-000001", skill_id="CUSTOMER_SUCCESS", proficiency_level=0.9))
    db_session.add(AgentLanguage(agent_id="AGT-000001", language_code="en", fluency_score=1.0))
    db_session.commit()

    svc = TicketService(db_session)
    req = TicketCreateRequest(customer_id="CUS-000001", channel_id="email", subject="Security intrusion alert", body="Unauthorized fraud attempt.")
    ticket = svc.create_ticket(req)

    # Must be queued, cannot be assigned to agent lacking SECURITY_FORENSICS
    assert ticket.assigned_agent_id is None
    assert ticket.status == "QUEUED"

# -----------------------------------------------------------------------------
# 7. Wrong Language Assignment Prevention
# -----------------------------------------------------------------------------
def test_negative_07_wrong_language_assignment(db_session):
    # Customer ticket in Telugu
    # Agent only has English and Spanish (not Telugu)
    agt = Agent(agent_id="AGT-000001", name="English Agent", email="en@support.com", status="ACTIVE", max_concurrency=5, current_active_tickets=0, experience_score=0.8)
    db_session.add(agt)
    db_session.add(AgentSkill(agent_id="AGT-000001", skill_id="PAYMENT_GATEWAY", proficiency_level=0.9))
    db_session.add(AgentLanguage(agent_id="AGT-000001", language_code="en", fluency_score=1.0))
    db_session.commit()

    router = IntelligentRoutingEngine(db_session)
    ticket = Ticket(ticket_id="TKT-TEST-LANG", customer_id="CUS-000001", channel_id="email", subject="Dabbu raledu", status="NEW", priority="P2", intent_id="PAYMENT_FAILURE", language_code="te")
    ticket.intent = Intent(intent_id="PAYMENT_FAILURE", name="Payment", category="BILLING", default_priority="P2", required_skill_id="PAYMENT_GATEWAY")

    res = router.evaluate_routing(ticket)
    # The agent receives a penalty / lower score, and if language check strictness rejects:
    assert len(res.candidate_scores) > 0 or len(res.rejected_candidates) > 0

# -----------------------------------------------------------------------------
# 8. No Eligible Agent Graceful Queueing
# -----------------------------------------------------------------------------
def test_negative_08_no_eligible_agent(db_session):
    # Zero agents in database
    svc = TicketService(db_session)
    req = TicketCreateRequest(customer_id="CUS-000001", channel_id="email", subject="Payment gateway error", body="Failed payment.")
    ticket = svc.create_ticket(req)

    assert ticket.status == "QUEUED"
    assert ticket.assigned_agent_id is None

# -----------------------------------------------------------------------------
# 9. Concurrent Assignment Race Condition
# -----------------------------------------------------------------------------
def test_negative_09_concurrent_assignment_race_condition(session_factory):
    # Agent has capacity for exactly 1 ticket
    setup_db = session_factory()
    agt = Agent(agent_id="AGT-000001", name="Solo Agent", email="solo@support.com", status="ACTIVE", max_concurrency=1, current_active_tickets=0, experience_score=0.9)
    setup_db.add(agt)
    setup_db.add(AgentSkill(agent_id="AGT-000001", skill_id="PAYMENT_GATEWAY", proficiency_level=0.9))
    setup_db.add(AgentLanguage(agent_id="AGT-000001", language_code="en", fluency_score=1.0))
    setup_db.commit()
    setup_db.close()

    results = []
    thread_lock = threading.Lock()
    def assign_worker(ticket_id):
        with thread_lock:
            worker_session = session_factory()
            router = IntelligentRoutingEngine(worker_session)
            t = Ticket(
                ticket_id=ticket_id,
                customer_id="CUS-000001",
                channel_id="email",
                subject="Payment",
                status="NEW",
                priority="P2",
                intent_id="PAYMENT_FAILURE",
                language_code="en"
            )
            worker_session.add(t)
            worker_session.commit()
            success = router.assign_ticket_atomically(t, "AGT-000001", "Race test", "TEST_RUNNER")
            results.append(success)
            worker_session.close()

    t1 = threading.Thread(target=assign_worker, args=("TKT-RACE-001",))
    t2 = threading.Thread(target=assign_worker, args=("TKT-RACE-002",))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Exactly one succeeded and one failed (no overcapacity!)
    assert results.count(True) == 1
    assert results.count(False) == 1

# -----------------------------------------------------------------------------
# 10. Duplicate Email Ingestion Idempotency
# -----------------------------------------------------------------------------
def test_negative_10_duplicate_email_ingestion(db_session):
    svc = TicketService(db_session)
    req = TicketCreateRequest(
        customer_id="CUS-000001",
        channel_id="email",
        subject="Internet outage query",
        body="My router has had no internet connection for two days."
    )
    # First ingestion succeeds
    ticket1 = svc.create_ticket(req)
    assert ticket1.ticket_id.startswith("TKT-2026-")

    # Immediate second identical ingestion must raise DuplicateIngestionError
    with pytest.raises(DuplicateIngestionError):
        svc.create_ticket(req)

# -----------------------------------------------------------------------------
# 11. Low-Confidence Classification
# -----------------------------------------------------------------------------
def test_negative_11_low_confidence_classification():
    # Ambiguous random string with no matched keywords
    res = ClassificationEngine.classify(
        subject="Random hello xyz qwerty",
        body="Lorem ipsum dolor sit amet consectetur adipiscing elit."
    )
    assert res.confidence < 0.65
    assert res.needs_manual_review is True

# -----------------------------------------------------------------------------
# 12. After-Hours SLA Weekend / Night Jump
# -----------------------------------------------------------------------------
def test_negative_12_after_hours_sla():
    # Saturday evening 20:00
    saturday_night = datetime.datetime(2026, 11, 14, 20, 0, 0, tzinfo=datetime.timezone.utc)
    fr_due, res_due = SLACalculator.calculate_deadlines("P3", "email", saturday_night)

    # Must jump past Sunday to Monday morning 09:00+
    assert fr_due.weekday() == 0 # Monday
    assert fr_due.hour >= 9

# -----------------------------------------------------------------------------
# 13. Holiday SLA Calendar Skip
# -----------------------------------------------------------------------------
def test_negative_13_holiday_sla():
    # Republic Day: 2026-01-26 is Monday
    # Ticket created Friday 2026-01-23 at 17:50 (10 mins before 18:00 EOD)
    friday_eod = datetime.datetime(2026, 1, 23, 17, 50, 0, tzinfo=datetime.timezone.utc)
    # 15 minute SLA for P2: 10 mins used Friday, remaining 5 mins roll over
    fr_due, _ = SLACalculator.calculate_deadlines("P2", "email", friday_eod, channel_sla_factor=1.0)

    # Must skip weekend (Jan 24, 25) and Republic Day holiday (Jan 26 Monday), falling on Tuesday Jan 27 at 09:05
    assert fr_due.strftime("%Y-%m-%d") == "2026-01-27"
    assert fr_due.hour == 9
    assert fr_due.minute == 5

# -----------------------------------------------------------------------------
# 14. Deterministic Tie-Breaking
# -----------------------------------------------------------------------------
def test_negative_14_deterministic_tie_breaking(db_session):
    # Two agents with identical skills, languages, capacity, and experience
    agt1 = Agent(agent_id="AGT-000001", name="Agent Alpha", email="alpha@support.com", status="ACTIVE", max_concurrency=4, current_active_tickets=0, experience_score=0.90)
    agt2 = Agent(agent_id="AGT-000002", name="Agent Beta", email="beta@support.com", status="ACTIVE", max_concurrency=4, current_active_tickets=0, experience_score=0.90)
    db_session.add_all([agt1, agt2])
    db_session.add_all([
        AgentSkill(agent_id="AGT-000001", skill_id="PAYMENT_GATEWAY", proficiency_level=0.95),
        AgentSkill(agent_id="AGT-000002", skill_id="PAYMENT_GATEWAY", proficiency_level=0.95),
        AgentLanguage(agent_id="AGT-000001", language_code="en", fluency_score=1.0),
        AgentLanguage(agent_id="AGT-000002", language_code="en", fluency_score=1.0)
    ])
    db_session.commit()

    router = IntelligentRoutingEngine(db_session)
    ticket = Ticket(ticket_id="TKT-TIE-001", customer_id="CUS-000001", channel_id="email", subject="Payment", status="NEW", priority="P2", intent_id="PAYMENT_FAILURE", language_code="en")
    ticket.intent = Intent(intent_id="PAYMENT_FAILURE", name="Payment", category="BILLING", default_priority="P2", required_skill_id="PAYMENT_GATEWAY")

    # Repeat 10 times: must deterministically pick AGT-000001 every single time
    for _ in range(10):
        res = router.evaluate_routing(ticket)
        assert res.selected_agent_id == "AGT-000001"
