import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from backend.app.models.entities import (
    Ticket, Customer, Channel, Intent, Language, Message, AssignmentEvent,
    SLAEvent, Resolution, TicketStatusEvent, Agent, RoutingDecision, Anomaly
)
from backend.app.schemas.models import (
    TicketCreateRequest, TicketTransferRequest, TicketEscalateRequest,
    TicketReopenRequest, TicketResolveRequest
)
from backend.app.services.classification.classifier import ClassificationEngine
from backend.app.services.sla.sla_calculator import SLACalculator
from backend.app.services.sla.sla_engine import SLAEngine, UnauthorizedPauseError
from backend.app.services.routing.routing_engine import IntelligentRoutingEngine
from backend.app.schemas.models import SLAPauseRequest, SLAResumeRequest

def ensure_utc(dt: Optional[datetime.datetime]) -> Optional[datetime.datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=datetime.timezone.utc)
    return dt

VALID_TRANSITIONS = {
    "NEW": ["OPEN", "ASSIGNED", "QUEUED", "TRIAGED"],
    "TRIAGED": ["QUEUED", "ASSIGNED"],
    "OPEN": ["ASSIGNED", "IN_PROGRESS", "PENDING_CUSTOMER", "WAITING_FOR_CUSTOMER", "WAITING_FOR_EXTERNAL_DEPENDENCY", "RESOLVED", "CLOSED"],
    "ASSIGNED": ["ASSIGNED", "IN_PROGRESS", "PENDING_CUSTOMER", "WAITING_FOR_CUSTOMER", "WAITING_FOR_EXTERNAL_DEPENDENCY", "ESCALATED", "RESOLVED", "QUEUED"],
    "QUEUED": ["ASSIGNED", "ESCALATED"],
    "IN_PROGRESS": ["PENDING_CUSTOMER", "WAITING_FOR_CUSTOMER", "WAITING_FOR_EXTERNAL_DEPENDENCY", "ESCALATED", "RESOLVED", "ASSIGNED"],
    "PENDING_CUSTOMER": ["IN_PROGRESS", "ASSIGNED", "RESOLVED", "CLOSED"],
    "WAITING_FOR_CUSTOMER": ["IN_PROGRESS", "ASSIGNED", "RESOLVED", "CLOSED"],
    "WAITING_FOR_EXTERNAL_DEPENDENCY": ["IN_PROGRESS", "ASSIGNED", "RESOLVED", "CLOSED"],
    "ESCALATED": ["ASSIGNED", "IN_PROGRESS", "RESOLVED"],
    "RESOLVED": ["REOPENED", "CLOSED"],
    "REOPENED": ["ASSIGNED", "IN_PROGRESS", "ESCALATED"],
    "CLOSED": []  # Terminal state
}

class DuplicateIngestionError(ValueError):
    """Raised when duplicate ticket or message is submitted within deduplication window."""
    pass

class InvalidStateTransitionError(ValueError):
    """Raised when an invalid lifecycle transition is attempted."""
    pass

