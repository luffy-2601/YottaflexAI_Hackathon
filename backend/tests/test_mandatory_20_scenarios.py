import pytest
import datetime
import threading
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.app.core.database import Base
from backend.app.models.entities import (
    Customer, Channel, Skill, Language, Intent, Agent, AgentSkill, AgentLanguage,
    Ticket, Message, AssignmentEvent, SLAEvent, SLAHistoryEvent, Resolution, Anomaly, SLAPolicy
)
from backend.app.schemas.models import (
    TicketCreateRequest, TicketTransferRequest, TicketResolveRequest, TicketReopenRequest,
    SLAPauseRequest, SLAResumeRequest
)
from backend.app.services.classification.classifier import ClassificationEngine
from backend.app.services.sla.sla_calculator import SLACalculator
from backend.app.services.sla.sla_engine import SLAEngine, UnauthorizedPauseError
from backend.app.services.routing.routing_engine import IntelligentRoutingEngine
from backend.app.services.tickets.ticket_service import (
    TicketService, DuplicateIngestionError, InvalidStateTransitionError
)
from backend.app.services.anomalies.anomaly_service import AnomalyDetectionService

@pytest.fixture(scope="function")
def session_factory():
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=test_engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    
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
        Customer(customer_id="CUS-000001", tenant_id="default_tenant", name="Rohan Verma", email="rohan@example.com", tier="STANDARD"),
        Customer(customer_id="CUS-000002", tenant_id="jio_demo", name="Jio Customer", email="jio@example.com", tier="VIP")
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
# 1. Wrong skill must reject an agent
# -----------------------------------------------------------------------------
def test_01_wrong_skill_rejects_agent(db_session):
    agt = Agent(agent_id="AGT-000001", tenant_id="default_tenant", name="CS Agent", email="cs@test.com", status="ACTIVE", max_concurrency=3, current_active_tickets=0)
    db_session.add(agt)
    db_session.add(AgentSkill(agent_id="AGT-000001", skill_id="CUSTOMER_SUCCESS", proficiency_level=0.9))
    db_session.add(AgentLanguage(agent_id="AGT-000001", language_code="en", fluency_score=1.0))
    db_session.commit()

    svc = TicketService(db_session)
    req = TicketCreateRequest(customer_id="CUS-000001", channel_id="email", subject="Security intrusion hacked credentials", body="Compromised account.")
    ticket = svc.create_ticket(req)

    assert ticket.assigned_agent_id is None
    assert ticket.status == "QUEUED"

# -----------------------------------------------------------------------------
# 2. Insufficient language proficiency must reject an agent
# -----------------------------------------------------------------------------
def test_02_insufficient_language_proficiency_rejects(db_session):
    agt = Agent(agent_id="AGT-000001", tenant_id="default_tenant", name="English Agent", email="en@test.com", status="ACTIVE", max_concurrency=3, current_active_tickets=0)
    db_session.add(agt)
    db_session.add(AgentSkill(agent_id="AGT-000001", skill_id="PAYMENT_GATEWAY", proficiency_level=0.95))
    db_session.add(AgentLanguage(agent_id="AGT-000001", language_code="en", fluency_score=1.0))
    db_session.commit()

    router = IntelligentRoutingEngine(db_session)
    t = Ticket(ticket_id="TKT-LANG-01", tenant_id="default_tenant", customer_id="CUS-000001", channel_id="chat", subject="Dabbu raledu", status="NEW", priority="P2", intent_id="PAYMENT_FAILURE", language_code="te")
    t.intent = Intent(intent_id="PAYMENT_FAILURE", name="Payment", category="BILLING", default_priority="P2", required_skill_id="PAYMENT_GATEWAY")

    res = router.evaluate_routing(t)
    # Telugu is required; AGT-000001 has no Telugu
    assert res.selected_agent_id is None or any(r.agent_id == "AGT-000001" for r in res.rejected_candidates)

# -----------------------------------------------------------------------------
# 3. Full capacity must prevent assignment
# -----------------------------------------------------------------------------
def test_03_full_capacity_prevents_assignment(db_session):
    agt = Agent(agent_id="AGT-000001", tenant_id="default_tenant", name="Full Agent", email="full@test.com", status="ACTIVE", max_concurrency=2, current_active_tickets=2)
    db_session.add(agt)
    db_session.add(AgentSkill(agent_id="AGT-000001", skill_id="PAYMENT_GATEWAY", proficiency_level=0.95))
    db_session.add(AgentLanguage(agent_id="AGT-000001", language_code="en", fluency_score=1.0))
    db_session.commit()

    svc = TicketService(db_session)
    req = TicketCreateRequest(customer_id="CUS-000001", channel_id="email", subject="Payment failure", body="Transaction declined.")
    t = svc.create_ticket(req)

    assert t.status == "QUEUED"
    assert t.assigned_agent_id is None

