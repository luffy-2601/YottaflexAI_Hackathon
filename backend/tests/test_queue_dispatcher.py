import pytest
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.app.core.database import Base
from backend.app.models.entities import (
    Customer, Channel, Skill, Language, Intent, Agent, AgentSkill, AgentLanguage,
    Ticket, SLAEvent, SLAPolicy
)
from backend.app.schemas.models import TicketCreateRequest, TicketResolveRequest
from backend.app.services.tickets.ticket_service import TicketService
from backend.app.services.routing.queue_dispatcher import QueueDispatcher

@pytest.fixture(scope="function")
def test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()

    # Seed base master data
    db.add_all([
        Channel(channel_id="email", name="Email", default_sla_factor=1.0, is_active=True),
        Language(language_code="en", name="English", is_supported=True),
        Skill(skill_id="PAYMENT_GATEWAY", name="Payment Gateway", tier_level=2),
        Skill(skill_id="SECURITY_FORENSICS", name="Security", tier_level=3),
        Intent(intent_id="PAYMENT_FAILURE", name="Payment Failure", category="BILLING", default_priority="P2", required_skill_id="PAYMENT_GATEWAY"),
        Customer(customer_id="CUS-001", tenant_id="default_tenant", name="Alice", email="alice@test.com", tier="STANDARD"),
        Customer(customer_id="CUS-002", tenant_id="default_tenant", name="Bob", email="bob@test.com", tier="STANDARD"),
    ])
    db.commit()
    yield db
    db.close()

def test_queue_dispatch_when_agent_capacity_freed(test_db):
    # Agent with max concurrency = 1
    agt = Agent(
        agent_id="AGT-SOLO",
        tenant_id="default_tenant",
        name="Solo Support",
        email="solo@test.com",
        status="ACTIVE",
        max_concurrency=1,
        current_active_tickets=1, # Currently full
        experience_score=0.9
    )
    test_db.add(agt)
    test_db.add(AgentSkill(agent_id="AGT-SOLO", skill_id="PAYMENT_GATEWAY", proficiency_level=0.95))
    test_db.add(AgentLanguage(agent_id="AGT-SOLO", language_code="en", fluency_score=1.0))
    test_db.commit()

    # Create an active ticket assigned to AGT-SOLO
    active_tkt = Ticket(
        ticket_id="TKT-ACTIVE",
        tenant_id="default_tenant",
        customer_id="CUS-001",
        channel_id="email",
        subject="Active Payment Issue",
        status="IN_PROGRESS",
        priority="P2",
        intent_id="PAYMENT_FAILURE",
        language_code="en",
        assigned_agent_id="AGT-SOLO",
        created_at=datetime.datetime.now(datetime.timezone.utc)
    )
    test_db.add(active_tkt)

    # Create a waiting QUEUED ticket (P1 High Priority)
    queued_tkt = Ticket(
        ticket_id="TKT-QUEUED-1",
        tenant_id="default_tenant",
        customer_id="CUS-002",
        channel_id="email",
        subject="Queued Urgent Payment Issue",
        status="QUEUED",
        priority="P1",
        intent_id="PAYMENT_FAILURE",
        language_code="en",
        assigned_agent_id=None,
        created_at=datetime.datetime.now(datetime.timezone.utc)
    )
    test_db.add(queued_tkt)
    test_db.commit()

    svc = TicketService(test_db)
    # Resolve the active ticket -> should release capacity and trigger QueueDispatcher
    svc.resolve_ticket("TKT-ACTIVE", TicketResolveRequest(agent_id="AGT-SOLO", summary="Refund issued", csat_score=5))

    test_db.refresh(queued_tkt)
    test_db.refresh(agt)

    # The queued ticket must have been automatically assigned to AGT-SOLO!
    assert queued_tkt.status == "ASSIGNED"
    assert queued_tkt.assigned_agent_id == "AGT-SOLO"
    assert agt.current_active_tickets == 1 # Was freed to 0, then immediately claimed back to 1

def test_queue_dispatch_priority_ordering(test_db):
    # Agent with max concurrency = 1, current = 0
    agt = Agent(
        agent_id="AGT-DISPATCH",
        tenant_id="default_tenant",
        name="Dispatcher Agent",
        email="disp@test.com",
        status="ACTIVE",
        max_concurrency=1,
        current_active_tickets=0,
        experience_score=0.9
    )
    test_db.add(agt)
    test_db.add(AgentSkill(agent_id="AGT-DISPATCH", skill_id="PAYMENT_GATEWAY", proficiency_level=0.95))
    test_db.add(AgentLanguage(agent_id="AGT-DISPATCH", language_code="en", fluency_score=1.0))

    # Add 2 queued tickets: P3 created earlier, P1 created later.
    # P1 MUST be picked before P3 despite arriving later!
    now = datetime.datetime.now(datetime.timezone.utc)
    tkt_p3 = Ticket(
        ticket_id="TKT-P3",
        tenant_id="default_tenant",
        customer_id="CUS-001",
        channel_id="email",
        subject="Minor Payment Query",
        status="QUEUED",
        priority="P3",
        intent_id="PAYMENT_FAILURE",
        language_code="en",
        created_at=now - datetime.timedelta(hours=2)
    )
    tkt_p1 = Ticket(
        ticket_id="TKT-P1",
        tenant_id="default_tenant",
        customer_id="CUS-002",
        channel_id="email",
        subject="Critical Payment Failure",
        status="QUEUED",
        priority="P1",
        intent_id="PAYMENT_FAILURE",
        language_code="en",
        created_at=now
    )
    test_db.add_all([tkt_p3, tkt_p1])
    test_db.commit()

    dispatcher = QueueDispatcher(test_db)
    dispatched = dispatcher.dispatch_for_agent("AGT-DISPATCH", "default_tenant")

    assert len(dispatched) == 1
    assert dispatched[0].ticket_id == "TKT-P1" # Higher priority wins!
    assert dispatched[0].assigned_agent_id == "AGT-DISPATCH"
