import datetime
from typing import List, Dict, Tuple, Optional
from sqlalchemy.orm import Session
from backend.app.models.entities import Agent, Ticket, Skill, Language, RoutingDecision, AssignmentEvent, AgentShift
from backend.app.schemas.models import RoutingCandidateScore, RoutingRejectedCandidate, RoutingEvaluationResponse
from backend.app.core.config import settings

class IntelligentRoutingEngine:
    def __init__(self, db: Session):
        self.db = db

    def evaluate_routing(
        self,
        ticket: Ticket,
        current_time: Optional[datetime.datetime] = None,
        strategy: str = "INTELLIGENT"
    ) -> RoutingEvaluationResponse:
        now = current_time or datetime.datetime.now(datetime.timezone.utc)
        current_weekday = now.weekday()
        current_hour = now.hour

        # Fetch all mandatory skills for this ticket (single or multi-skill)
        mandatory_skills = set()
        if ticket.intent and ticket.intent.required_skill_id:
            mandatory_skills.add(ticket.intent.required_skill_id)
        extra_skills = getattr(ticket, "required_skills", None) or getattr(ticket, "mandatory_skills", None)
        if extra_skills:
            if isinstance(extra_skills, (list, set)):
                mandatory_skills.update(extra_skills)
            elif isinstance(extra_skills, str):
                mandatory_skills.add(extra_skills)
        
        required_skill_id = ticket.intent.required_skill_id if ticket.intent else None
        required_lang = ticket.language_code

        # Fetch all agents with skills, languages, shifts
        all_agents: List[Agent] = self.db.query(Agent).all()

        eligible_agents: List[Tuple[Agent, float, Dict[str, float]]] = []
        rejected_candidates: List[RoutingRejectedCandidate] = []

        for agt in all_agents:
            reasons = []

            # 0. Multi-Tenant Boundary Isolation Check
            ticket_tenant = getattr(ticket, "tenant_id", "default_tenant") or "default_tenant"
            agent_tenant = getattr(agt, "tenant_id", "default_tenant") or "default_tenant"
            if agent_tenant != ticket_tenant:
                reasons.append(f"Tenant isolation mismatch: agent '{agent_tenant}' != ticket '{ticket_tenant}'")

            # 1. Active status check
            if agt.status != "ACTIVE":
                reasons.append(f"Status is {agt.status} (must be ACTIVE)")

            # 2. Shift check (Agent must have a shift covering current day/hour in UTC or shift timezone IST)
            ist_now = now + datetime.timedelta(hours=5, minutes=30)
            ist_weekday = ist_now.weekday()
            ist_hour = ist_now.hour

            has_shift = any(
                (s.day_of_week == current_weekday and s.start_hour <= current_hour < s.end_hour) or
                (s.day_of_week == ist_weekday and s.start_hour <= ist_hour < s.end_hour)
                for s in agt.shifts
            ) if agt.shifts else True
            if not has_shift:
                reasons.append(f"Agent off-shift (UTC {current_hour}:00, IST {ist_hour}:00, day {current_weekday})")

            # 3. Capacity check
            if agt.current_active_tickets >= agt.max_concurrency:
                reasons.append(f"At capacity limit ({agt.current_active_tickets}/{agt.max_concurrency})")

            # 4. Mandatory Multi-Skill check and Minimum Proficiency (>= 0.60)
            skill_map = {s.skill_id: s.proficiency_level for s in agt.skills}
            for req_skill in mandatory_skills:
                if req_skill not in skill_map:
                    reasons.append(f"Missing mandatory skill '{req_skill}'")
                elif skill_map[req_skill] < 0.60:
                    reasons.append(f"Skill proficiency in '{req_skill}' ({skill_map[req_skill]:.2f}) is below minimum threshold (0.60)")

            # 5. Language check
            lang_map = {l.language_code: l.fluency_score for l in agt.languages}
            if required_lang and required_lang != "en":
                if required_lang not in lang_map:
                    reasons.append(f"Agent does not speak required language '{required_lang}'")
                elif lang_map[required_lang] < 0.60:
                    reasons.append(f"Language proficiency in '{required_lang}' ({lang_map[required_lang]:.2f}) is below minimum threshold (0.60)")

            if reasons:
                rejected_candidates.append(RoutingRejectedCandidate(
                    agent_id=agt.agent_id,
                    agent_name=agt.name,
                    reasons=reasons
                ))
            else:
                # Stage 2: Calculate Weighted Score (Composite Multi-Skill Support)
                skill_proficiency = skill_map.get(required_skill_id, 0.70) if required_skill_id else 0.85
                # Composite multi-skill boost if agent possesses multiple complementary domain skills
                if len(skill_map) > 1:
                    avg_other_prof = sum(p for k, p in skill_map.items() if k != required_skill_id) / (len(skill_map) - 1)
                    skill_proficiency = (0.75 * skill_proficiency) + (0.25 * avg_other_prof)
                skill_score = skill_proficiency * 100.0

                # Language score
                if required_lang in lang_map:
                    lang_score = lang_map[required_lang] * 100.0
                elif "en" in lang_map:
                    lang_score = 60.0 # Partial fallback score
                else:
                    lang_score = 40.0

                # Available capacity score (remaining capacity percentage)
                avail_slots = agt.max_concurrency - agt.current_active_tickets
                capacity_score = (avail_slots / agt.max_concurrency) * 100.0

                # Experience score
                exp_score = agt.experience_score * 100.0

                # Score formula: 0.35S + 0.25L + 0.25C + 0.15E
                total_score = (
                    (settings.WEIGHT_SKILL * skill_score) +
                    (settings.WEIGHT_LANGUAGE * lang_score) +
                    (settings.WEIGHT_CAPACITY * capacity_score) +
                    (settings.WEIGHT_EXPERIENCE * exp_score)
                )

                score_breakdown = {
                    "skill_score": round(skill_score, 2),
                    "language_score": round(lang_score, 2),
                    "capacity_score": round(capacity_score, 2),
                    "experience_score": round(exp_score, 2),
                    "total_score": round(total_score, 2)
                }

                eligible_agents.append((agt, total_score, score_breakdown))

        # Sort eligible candidates deterministically:
        # 1. Total score descending
        # 2. Free capacity slots descending
        # 3. Agent ID ascending (tie-breaker)
        def agent_sort_key(item):
            agt, score, bd = item
            free_slots = agt.max_concurrency - agt.current_active_tickets
            # For agent_id, lower number wins tie (so negate for reverse=True)
            try:
                agt_num = int(agt.agent_id.replace("AGT-", ""))
            except Exception:
                agt_num = 999999
            return (round(score, 4), free_slots, -agt_num)

        eligible_agents.sort(key=agent_sort_key, reverse=True)

        candidate_scores: List[RoutingCandidateScore] = [
            RoutingCandidateScore(
                agent_id=agt.agent_id,
                agent_name=agt.name,
                skill_score=bd["skill_score"],
                language_score=bd["language_score"],
                capacity_score=bd["capacity_score"],
                experience_score=bd["experience_score"],
                total_score=bd["total_score"]
            )
            for agt, score, bd in eligible_agents
        ]

        if not eligible_agents:
            explanation = f"NO_ELIGIBLE_AGENT: No agents met all mandatory criteria (Skill: {required_skill_id}, Lang: {required_lang}, Capacity, Shifts). Ticket enqueued."
            return RoutingEvaluationResponse(
                ticket_id=ticket.ticket_id,
                eligible_count=0,
                selected_agent_id=None,
                final_score=None,
                explanation=explanation,
                candidate_scores=[],
                rejected_candidates=rejected_candidates
            )

        best_agent, best_score, best_breakdown = eligible_agents[0]
        explanation = (
            f"Assigned to {best_agent.agent_id} ({best_agent.name}) because the agent possesses required skill "
            f"'{required_skill_id or 'GENERAL'}', supports language '{required_lang}', is currently on shift, "
            f"and has {best_agent.max_concurrency - best_agent.current_active_tickets} available capacity slots. "
            f"Final routing score: {best_score:.2f}."
        )

        return RoutingEvaluationResponse(
            ticket_id=ticket.ticket_id,
            eligible_count=len(eligible_agents),
            selected_agent_id=best_agent.agent_id,
            final_score=best_score,
            explanation=explanation,
            candidate_scores=candidate_scores,
            rejected_candidates=rejected_candidates
        )

    def assign_ticket_atomically(
        self,
        ticket: Ticket,
        selected_agent_id: str,
        reason: str,
        actor_id: str = "SYSTEM_ROUTER"
    ) -> bool:
        """
        Atomically increments agent capacity via conditional SQL UPDATE guard,
        sets ticket assignment, and creates immutable audit events.
        """
        # Atomic conditional capacity reservation (concurrency safe across SQLite and PostgreSQL)
        rows_updated = self.db.query(Agent).filter(
            Agent.agent_id == selected_agent_id,
            Agent.current_active_tickets < Agent.max_concurrency
        ).update(
            {Agent.current_active_tickets: Agent.current_active_tickets + 1},
            synchronize_session=False
        )
        if rows_updated == 0:
            return False

        ticket.assigned_agent_id = selected_agent_id
        ticket.status = "ASSIGNED"

        # Record Assignment Event
        event_count = self.db.query(AssignmentEvent).filter(AssignmentEvent.ticket_id == ticket.ticket_id).count()
        assignment_id = f"ASN-{ticket.ticket_id}-{event_count + 1:03d}"
        
        asn_event = AssignmentEvent(
            assignment_id=assignment_id,
            ticket_id=ticket.ticket_id,
            agent_id=selected_agent_id,
            event_type="INITIAL_ASSIGN" if event_count == 0 else "REASSIGN",
            actor_id=actor_id,
            reason=reason
        )
        self.db.add(asn_event)
        self.db.commit()
        return True