# -----------------------------------------------------------------------------
# 4. Simultaneous ticket assignments must not exceed agent capacity
# -----------------------------------------------------------------------------
def test_04_simultaneous_assignment_concurrency_safe(session_factory):
    setup_db = session_factory()
    agt = Agent(agent_id="AGT-000001", tenant_id="default_tenant", name="Solo Agent", email="solo@test.com", status="ACTIVE", max_concurrency=1, current_active_tickets=0)
    setup_db.add(agt)
    setup_db.add(AgentSkill(agent_id="AGT-000001", skill_id="PAYMENT_GATEWAY", proficiency_level=0.95))
    setup_db.add(AgentLanguage(agent_id="AGT-000001", language_code="en", fluency_score=1.0))
    setup_db.commit()
    setup_db.close()

    results = []
    def assign_worker(ticket_id):
        sess = session_factory()
        router = IntelligentRoutingEngine(sess)
        t = Ticket(ticket_id=ticket_id, tenant_id="default_tenant", customer_id="CUS-000001", channel_id="email", subject="Payment", status="NEW", priority="P2", intent_id="PAYMENT_FAILURE", language_code="en")
        sess.add(t)
        sess.commit()
        success = router.assign_ticket_atomically(t, "AGT-000001", "Concurrency test", "TEST")
        results.append(success)
        sess.close()

    t1 = threading.Thread(target=assign_worker, args=("TKT-C1",))
    t2 = threading.Thread(target=assign_worker, args=("TKT-C2",))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert results.count(True) == 1
    assert results.count(False) == 1

# -----------------------------------------------------------------------------
# 5. No eligible agent must create a queued ticket
# -----------------------------------------------------------------------------
def test_05_no_eligible_agent_creates_queued_ticket(db_session):
    svc = TicketService(db_session)
    req = TicketCreateRequest(customer_id="CUS-000001", channel_id="email", subject="Payment failure", body="Declined.")
    t = svc.create_ticket(req)

    assert t.status == "QUEUED"
    assert t.assigned_agent_id is None

# -----------------------------------------------------------------------------
# 6. Business-hour SLA calculation must be correct
# -----------------------------------------------------------------------------
def test_06_business_hour_sla_calculation_correctness():
    monday_10am = datetime.datetime(2026, 11, 16, 10, 0, 0, tzinfo=datetime.timezone.utc)
    fr_due, res_due = SLACalculator.calculate_deadlines("P2", "email", monday_10am, channel_sla_factor=1.0)

    # P2 first response is 15 business minutes (10:15 AM)
    assert fr_due == monday_10am + datetime.timedelta(minutes=15)
    # P2 resolution is 240 business minutes (4 hours = 14:00 PM)
    assert res_due == monday_10am + datetime.timedelta(hours=4)

# -----------------------------------------------------------------------------
# 7. Weekend and holiday calculation must be correct
# -----------------------------------------------------------------------------
def test_07_weekend_and_holiday_sla_calculation():
    # Friday 2026-01-23 17:50 (10 minutes before 18:00 close). 2026-01-26 is Republic Day holiday.
    friday_eod = datetime.datetime(2026, 1, 23, 17, 50, 0, tzinfo=datetime.timezone.utc)
    fr_due, _ = SLACalculator.calculate_deadlines("P2", "email", friday_eod, channel_sla_factor=1.0)

    # Skips weekend (Jan 24, 25), skips Republic Day (Jan 26), lands on Tuesday Jan 27 at 09:05
    assert fr_due.strftime("%Y-%m-%d") == "2026-01-27"
    assert fr_due.hour == 9
    assert fr_due.minute == 5

# -----------------------------------------------------------------------------
# 8. After-hours ticket deadline must be correct
# -----------------------------------------------------------------------------
def test_08_after_hours_ticket_deadline_advancement():
    # Arrives at 22:00 (after-hours) on Monday
    mon_night = datetime.datetime(2026, 11, 16, 22, 0, 0, tzinfo=datetime.timezone.utc)
    fr_due, _ = SLACalculator.calculate_deadlines("P2", "email", mon_night, channel_sla_factor=1.0)

    # Must start counting from Tuesday 09:00 + 15 mins = 09:15 AM
    assert fr_due.strftime("%Y-%m-%d") == "2026-11-17"
    assert fr_due.hour == 9
    assert fr_due.minute == 15

