import pytest
from fastapi.testclient import TestClient
from backend.app.main import app, client_request_history
from backend.app.services.classification.classifier import ClassificationEngine
from backend.app.models.entities import Agent, AgentSkill, AgentLanguage, Ticket, Intent
from backend.app.services.routing.routing_engine import IntelligentRoutingEngine
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.app.core.database import Base

def test_customer_sentiment_analysis():
    # Frustrated customer
    frustrated_msg = "Your service is terrible and worst experience! Money stolen and network broken!"
    score_neg = ClassificationEngine.analyze_sentiment(frustrated_msg)
    assert score_neg < 0.0

    # Happy customer
    happy_msg = "Thank you so much! Great quick resolution and excellent helpful support!"
    score_pos = ClassificationEngine.analyze_sentiment(happy_msg)
    assert score_pos > 0.0

    # Neutral
    neutral_msg = "Here is my account number."
    score_neu = ClassificationEngine.analyze_sentiment(neutral_msg)
    assert score_neu == 0.0

def test_rate_limiting_middleware():
    client = TestClient(app)
    # Clear client request history for test purity
    client_request_history.clear()

    # Normal requests succeed
    resp = client.get("/api/v1/auth/me")
    # Will return 401 because no token, but NOT 429
    assert resp.status_code == 401

    # Simulate 300 rapid requests to trigger rate limit
    for _ in range(305):
        resp = client.get("/api/v1/auth/me")

    # The 301st+ request must be rate limited with 429 Too Many Requests
    assert resp.status_code == 429
    assert "Too Many Requests" in resp.json()["detail"]
    assert "Retry-After" in resp.headers

    # Clean up
    client_request_history.clear()

def test_composite_multi_skill_routing_boost():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    # Agent A: has only PAYMENT_GATEWAY
    agt_a = Agent(agent_id="AGT-SINGLE", name="Single Skill", email="a@test.com", status="ACTIVE", max_concurrency=5, current_active_tickets=0, experience_score=0.8)
    # Agent B: has PAYMENT_GATEWAY + SECURITY_FORENSICS + INFRA_SYSADMIN
    agt_b = Agent(agent_id="AGT-MULTI", name="Multi Skill", email="b@test.com", status="ACTIVE", max_concurrency=5, current_active_tickets=0, experience_score=0.8)

    db.add_all([agt_a, agt_b])
    db.add_all([
        AgentSkill(agent_id="AGT-SINGLE", skill_id="PAYMENT_GATEWAY", proficiency_level=0.85),
        AgentLanguage(agent_id="AGT-SINGLE", language_code="en", fluency_score=1.0),

        AgentSkill(agent_id="AGT-MULTI", skill_id="PAYMENT_GATEWAY", proficiency_level=0.85),
        AgentSkill(agent_id="AGT-MULTI", skill_id="SECURITY_FORENSICS", proficiency_level=0.90),
        AgentSkill(agent_id="AGT-MULTI", skill_id="INFRA_SYSADMIN", proficiency_level=0.90),
        AgentLanguage(agent_id="AGT-MULTI", language_code="en", fluency_score=1.0),
    ])
    db.commit()

    router = IntelligentRoutingEngine(db)
    t = Ticket(
        ticket_id="TKT-COMPOSITE",
        customer_id="CUS-001",
        channel_id="email",
        subject="Payment outage issue",
        status="NEW",
        priority="P2",
        intent_id="PAYMENT_FAILURE",
        language_code="en"
    )
    t.intent = Intent(intent_id="PAYMENT_FAILURE", name="Payment", category="BILLING", default_priority="P2", required_skill_id="PAYMENT_GATEWAY")

    eval_res = router.evaluate_routing(t)
    # AGT-MULTI should score higher than AGT-SINGLE due to composite multi-skill breadth!
    scores = {c.agent_id: c.total_score for c in eval_res.candidate_scores}
    assert scores["AGT-MULTI"] > scores["AGT-SINGLE"]
    db.close()

def test_dynamic_calendar_holidays_crud_and_sla():
    client = TestClient(app)
    # 1. Fetch holidays
    res = client.get("/api/v1/config/holidays")
    assert res.status_code == 200
    data = res.json()
    assert "2026-01-26" in data["default_company_holidays"]

    # 2. Add dynamic holiday
    post_res = client.post("/api/v1/config/holidays", json={
        "calendar_id": "DEFAULT_CALENDAR",
        "holiday_date": "2026-06-15",
        "name": "Mid-Year Maintenance Holiday"
    })
    assert post_res.status_code == 201
    hol_id = post_res.json()["holiday"]["holiday_id"]

    # 3. Verify in list
    res2 = client.get("/api/v1/config/holidays")
    dyn_dates = [h["holiday_date"] for h in res2.json()["dynamic_calendar_holidays"]]
    assert "2026-06-15" in dyn_dates

    # 4. Delete holiday
    del_res = client.delete(f"/api/v1/config/holidays/{hol_id}")
    assert del_res.status_code == 200

def test_supervisor_worsening_sentiment_alert():
    import uuid
    from backend.app.core.database import SessionLocal
    from backend.app.services.tickets.ticket_service import TicketService
    from backend.app.models.entities import Anomaly
    from backend.app.schemas.models import TicketCreateRequest

    client = TestClient(app)
    db = SessionLocal()
    svc = TicketService(db)

    # 1. Create a ticket with initial mild or neutral message
    req = TicketCreateRequest(
        customer_id="CUS-000001",
        channel_id="email",
        subject=f"Order inquiry status check {uuid.uuid4().hex[:6]}",
        body="Hello, I wanted to check the status of my order please.",
        language_code="en"
    )
    tkt = svc.create_ticket(req)

    # 2. Customer replies with severely negative / worsening sentiment
    bad_msg = svc.add_message(
        ticket_id=tkt.ticket_id,
        sender_type="CUSTOMER",
        sender_id="CUS-000001",
        body="This is ridiculous, completely unacceptable! You stole my money and ruined everything, worst company ever!"
    )

    # 3. Verify supervisor alert was recorded in Anomaly table
    alert = db.query(Anomaly).filter(
        Anomaly.ticket_id == tkt.ticket_id,
        Anomaly.category == "WORSENING_SENTIMENT_ALERT"
    ).first()

    assert alert is not None
    assert alert.severity == "HIGH"
    assert "Supervisor Alert" in alert.description
    db.close()

def test_realtime_telemetry_snapshot_and_sse():
    client = TestClient(app)
    # 1. Snapshot endpoint
    snap = client.get("/api/v1/analytics/telemetry/snapshot")
    assert snap.status_code == 200
    data = snap.json()
    assert "open_tickets" in data
    assert "queued_tickets" in data
    assert "sla_breaches" in data
    assert "active_agents" in data

    # 2. Background jobs telemetry
    bg = client.get("/api/v1/analytics/telemetry/background-jobs")
    assert bg.status_code == 200
    bg_data = bg.json()
    assert "job_id" in bg_data
    assert bg_data["status"] in ["HEALTHY", "FAILED"]

    # 3. SSE stream endpoint
    stream_resp = client.get("/api/v1/analytics/telemetry/stream")
    assert stream_resp.status_code == 200
    assert "text/event-stream" in stream_resp.headers["content-type"]
    assert "data:" in stream_resp.text