class TicketService:
    def __init__(self, db: Session):
        self.db = db
        self.router = IntelligentRoutingEngine(db)
        self.sla_engine = SLAEngine(db)

    def validate_transition(self, current_status: str, new_status: str):
        allowed = VALID_TRANSITIONS.get(current_status, [])
        if new_status not in allowed:
            raise InvalidStateTransitionError(
                f"Invalid state transition from '{current_status}' to '{new_status}'. Allowed transitions: {allowed}"
            )

    def create_ticket(self, req: TicketCreateRequest) -> Ticket:
        now = datetime.datetime.now(datetime.timezone.utc)

        # Duplicate Ingestion Check (60-second window on customer_id + subject + body)
        recent_cutoff = now - datetime.timedelta(seconds=60)
        recent_duplicate = (
            self.db.query(Ticket)
            .join(Message, Message.ticket_id == Ticket.ticket_id)
            .filter(
                Ticket.customer_id == req.customer_id,
                Ticket.subject == req.subject,
                Message.body == req.body,
                Ticket.created_at >= recent_cutoff
            )
            .first()
        )
        if recent_duplicate:
            raise DuplicateIngestionError(
                f"Duplicate ticket ingestion detected for customer '{req.customer_id}' with subject '{req.subject}' within deduplication window."
            )

        # 1. Classification & Safety Rule Check
        classification = ClassificationEngine.classify(req.subject, req.body)
        
        # Priority override if specified, but safety rules override downgrade
        final_priority = req.priority or classification.priority
        if classification.applied_safety_rules and "Forced P1" in classification.applied_safety_rules[0]:
            final_priority = "P1" # Safety rule invariant
        
        language_code = req.language_code or classification.language_code
        intent_id = classification.intent_id

        # Verify Customer and Channel exist
        customer = self.db.query(Customer).filter(Customer.customer_id == req.customer_id).first()
        if not customer:
            # Create default customer if missing
            customer = Customer(
                customer_id=req.customer_id,
                name=f"Customer {req.customer_id}",
                email=f"{req.customer_id.lower()}@example.com",
                tier="STANDARD"
            )
            self.db.add(customer)
            self.db.flush()

        channel = self.db.query(Channel).filter(Channel.channel_id == req.channel_id).first()
        sla_factor = channel.default_sla_factor if channel else 1.0

        # Generate Deterministic Ticket ID
        total_tickets = self.db.query(Ticket).count()
        ticket_id = f"TKT-2026-{total_tickets + 1:06d}"
        now = datetime.datetime.now(datetime.timezone.utc)

        # 2. SLA Deadlines
        first_resp_due, resol_due = SLACalculator.calculate_deadlines(
            priority=final_priority,
            channel_id=req.channel_id,
            created_at=now,
            channel_sla_factor=sla_factor
        )

        ticket = Ticket(
            ticket_id=ticket_id,
            tenant_id=getattr(req, "tenant_id", "default_tenant") or "default_tenant",
            customer_id=customer.customer_id,
            channel_id=req.channel_id,
            subject=req.subject,
            status="NEW",
            priority=final_priority,
            intent_id=intent_id,
            language_code=language_code,
            created_at=now,
            updated_at=now
        )
        self.db.add(ticket)
        self.db.flush()

        # 3. Initial Customer Message
        msg_id = f"MSG-{ticket_id}-001"
        computed_sentiment = ClassificationEngine.analyze_sentiment(req.body)
        initial_msg = Message(
            message_id=msg_id,
            ticket_id=ticket_id,
            sender_type="CUSTOMER",
            sender_id=customer.customer_id,
            body=req.body,
            sentiment_score=computed_sentiment,
            created_at=now
        )
        self.db.add(initial_msg)

        # 4. Independent Dual-Clock SLA Orchestration
        sla_record = self.sla_engine.create_sla_for_ticket(ticket, actor="SYSTEM_INGEST")

        # 5. Status Event
        status_evt = TicketStatusEvent(
            event_id=f"EVT-{ticket_id}-001",
            ticket_id=ticket_id,
            old_status=None,
            new_status="NEW",
            changed_by="SYSTEM_INGEST",
            reason="Ticket created from incoming message",
            created_at=now
        )
        self.db.add(status_evt)

        # 6. Intelligent Routing Evaluation
        eval_result = self.router.evaluate_routing(ticket, now)

        # Persist Routing Decision Record
        decision = RoutingDecision(
            decision_id=f"DEC-{ticket_id}-001",
            ticket_id=ticket_id,
            selected_agent_id=eval_result.selected_agent_id,
            final_score=eval_result.final_score,
            eligible_count=eval_result.eligible_count,
            candidate_scores=[s.model_dump() for s in eval_result.candidate_scores],
            rejected_candidates=[r.model_dump() for r in eval_result.rejected_candidates],
            reason=eval_result.explanation,
            policy_version="v1.0-weighted",
            created_at=now
        )
        self.db.add(decision)

        if eval_result.selected_agent_id:
            assigned = self.router.assign_ticket_atomically(
                ticket=ticket,
                selected_agent_id=eval_result.selected_agent_id,
                reason=eval_result.explanation,
                actor_id="SYSTEM_ROUTER"
            )
            if not assigned:
                ticket.status = "QUEUED"
        else:
            ticket.status = "QUEUED"

        self.db.commit()
        self.db.refresh(ticket)
        return ticket

    def add_message(self, ticket_id: str, sender_type: str, sender_id: str, body: str) -> Message:
        ticket = self.db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")

        msg_count = self.db.query(Message).filter(Message.ticket_id == ticket_id).count()
        msg_id = f"MSG-{ticket_id}-{msg_count + 1:03d}"
        now = datetime.datetime.now(datetime.timezone.utc)

        computed_sentiment = ClassificationEngine.analyze_sentiment(body)
        msg = Message(
            message_id=msg_id,
            ticket_id=ticket_id,
            sender_type=sender_type,
            sender_id=sender_id,
            body=body,
            sentiment_score=computed_sentiment,
            created_at=now
        )
        self.db.add(msg)

        # Supervisor alert on worsening customer sentiment
        if sender_type == "CUSTOMER" and computed_sentiment <= -0.5:
            prev_cust_msg = self.db.query(Message).filter(
                Message.ticket_id == ticket_id,
                Message.sender_type == "CUSTOMER",
                Message.message_id != msg_id
            ).order_by(Message.created_at.desc()).first()
            if prev_cust_msg and prev_cust_msg.sentiment_score is not None and (prev_cust_msg.sentiment_score - computed_sentiment >= 0.3):
                alert_id = f"ANOM-SENT-{msg_id}"
                existing_alert = self.db.query(Anomaly).filter(Anomaly.anomaly_id == alert_id).first()
                if not existing_alert:
                    alert = Anomaly(
                        anomaly_id=alert_id,
                        ticket_id=ticket_id,
                        agent_id=ticket.assigned_agent_id,
                        category="WORSENING_SENTIMENT_ALERT",
                        severity="HIGH",
                        description=f"Supervisor Alert: Customer sentiment dropped from {prev_cust_msg.sentiment_score:.2f} to {computed_sentiment:.2f} in ticket {ticket_id}.",
                        expected_behavior="Customer sentiment should remain stable or positive during support resolution.",
                        actual_behavior=f"Customer expressed heightened dissatisfaction (sentiment score: {computed_sentiment:.2f}).",
                        detected_at=now
                    )
                    self.db.add(alert)

        # If this is an agent response, stop first response clock; automated acks do NOT stop it
        if sender_type == "AGENT":
            if not ticket.first_response_at:
                ticket.first_response_at = now
            self.sla_engine.record_first_response(ticket_id, actor=sender_id, is_automated_ack=False)
        elif sender_type in ["SYSTEM", "BOT", "AUTO_ACK"]:
            self.sla_engine.record_first_response(ticket_id, actor=sender_id, is_automated_ack=True)

        ticket.updated_at = now
        self.db.commit()
        self.db.refresh(msg)
        return msg

    def transfer_ticket(self, ticket_id: str, req: TicketTransferRequest) -> Ticket:
        ticket = self.db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")

        self.validate_transition(ticket.status, "ASSIGNED")

        target_agent = self.db.query(Agent).filter(Agent.agent_id == req.to_agent_id).first()
        if not target_agent:
            raise ValueError(f"Agent {req.to_agent_id} not found")

        # Transfer Loop Detection
        recent_assignments = (
            self.db.query(AssignmentEvent)
            .filter(AssignmentEvent.ticket_id == ticket_id)
            .order_by(AssignmentEvent.created_at.desc())
            .limit(4)
            .all()
        )
        agent_history = [e.agent_id for e in recent_assignments]
        if agent_history.count(req.to_agent_id) >= 2:
            # Transfer loop detected!
            loop_anomaly = Anomaly(
                anomaly_id=f"ANOM-LOOP-{ticket_id}-{int(datetime.datetime.now().timestamp())}",
                ticket_id=ticket_id,
                agent_id=req.to_agent_id,
                category="TRANSFER_LOOP",
                severity="HIGH",
                description=f"Ticket repeatedly transferred back and forth involving {req.to_agent_id}",
                expected_behavior="Ticket should progress to resolution without ping-pong reassignments",
                actual_behavior=f"Transfer loop detected with history: {agent_history}",
                detected_at=datetime.datetime.now(datetime.timezone.utc)
            )
            self.db.add(loop_anomaly)

        # Release capacity from previous agent
        if ticket.assigned_agent_id:
            old_agent = self.db.query(Agent).filter(Agent.agent_id == ticket.assigned_agent_id).first()
            if old_agent and old_agent.current_active_tickets > 0:
                old_agent.current_active_tickets -= 1

        # Reserve capacity for new agent
        target_agent.current_active_tickets += 1
        ticket.assigned_agent_id = target_agent.agent_id
        ticket.status = "ASSIGNED"
        now = datetime.datetime.now(datetime.timezone.utc)
        ticket.updated_at = now

        # Append assignment event
        event_count = self.db.query(AssignmentEvent).filter(AssignmentEvent.ticket_id == ticket_id).count()
        asn = AssignmentEvent(
            assignment_id=f"ASN-{ticket_id}-{event_count + 1:03d}",
            ticket_id=ticket_id,
            agent_id=target_agent.agent_id,
            event_type="TRANSFER",
            actor_id="SUPERVISOR",
            reason=req.reason,
            created_at=now
        )
        self.db.add(asn)
        self.db.commit()
        self.db.refresh(ticket)
        return ticket

    def escalate_ticket(self, ticket_id: str, req: TicketEscalateRequest) -> Ticket:
        ticket = self.db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
        if not ticket:
            raise ValueError("Ticket not found")

        self.validate_transition(ticket.status, "ESCALATED")

        # Upgrade Priority (e.g. P3 -> P2, P2 -> P1)
        priority_ladder = {"P4": "P3", "P3": "P2", "P2": "P1", "P1": "P1"}
        ticket.priority = priority_ladder.get(ticket.priority, "P1")
        ticket.status = "ESCALATED"
        now = datetime.datetime.now(datetime.timezone.utc)
        ticket.updated_at = now

        # Add event
        event_count = self.db.query(TicketStatusEvent).filter(TicketStatusEvent.ticket_id == ticket_id).count()
        status_evt = TicketStatusEvent(
            event_id=f"EVT-{ticket_id}-{event_count + 1:03d}",
            ticket_id=ticket_id,
            old_status="IN_PROGRESS",
            new_status="ESCALATED",
            changed_by="SLA_MONITOR",
            reason=req.reason,
            created_at=now
        )
        self.db.add(status_evt)
        self.db.commit()
        self.db.refresh(ticket)
        return ticket

    def reopen_ticket(self, ticket_id: str, req: TicketReopenRequest) -> Ticket:
        ticket = self.db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
        if not ticket:
            raise ValueError("Ticket not found")

        self.validate_transition(ticket.status, "REOPENED")

        # Reopening MUST preserve all historical events and prior resolutions
        now = datetime.datetime.now(datetime.timezone.utc)
        ticket.status = "REOPENED"
        ticket.updated_at = now

        # Record Status Event
        event_count = self.db.query(TicketStatusEvent).filter(TicketStatusEvent.ticket_id == ticket_id).count()
        status_evt = TicketStatusEvent(
            event_id=f"EVT-{ticket_id}-{event_count + 1:03d}",
            ticket_id=ticket_id,
            old_status="RESOLVED",
            new_status="REOPENED",
            changed_by="CUSTOMER",
            reason=req.reason,
            created_at=now
        )
        self.db.add(status_evt)

        # If agent still available, assign back, else route
        if ticket.assigned_agent_id:
            agent = self.db.query(Agent).filter(Agent.agent_id == ticket.assigned_agent_id).first()
            if agent:
                agent.current_active_tickets += 1

        self.db.commit()
        self.db.refresh(ticket)
        return ticket

    def resolve_ticket(self, ticket_id: str, req: TicketResolveRequest) -> Resolution:
        ticket = self.db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
        if not ticket:
            raise ValueError("Ticket not found")

        self.validate_transition(ticket.status, "RESOLVED")

        now = datetime.datetime.now(datetime.timezone.utc)
        ticket.status = "RESOLVED"
        ticket.resolved_at = now
        ticket.updated_at = now

        # Release agent capacity slot
        freed_agent_id = ticket.assigned_agent_id
        if freed_agent_id:
            agent = self.db.query(Agent).filter(Agent.agent_id == freed_agent_id).first()
            if agent and agent.current_active_tickets > 0:
                agent.current_active_tickets -= 1

        # Stop resolution clock via SLA Engine
        self.sla_engine.record_resolution(ticket_id, actor=req.agent_id, reason=req.summary)

        # Create or update Resolution
        res = self.db.query(Resolution).filter(Resolution.ticket_id == ticket_id).first()
        if not res:
            res = Resolution(
                resolution_id=f"RES-{ticket_id}",
                ticket_id=ticket_id,
                agent_id=req.agent_id,
                resolution_code=req.resolution_code,
                summary=req.summary,
                csat_score=req.csat_score,
                csat_feedback=req.csat_feedback,
                created_at=now
            )
            self.db.add(res)
        else:
            res.agent_id = req.agent_id
            res.resolution_code = req.resolution_code
            res.summary = req.summary
            res.csat_score = req.csat_score
            res.csat_feedback = req.csat_feedback

        self.db.commit()
        self.db.refresh(res)

        # Autonomous Queue Dispatch: Immediately pull next eligible ticket for freed agent
        if freed_agent_id:
            try:
                from backend.app.services.routing.queue_dispatcher import QueueDispatcher
                QueueDispatcher(self.db).dispatch_for_agent(freed_agent_id, ticket.tenant_id)
            except Exception as e:
                pass

        return res

    def update_ticket_status(self, ticket_id: str, new_status: str, actor_id: str = "AGENT", reason: Optional[str] = None) -> Ticket:
        ticket = self.db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")

        self.validate_transition(ticket.status, new_status)
        old_status = ticket.status
        now = datetime.datetime.now(datetime.timezone.utc)

        # Handle SLA pause when transitioning to waiting states
        pause_states = {"WAITING_FOR_CUSTOMER", "WAITING_FOR_THIRD_PARTY", "WAITING_FOR_EXTERNAL_DEPENDENCY", "PENDING_CUSTOMER"}
        if new_status in pause_states:
            mapped_reason = "WAITING_FOR_CUSTOMER" if new_status in ["WAITING_FOR_CUSTOMER", "PENDING_CUSTOMER"] else new_status
            self.sla_engine.pause_sla(ticket_id, SLAPauseRequest(reason=mapped_reason, authorized_by=actor_id))
        elif old_status in pause_states and new_status in ["IN_PROGRESS", "ASSIGNED"]:
            self.sla_engine.resume_sla(ticket_id, SLAResumeRequest(authorized_by=actor_id, reason=reason))

        ticket.status = new_status
        ticket.updated_at = now

        event_count = self.db.query(TicketStatusEvent).filter(TicketStatusEvent.ticket_id == ticket_id).count()
        evt = TicketStatusEvent(
            event_id=f"EVT-{ticket_id}-{event_count + 1:03d}",
            ticket_id=ticket_id,
            old_status=old_status,
            new_status=new_status,
            changed_by=actor_id,
            reason=reason or f"Status changed to {new_status}",
            created_at=now
        )
        self.db.add(evt)
        self.db.commit()
        self.db.refresh(ticket)
        return ticket