# -----------------------------------------------------------------------------
# 9. Automated acknowledgement must not count as a human response
# -----------------------------------------------------------------------------
def test_09_automated_ack_does_not_stop_first_response_clock(db_session):
    svc = TicketService(db_session)
    req = TicketCreateRequest(customer_id="CUS-000001", channel_id="email", subject="Payment failure", body="Declined transaction.")
    t = svc.create_ticket(req)

    # Ingest automated acknowledgment message
    svc.add_message(t.ticket_id, "SYSTEM", "AUTO_BOT", "Thank you, we have received your request.")
    
    sla = db_session.query(SLAEvent).filter(SLAEvent.ticket_id == t.ticket_id).first()
    # First response clock must still be RUNNING and not stopped!
    assert sla.first_response_clock_stopped_at is None
    assert sla.first_response_actual_at is None

# -----------------------------------------------------------------------------
# 10. Transfer must not reset the SLA
# -----------------------------------------------------------------------------
def test_10_agent_transfer_preserves_sla_deadlines(db_session):
    agt1 = Agent(agent_id="AGT-000001", tenant_id="default_tenant", name="A1", email="a1@test.com", status="ACTIVE", max_concurrency=5, current_active_tickets=0)
    agt2 = Agent(agent_id="AGT-000002", tenant_id="default_tenant", name="A2", email="a2@test.com", status="ACTIVE", max_concurrency=5, current_active_tickets=0)
    db_session.add_all([agt1, agt2])
    db_session.add_all([
        AgentSkill(agent_id="AGT-000001", skill_id="PAYMENT_GATEWAY", proficiency_level=0.9),
        AgentSkill(agent_id="AGT-000002", skill_id="PAYMENT_GATEWAY", proficiency_level=0.9),
        AgentLanguage(agent_id="AGT-000001", language_code="en", fluency_score=1.0),
        AgentLanguage(agent_id="AGT-000002", language_code="en", fluency_score=1.0)
    ])
    db_session.commit()

    svc = TicketService(db_session)
    req = TicketCreateRequest(customer_id="CUS-000001", channel_id="email", subject="Payment failed at checkout", body="Order failed.")
    t = svc.create_ticket(req)
    
    sla_before = db_session.query(SLAEvent).filter(SLAEvent.ticket_id == t.ticket_id).first()
    original_due = sla_before.resolution_due_at

    # Transfer ticket
    svc.transfer_ticket(t.ticket_id, TicketTransferRequest(to_agent_id="AGT-000002", reason="Need Tier 2 review"))
    
    sla_after = db_session.query(SLAEvent).filter(SLAEvent.ticket_id == t.ticket_id).first()
    # SLA deadline must remain unchanged upon transfer
    assert sla_after.resolution_due_at == original_due

# -----------------------------------------------------------------------------
# 11. Permitted pause must stop eligible SLA time
# -----------------------------------------------------------------------------
def test_11_permitted_pause_stops_sla_and_extends_deadline(db_session):
    engine = SLAEngine(db_session)
    t = Ticket(ticket_id="TKT-PAUSE-01", tenant_id="default_tenant", customer_id="CUS-000001", channel_id="email", subject="Waiting", status="IN_PROGRESS", priority="P2", intent_id="PAYMENT_FAILURE")
    db_session.add(t)
    db_session.commit()

    sla = engine.create_sla_for_ticket(t)
    orig_due = sla.resolution_due_at

    # Pause for authorized reason
    engine.pause_sla(t.ticket_id, SLAPauseRequest(reason="WAITING_FOR_CUSTOMER", authorized_by="AGENT_01"))
    db_session.refresh(sla)
    assert sla.is_paused is True
    assert sla.status == "PAUSED"

    # Resume SLA
    engine.resume_sla(t.ticket_id, SLAResumeRequest(authorized_by="AGENT_01"))
    db_session.refresh(sla)
    assert sla.is_paused is False
    assert sla.status == "RUNNING"
    from backend.app.services.sla.sla_engine import ensure_utc
    assert ensure_utc(sla.resolution_due_at) >= ensure_utc(orig_due)

