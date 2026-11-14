import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.app.models.entities import Ticket, Agent, AgentSkill, AgentLanguage, AgentShift
from backend.app.services.routing.routing_engine import IntelligentRoutingEngine

logger = logging.getLogger("OmniRoute.QueueDispatcher")

class QueueDispatcher:
    """
    Autonomous Queue Dispatcher.
    Pulls queued tickets in priority order (P1 > P2 > P3 > P4, then FIFO)
    and assigns them to available agents who have freed up capacity.
    """

    def __init__(self, db: Session):
        self.db = db
        self.router = IntelligentRoutingEngine(db)

    def dispatch_for_agent(
        self,
        agent_id: str,
        tenant_id: Optional[str] = "default_tenant"
    ) -> List[Ticket]:
        """
        Attempts to fill free capacity of a specific agent by pulling eligible
        tickets from the QUEUED pool.
        """
        agent = self.db.query(Agent).filter(
            Agent.agent_id == agent_id,
            Agent.status == "ACTIVE"
        ).first()

        if not agent:
            return []

        free_capacity = agent.max_concurrency - agent.current_active_tickets
        if free_capacity <= 0:
            return []

        # Fetch candidate queued tickets for this tenant
        query = self.db.query(Ticket).filter(
            Ticket.status == "QUEUED"
        )
        if tenant_id:
            query = query.filter(Ticket.tenant_id == tenant_id)

        # Order by priority weight: P1=1, P2=2, P3=3, P4=4, then created_at ASC (FIFO)
        queued_tickets = query.order_by(
            Ticket.priority.asc(),
            Ticket.created_at.asc()
        ).all()

        dispatched_tickets: List[Ticket] = []

        # Get agent's skills and languages
        agent_skills = {
            s.skill_id: s.proficiency_level
            for s in self.db.query(AgentSkill).filter(AgentSkill.agent_id == agent_id).all()
        }
        agent_languages = {
            l.language_code: l.fluency_score
            for l in self.db.query(AgentLanguage).filter(AgentLanguage.agent_id == agent_id).all()
        }

        for ticket in queued_tickets:
            if free_capacity <= 0:
                break

            # 1. Multi-Skill check (Agent must possess EVERY mandatory skill with prof >= 0.60)
            req_skills = set()
            if ticket.intent and ticket.intent.required_skill_id:
                req_skills.add(ticket.intent.required_skill_id)
            extra_skills = getattr(ticket, "required_skills", None) or getattr(ticket, "mandatory_skills", None)
            if extra_skills:
                if isinstance(extra_skills, (list, set)):
                    req_skills.update(extra_skills)
                elif isinstance(extra_skills, str):
                    req_skills.add(extra_skills)

            skills_satisfied = True
            for sk in req_skills:
                if agent_skills.get(sk, 0.0) < 0.60:
                    skills_satisfied = False
                    break
            if not skills_satisfied:
                continue

            # 2. Language check
            req_lang = ticket.language_code or "en"
            fluency = agent_languages.get(req_lang, 0.0)
            if fluency < 0.60:
                continue

            # 3. Attempt atomic assignment
            assigned = self.router.assign_ticket_atomically(
                ticket=ticket,
                selected_agent_id=agent_id,
                reason="AUTO_QUEUE_DISPATCH: Capacity released",
                actor_id="AUTONOMOUS_QUEUE_DISPATCHER"
            )

            if assigned:
                dispatched_tickets.append(ticket)
                free_capacity -= 1
                logger.info(
                    f"Dispatched queued ticket {ticket.ticket_id} (Priority: {ticket.priority}) "
                    f"to freed agent {agent_id}."
                )

        if dispatched_tickets:
            self.db.commit()

        return dispatched_tickets

    def dispatch_all(self, tenant_id: Optional[str] = "default_tenant") -> Dict[str, Any]:
        """
        Scans all active agents with available capacity and fills them from QUEUED tickets.
        """
        agents_with_capacity = self.db.query(Agent).filter(
            Agent.status == "ACTIVE",
            Agent.current_active_tickets < Agent.max_concurrency
        )
        if tenant_id:
            agents_with_capacity = agents_with_capacity.filter(Agent.tenant_id == tenant_id)

        agents = agents_with_capacity.all()
        total_dispatched = 0
        details = []

        for agt in agents:
            dispatched = self.dispatch_for_agent(agt.agent_id, tenant_id=tenant_id)
            if dispatched:
                total_dispatched += len(dispatched)
                details.append({
                    "agent_id": agt.agent_id,
                    "name": agt.name,
                    "dispatched_count": len(dispatched),
                    "ticket_ids": [t.ticket_id for t in dispatched]
                })

        return {
            "status": "SUCCESS",
            "total_dispatched": total_dispatched,
            "agents_serviced": len(details),
            "dispatches": details
        }
