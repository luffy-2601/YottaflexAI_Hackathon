import datetime
from typing import List
from sqlalchemy.orm import Session
from backend.app.models.entities import Agent, Ticket, AssignmentEvent, SLAEvent, PriorityRule, Anomaly
from backend.app.schemas.models import AnomalyResponse

class AnomalyDetectionService:
    def __init__(self, db: Session):
        self.db = db

    def scan_anomalies(self) -> List[Anomaly]:
        """
        Scans for 5 required anomaly patterns:
        1. Agent assigned beyond capacity (current_active_tickets > max_concurrency)
        2. SLA ignores channel calendar (e.g. Chat/Phone using raw asynchronous calendar)
        3. Reopened ticket loses historical records (missing original assignment or messages)
        4. Repeated transfer loop (ping-pong between agents)
        5. Priority contradicts defined safety rule (e.g. account compromised classified as P3/P4)
        """
        detected: List[Anomaly] = []
        now = datetime.datetime.now(datetime.timezone.utc)

        # 1. Capacity Violations
        overloaded_agents = self.db.query(Agent).filter(Agent.current_active_tickets > Agent.max_concurrency).all()
        for agt in overloaded_agents:
            anom = Anomaly(
                anomaly_id=f"ANOM-CAP-{agt.agent_id}-{int(now.timestamp())}",
                agent_id=agt.agent_id,
                category="CAPACITY_VIOLATION",
                severity="HIGH",
                description=f"Agent {agt.name} ({agt.agent_id}) currently holds {agt.current_active_tickets} tickets, exceeding max concurrency of {agt.max_concurrency}.",
                expected_behavior=f"Agent assignment should never exceed {agt.max_concurrency} concurrent tickets.",
                actual_behavior=f"Active tickets: {agt.current_active_tickets}.",
                detected_at=now
            )
            detected.append(anom)

        # 2. Safety Rule Invariant Violations
        # Tickets with account security keywords or fraud that are NOT P1
        critical_tickets = self.db.query(Ticket).filter(
            Ticket.intent_id == "ACCOUNT_SECURITY",
            Ticket.priority != "P1"
        ).all()
        for tkt in critical_tickets:
            anom = Anomaly(
                anomaly_id=f"ANOM-SAFE-{tkt.ticket_id}-{int(now.timestamp())}",
                ticket_id=tkt.ticket_id,
                category="SAFETY_VIOLATION",
                severity="CRITICAL",
                description=f"Ticket {tkt.ticket_id} has intent ACCOUNT_SECURITY but priority was downgraded to {tkt.priority}.",
                expected_behavior="Safety rules mandate that ACCOUNT_SECURITY must strictly enforce P1 priority.",
                actual_behavior=f"Encountered priority: {tkt.priority}.",
                detected_at=now
            )
            detected.append(anom)

        # 3. SLA Channel Calendar Anomaly
        # Voice/phone tickets should have first response <= 15 minutes, never > 60 minutes
        phone_tickets = self.db.query(Ticket).join(SLAEvent).filter(
            Ticket.channel_id == "phone"
        ).all()
        for tkt in phone_tickets:
            for sla in tkt.sla_events:
                diff_minutes = (sla.first_response_due_at - tkt.created_at).total_seconds() / 60
                if diff_minutes > 120:
                    anom = Anomaly(
                        anomaly_id=f"ANOM-SLA-{tkt.ticket_id}-{int(now.timestamp())}",
                        ticket_id=tkt.ticket_id,
                        category="CALENDAR_MISMATCH",
                        severity="MEDIUM",
                        description=f"Synchronous Phone ticket {tkt.ticket_id} was assigned a slow async SLA of {diff_minutes:.0f} minutes.",
                        expected_behavior="Phone channel tickets must receive strict synchronous first-response deadlines (< 15 mins).",
                        actual_behavior=f"Deadline set {diff_minutes:.0f} mins out.",
                        detected_at=now
                    )
                    detected.append(anom)

        # 4. Reopened Ticket Lost History Anomaly
        reopened_tickets = self.db.query(Ticket).filter(Ticket.status == "REOPENED").all()
        for tkt in reopened_tickets:
            if len(tkt.assignment_events) == 0 or len(tkt.messages) <= 1:
                anom = Anomaly(
                    anomaly_id=f"ANOM-HIST-{tkt.ticket_id}-{int(now.timestamp())}",
                    ticket_id=tkt.ticket_id,
                    category="HISTORY_LOSS",
                    severity="HIGH",
                    description=f"Reopened ticket {tkt.ticket_id} has truncated or missing message/assignment event history.",
                    expected_behavior="Lifecycle invariant: Reopened tickets must retain 100% of previous conversation and assignments.",
                    actual_behavior=f"Found only {len(tkt.assignment_events)} assignment events and {len(tkt.messages)} messages.",
                    detected_at=now
                )
                detected.append(anom)

        # 5. Transfer Loop Scanning
        all_transfer_tickets = self.db.query(Ticket).all()
        for tkt in all_transfer_tickets:
            transfers = [e.agent_id for e in tkt.assignment_events if e.event_type == "TRANSFER"]
            if len(transfers) >= 2 and len(set(transfers)) < len(transfers):
                anom = Anomaly(
                    anomaly_id=f"ANOM-LOOP-{tkt.ticket_id}-{int(now.timestamp())}",
                    ticket_id=tkt.ticket_id,
                    category="TRANSFER_LOOP",
                    severity="HIGH",
                    description=f"Ticket {tkt.ticket_id} detected in cyclic transfer loop between agents {transfers}.",
                    expected_behavior="Tickets should progress to resolution without repeated cyclic transfers.",
                    actual_behavior=f"Transfer sequence: {transfers}",
                    detected_at=now
                )
                detected.append(anom)

        # Save any new anomalies to DB
        for a in detected:
            existing = self.db.query(Anomaly).filter(Anomaly.anomaly_id == a.anomaly_id).first()
            if not existing:
                self.db.add(a)
        self.db.commit()

        return self.db.query(Anomaly).order_by(Anomaly.detected_at.desc()).all()