# -----------------------------------------------------------------------------
# 12. Unauthorized pause must be rejected
# -----------------------------------------------------------------------------
def test_12_unauthorized_pause_is_rejected(db_session):
    engine = SLAEngine(db_session)
    t = Ticket(ticket_id="TKT-PAUSE-02", tenant_id="default_tenant", customer_id="CUS-000001", channel_id="email", subject="Arbitrary pause", status="IN_PROGRESS", priority="P2", intent_id="PAYMENT_FAILURE")
    db_session.add(t)
    db_session.commit()
    engine.create_sla_for_ticket(t)

    # Unauthorized pause reason should raise UnauthorizedPauseError
    with pytest.raises(UnauthorizedPauseError):
        engine.pause_sla(t.ticket_id, SLAPauseRequest(reason="GOING_TO_LUNCH", authorized_by="AGENT_01"))

# -----------------------------------------------------------------------------
# 13. Reopening must preserve history
# -----------------------------------------------------------------------------
def test_13_reopening_preserves_history(db_session):
    agt = Agent(agent_id="AGT-000001", tenant_id="default_tenant", name="A1", email="a1@test.com", status="ACTIVE", max_concurrency=5, current_active_tickets=0)
    db_session.add(agt)
    db_session.add(AgentSkill(agent_id="AGT-000001", skill_id="PAYMENT_GATEWAY", proficiency_level=0.9))
    db_session.add(AgentLanguage(agent_id="AGT-000001", language_code="en", fluency_score=1.0))
    db_session.commit()

    svc = TicketService(db_session)
    t = svc.create_ticket(TicketCreateRequest(customer_id="CUS-000001", channel_id="email", subject="Payment fix", body="Debit error."))
    svc.add_message(t.ticket_id, "AGENT", "AGT-000001", "Fixed your payment.")
    svc.resolve_ticket(t.ticket_id, TicketResolveRequest(agent_id="AGT-000001", summary="Done", csat_score=5))

    svc.reopen_ticket(t.ticket_id, TicketReopenRequest(reason="Recurred today."))
    db_session.refresh(t)

    assert t.status == "REOPENED"
    assert len(t.messages) == 2
    assert t.resolution is not None
    assert t.resolution.csat_score == 5

# -----------------------------------------------------------------------------
# 14. Transfer loop must be detected
# -----------------------------------------------------------------------------
def test_14_transfer_loop_detected(db_session):
    agt1 = Agent(agent_id="AGT-000001", tenant_id="default_tenant", name="A1", email="a1@test.com", status="ACTIVE", max_concurrency=5, current_active_tickets=0)
    agt2 = Agent(agent_id="AGT-000002", tenant_id="default_tenant", name="A2", email="a2@test.com", status="ACTIVE", max_concurrency=5, current_active_tickets=0)
    db_session.add_all([agt1, agt2])
    db_session.add_all([
        AgentSkill(agent_id="AGT-000001", skill_id="PAYMENT_GATEWAY", proficiency_level=0.9),
        AgentSkill(agent_id="AGT-000002", skill_id="PAYMENT_GATEWAY", proficiency_level=0.9),
        AgentLanguage(agent_id="AGT-000001", language_code="en", fluency_score=1.0),
        AgentLanguage(agent_id="AGT-000002", language_code="en", fluency_score=1.0)
    ])
    db_session.commit()

    svc = TicketService(db_session)
    t = svc.create_ticket(TicketCreateRequest(customer_id="CUS-000001", channel_id="email", subject="Payment loop", body="Error."))

    svc.transfer_ticket(t.ticket_id, TicketTransferRequest(to_agent_id="AGT-000002", reason="To 2"))
    svc.transfer_ticket(t.ticket_id, TicketTransferRequest(to_agent_id="AGT-000001", reason="Back to 1"))
    svc.transfer_ticket(t.ticket_id, TicketTransferRequest(to_agent_id="AGT-000002", reason="To 2 again"))

    anoms = AnomalyDetectionService(db_session).scan_anomalies()
    assert any(a.category == "TRANSFER_LOOP" for a in anoms)

# -----------------------------------------------------------------------------
# 15. Duplicate ingestion must not create duplicate tickets
# -----------------------------------------------------------------------------
def test_15_duplicate_ingestion_prevents_duplicate_tickets(db_session):
    svc = TicketService(db_session)
    req = TicketCreateRequest(customer_id="CUS-000001", channel_id="email", subject="No internet issue", body="Broadband down for 2 days.")
    svc.create_ticket(req)

    with pytest.raises(DuplicateIngestionError):
        svc.create_ticket(req)

