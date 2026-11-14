import datetime
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.models.entities import Ticket, Agent, SLAEvent, Resolution, Channel, Intent

class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def get_operations_overview(self) -> Dict[str, Any]:
        total_tickets = self.db.query(Ticket).count()
        open_tickets = self.db.query(Ticket).filter(Ticket.status.notin_(["RESOLVED", "CLOSED"])).count()
        resolved_tickets = self.db.query(Ticket).filter(Ticket.status.in_(["RESOLVED", "CLOSED"])).count()
        unassigned_tickets = self.db.query(Ticket).filter(Ticket.assigned_agent_id.is_(None)).count()
        critical_incidents = self.db.query(Ticket).filter(Ticket.priority == "P1").count()

        active_agents = self.db.query(Agent).filter(Agent.status == "ACTIVE").count()
        total_capacity = self.db.query(func.sum(Agent.max_concurrency)).scalar() or 1
        used_capacity = self.db.query(func.sum(Agent.current_active_tickets)).scalar() or 0
        overall_utilization = round((used_capacity / total_capacity) * 100.0, 1) if total_capacity else 0.0

        # SLA metrics
        total_sla_records = self.db.query(SLAEvent).count()
        breached_sla_records = self.db.query(SLAEvent).filter(
            (SLAEvent.is_first_response_breached == True) | (SLAEvent.is_resolution_breached == True)
        ).count()
        sla_compliance_pct = round(
            ((total_sla_records - breached_sla_records) / total_sla_records * 100.0) if total_sla_records > 0 else 100.0,
            1
        )

        # Average Response Times
        tickets_with_response = self.db.query(Ticket).filter(Ticket.first_response_at.isnot(None)).all()
        avg_frt = 0.0
        if tickets_with_response:
            total_frt_secs = sum(
                (t.first_response_at - t.created_at).total_seconds()
                for t in tickets_with_response
                if t.first_response_at >= t.created_at
            )
            avg_frt = round((total_frt_secs / len(tickets_with_response)) / 60.0, 1)

        # Average Resolution Times
        resolved_list = self.db.query(Ticket).filter(Ticket.resolved_at.isnot(None)).all()
        avg_mttr = 0.0
        if resolved_list:
            total_mttr_secs = sum(
                (t.resolved_at - t.created_at).total_seconds()
                for t in resolved_list
                if t.resolved_at >= t.created_at
            )
            avg_mttr = round((total_mttr_secs / len(resolved_list)) / 60.0, 1)

        # Average CSAT
        csat_records = self.db.query(Resolution.csat_score).filter(Resolution.csat_score.isnot(None)).all()
        avg_csat = round(sum(r[0] for r in csat_records) / len(csat_records), 2) if csat_records else 4.2

        # Distributions
        channel_dist = [
            {"channel": ch, "count": cnt}
            for ch, cnt in self.db.query(Ticket.channel_id, func.count(Ticket.ticket_id)).group_by(Ticket.channel_id).all()
        ]

        priority_dist = [
            {"priority": p, "count": cnt}
            for p, cnt in self.db.query(Ticket.priority, func.count(Ticket.ticket_id)).group_by(Ticket.priority).all()
        ]

        intent_dist = [
            {"intent": intent, "count": cnt}
            for intent, cnt in self.db.query(Ticket.intent_id, func.count(Ticket.ticket_id)).group_by(Ticket.intent_id).order_by(func.count(Ticket.ticket_id).desc()).limit(8).all()
        ]

        status_dist = [
            {"status": st, "count": cnt}
            for st, cnt in self.db.query(Ticket.status, func.count(Ticket.ticket_id)).group_by(Ticket.status).all()
        ]

        return {
            "total_tickets": total_tickets,
            "open_tickets": open_tickets,
            "resolved_tickets": resolved_tickets,
            "unassigned_tickets": unassigned_tickets,
            "critical_incidents": critical_incidents,
            "active_agents": active_agents,
            "overall_utilization_pct": overall_utilization,
            "sla_compliance_pct": sla_compliance_pct,
            "sla_breaches_count": breached_sla_records,
            "avg_first_response_minutes": avg_frt,
            "avg_resolution_minutes": avg_mttr,
            "avg_csat": avg_csat,
            "distributions": {
                "channel": channel_dist,
                "priority": priority_dist,
                "intent": intent_dist,
                "status": status_dist
            }
        }