# -----------------------------------------------------------------------------
# 16. Low-confidence analysis must trigger manual review
# -----------------------------------------------------------------------------
def test_16_low_confidence_triggers_manual_review():
    res = ClassificationEngine.classify(subject="Unclear hello", body="Asdfghjk qwertyuiop zxcvbnm.")
    assert res.confidence < 0.65
    assert res.needs_manual_review is True

# -----------------------------------------------------------------------------
# 17. Safety-priority rules must override ordinary recommendations
# -----------------------------------------------------------------------------
def test_17_safety_priority_rules_override_recommendations(db_session):
    svc = TicketService(db_session)
    req = TicketCreateRequest(
        customer_id="CUS-000001",
        channel_id="email",
        subject="Account hacked and password stolen",
        body="Attacker breached system.",
        priority="P4" # Downgrade attempt
    )
    t = svc.create_ticket(req)
    # Forced P1 invariant
    assert t.priority == "P1"

# -----------------------------------------------------------------------------
# 18. Cross-tenant access must be rejected
# -----------------------------------------------------------------------------
def test_18_cross_tenant_access_isolation(db_session):
    # Agent belongs to "amazon_demo", ticket belongs to "jio_demo"
    agt = Agent(agent_id="AGT-AMZ-01", tenant_id="amazon_demo", name="Amazon Lead", email="amz@support.com", status="ACTIVE", max_concurrency=5, current_active_tickets=0)
    db_session.add(agt)
    db_session.add(AgentSkill(agent_id="AGT-AMZ-01", skill_id="PAYMENT_GATEWAY", proficiency_level=0.95))
    db_session.add(AgentLanguage(agent_id="AGT-AMZ-01", language_code="en", fluency_score=1.0))
    db_session.commit()

    router = IntelligentRoutingEngine(db_session)
    t = Ticket(ticket_id="TKT-JIO-01", tenant_id="jio_demo", customer_id="CUS-000002", channel_id="email", subject="UPI failure", status="NEW", priority="P2", intent_id="PAYMENT_FAILURE", language_code="en")
    t.intent = Intent(intent_id="PAYMENT_FAILURE", name="Payment", category="BILLING", default_priority="P2", required_skill_id="PAYMENT_GATEWAY")

    res = router.evaluate_routing(t)
    # Amazon agent must be disqualified from Jio ticket
    assert res.selected_agent_id != "AGT-AMZ-01"
    assert any("Tenant isolation mismatch" in reason for r in res.rejected_candidates for reason in r.reasons)

# -----------------------------------------------------------------------------
# 19. Invalid lifecycle transitions must be rejected
# -----------------------------------------------------------------------------
def test_19_invalid_lifecycle_transitions_rejected(db_session):
    svc = TicketService(db_session)
    t = Ticket(ticket_id="TKT-STATE-01", tenant_id="default_tenant", customer_id="CUS-000001", channel_id="email", subject="State test", status="NEW", priority="P3", intent_id="PAYMENT_FAILURE")
    db_session.add(t)
    db_session.commit()

    # NEW cannot jump directly to RESOLVED without triage/assignment
    with pytest.raises(InvalidStateTransitionError):
        svc.update_ticket_status(t.ticket_id, "RESOLVED")

# -----------------------------------------------------------------------------
# 20. Historical events must remain immutable
# -----------------------------------------------------------------------------
def test_20_historical_events_remain_immutable(db_session):
    engine = SLAEngine(db_session)
    t = Ticket(ticket_id="TKT-IMMUTABLE-01", tenant_id="default_tenant", customer_id="CUS-000001", channel_id="email", subject="Audit", status="NEW", priority="P2", intent_id="PAYMENT_FAILURE")
    db_session.add(t)
    db_session.commit()

    sla = engine.create_sla_for_ticket(t)
    history_initial = db_session.query(SLAHistoryEvent).filter(SLAHistoryEvent.ticket_id == t.ticket_id).count()

    engine.pause_sla(t.ticket_id, SLAPauseRequest(reason="WAITING_FOR_CUSTOMER", authorized_by="SUPERVISOR"))
    engine.resume_sla(t.ticket_id, SLAResumeRequest(authorized_by="SUPERVISOR"))

    history_final = db_session.query(SLAHistoryEvent).filter(SLAHistoryEvent.ticket_id == t.ticket_id).count()
    # History count strictly increases; historical records are never deleted
    assert history_final > history_initial
    assert history_final >= 5
