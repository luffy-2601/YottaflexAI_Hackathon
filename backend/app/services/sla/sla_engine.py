import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.models.entities import (
    Ticket, SLAEvent, SLAHistoryEvent, SLAPolicy, Customer, Channel, BusinessCalendarHoliday
)
from backend.app.schemas.models import (
    SLAPolicyCreate, SLAPauseRequest, SLAResumeRequest, SLATicketDetailResponse, SLAHistoryEventResponse
)
from backend.app.services.sla.sla_calculator import SLACalculator, COMPANY_HOLIDAYS_2026
from backend.app.core.config import settings

def ensure_utc(dt: Optional[datetime.datetime]) -> Optional[datetime.datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=datetime.timezone.utc)
    return dt

AUTHORIZED_PAUSE_REASONS = {
    "WAITING_FOR_CUSTOMER",
    "WAITING_FOR_THIRD_PARTY",
    "WAITING_FOR_EXTERNAL_DEPENDENCY"
}

class UnauthorizedPauseError(ValueError):
    """Raised when an unauthorized or invalid pause reason is specified."""
    pass

class InvalidSLATransitionError(ValueError):
    """Raised when an invalid clock transition is attempted."""
    pass

class SLAEngine:
    """
    Centralized, independent SLA calculation, dual clock management,
    pause/resume orchestration, risk evaluation, and immutable audit event service.
    """
    def __init__(self, db: Session):
        self.db = db

    def resolve_policy(
        self,
        tenant_id: str = "default_tenant",
        channel_id: Optional[str] = None,
        priority: Optional[str] = None,
        category: Optional[str] = None,
        customer_tier: Optional[str] = None
    ) -> SLAPolicy:
        """
        Hierarchical SLA Policy Resolver.
        Finds the most specific active policy for tenant + channel + priority + tier,
        falling back to default parameters if no custom policy exists.
        """
        # Try exact tenant match
        query = self.db.query(SLAPolicy).filter(
            SLAPolicy.tenant_id == tenant_id,
            SLAPolicy.is_active == True
        )
        if priority:
            match_prio = query.filter(SLAPolicy.priority == priority).first()
            if match_prio:
                return match_prio

        generic_policy = query.first()
        if generic_policy:
            return generic_policy

        # Fallback to default synthesized policy from system settings
        prio = priority or "P3"
        fr_min = settings.SLA_FIRST_RESPONSE_MINUTES.get(prio, 60)
        res_min = settings.SLA_RESOLUTION_MINUTES.get(prio, 480)
        
        # Apply channel factor if known
        channel = self.db.query(Channel).filter(Channel.channel_id == channel_id).first()
        ch_factor = channel.default_sla_factor if channel else 1.0
        fr_min = max(1, int(fr_min * ch_factor))
        res_min = max(15, int(res_min * ch_factor))

        synth_id = f"POL-SYNTH-{tenant_id}-{prio}"
        existing_synth = self.db.query(SLAPolicy).filter(SLAPolicy.policy_id == synth_id).first()
        if existing_synth:
            return existing_synth

        synth_policy = SLAPolicy(
            policy_id=synth_id,
            tenant_id=tenant_id,
            name=f"Synthesized Policy ({tenant_id} - {prio})",
            channel_id=channel_id,
            priority=prio,
            customer_tier=customer_tier,
            first_response_minutes=fr_min,
            resolution_minutes=res_min,
            business_hours_only=(prio != "P1"),
            timezone=settings.BUSINESS_TIMEZONE,
            work_start_hour=settings.BUSINESS_START_HOUR,
            work_end_hour=settings.BUSINESS_END_HOUR,
            work_days="0,1,2,3,4",
            escalation_level_1_ratio=0.70,
            escalation_level_2_ratio=0.90,
            is_active=True
        )
        try:
            self.db.add(synth_policy)
            self.db.flush()
        except Exception:
            self.db.rollback()
        return synth_policy

    def record_history_event(
        self,
        ticket_id: str,
        sla_id: str,
        event_type: str,
        actor: str = "SYSTEM",
        reason: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None
    ) -> Optional[SLAHistoryEvent]:
        """
        Records an immutable SLA history event with idempotency protection.
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        if idempotency_key:
            existing = self.db.query(SLAHistoryEvent).filter(
                SLAHistoryEvent.idempotency_key == idempotency_key
            ).first()
            if existing:
                return existing

        event_count = self.db.query(SLAHistoryEvent).filter(SLAHistoryEvent.ticket_id == ticket_id).count()
        history_id = f"SLAHIST-{ticket_id}-{event_count + 1:03d}"

        evt = SLAHistoryEvent(
            history_id=history_id,
            ticket_id=ticket_id,
            sla_id=sla_id,
            event_type=event_type,
            actor=actor,
            reason=reason,
            idempotency_key=idempotency_key,
            payload=payload,
            created_at=now
        )
        self.db.add(evt)
        self.db.flush()
        return evt

    def create_sla_for_ticket(self, ticket: Ticket, actor: str = "SYSTEM") -> SLAEvent:
        """
        Initializes dual independent SLA clocks, calculates deadlines,
        and records initial immutable SLA lifecycle events.
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        customer = self.db.query(Customer).filter(Customer.customer_id == ticket.customer_id).first()
        cust_tier = customer.tier if customer else "STANDARD"

        policy = self.resolve_policy(
            tenant_id=ticket.tenant_id,
            channel_id=ticket.channel_id,
            priority=ticket.priority,
            customer_tier=cust_tier
        )

        # Calculate Deadlines
        channel = self.db.query(Channel).filter(Channel.channel_id == ticket.channel_id).first()
        ch_factor = channel.default_sla_factor if channel else 1.0

        # Dynamic DB holidays + Default 2026 Company Holidays
        db_holidays = {h.holiday_date for h in self.db.query(BusinessCalendarHoliday).all()}
        all_holidays = COMPANY_HOLIDAYS_2026.union(db_holidays)

        fr_due, res_due = SLACalculator.calculate_deadlines(
            priority=ticket.priority,
            channel_id=ticket.channel_id,
            created_at=now,
            channel_sla_factor=ch_factor,
            holidays=all_holidays
        )

        sla_record = SLAEvent(
            sla_id=f"SLA-{ticket.ticket_id}",
            ticket_id=ticket.ticket_id,
            policy_id=policy.policy_id if policy else None,
            first_response_clock_started_at=now,
            first_response_clock_stopped_at=None,
            first_response_due_at=fr_due,
            first_response_actual_at=None,
            is_first_response_breached=False,
            resolution_clock_started_at=now,
            resolution_clock_stopped_at=None,
            resolution_due_at=res_due,
            resolution_actual_at=None,
            is_resolution_breached=False,
            status="RUNNING",
            risk_level="ON_TRACK",
            escalation_level=0,
            is_paused=False,
            total_paused_seconds=0,
            created_at=now,
            updated_at=now
        )
        self.db.add(sla_record)
        self.db.flush()

        # Emit audit events
        self.record_history_event(
            ticket_id=ticket.ticket_id,
            sla_id=sla_record.sla_id,
            event_type="SLA_CREATED",
            actor=actor,
            reason="Ticket accepted into system; SLA initialized.",
            payload={"first_response_due": fr_due.isoformat(), "resolution_due": res_due.isoformat()}
        )
        self.record_history_event(
            ticket_id=ticket.ticket_id,
            sla_id=sla_record.sla_id,
            event_type="FIRST_RESPONSE_CLOCK_STARTED",
            actor=actor,
            reason="First Response SLA clock running."
        )
        self.record_history_event(
            ticket_id=ticket.ticket_id,
            sla_id=sla_record.sla_id,
            event_type="RESOLUTION_CLOCK_STARTED",
            actor=actor,
            reason="Resolution SLA clock running."
        )

        return sla_record

    def record_first_response(
        self,
        ticket_id: str,
        actor: str = "AGENT",
        is_automated_ack: bool = False
    ) -> Optional[SLAEvent]:
        """
        Stops the First Response SLA clock on human agent communication.
        Automated acknowledgments do NOT satisfy or stop the First Response SLA clock.
        """
        sla = self.db.query(SLAEvent).filter(SLAEvent.ticket_id == ticket_id).first()
        if not sla:
            return None

        # Automated acknowledgement exclusion rule
        if is_automated_ack:
            self.record_history_event(
                ticket_id=ticket_id,
                sla_id=sla.sla_id,
                event_type="AUTO_ACK_RECEIVED",
                actor=actor,
                reason="Automated acknowledgment received; first response clock continues running."
            )
            return sla

        # Already stopped
        if sla.first_response_clock_stopped_at is not None:
            return sla

        now = datetime.datetime.now(datetime.timezone.utc)
        sla.first_response_clock_stopped_at = now
        sla.first_response_actual_at = now

        if ensure_utc(now) > ensure_utc(sla.first_response_due_at):
            sla.is_first_response_breached = True
            event_type = "FIRST_RESPONSE_BREACHED"
            reason = f"First response delivered {int((ensure_utc(now) - ensure_utc(sla.first_response_due_at)).total_seconds() / 60)}m after deadline."
        else:
            sla.is_first_response_breached = False
            event_type = "FIRST_RESPONSE_MET"
            reason = "First response delivered within SLA deadline."

        sla.updated_at = now
        self.record_history_event(
            ticket_id=ticket_id,
            sla_id=sla.sla_id,
            event_type=event_type,
            actor=actor,
            reason=reason,
            payload={"first_response_actual_at": now.isoformat()}
        )
        return sla

    def record_resolution(
        self,
        ticket_id: str,
        actor: str = "AGENT",
        reason: Optional[str] = None
    ) -> Optional[SLAEvent]:
        """
        Stops the Resolution SLA clock upon reaching a valid resolved state.
        """
        sla = self.db.query(SLAEvent).filter(SLAEvent.ticket_id == ticket_id).first()
        if not sla:
            return None

        now = datetime.datetime.now(datetime.timezone.utc)
        sla.resolution_clock_stopped_at = now
        sla.resolution_actual_at = now

        if ensure_utc(now) > ensure_utc(sla.resolution_due_at):
            sla.is_resolution_breached = True
            sla.status = "BREACHED"
            sla.risk_level = "BREACHED"
            event_type = "RESOLUTION_BREACHED"
            res_reason = "Resolution completed after SLA deadline."
        else:
            sla.is_resolution_breached = False
            sla.status = "MET"
            sla.risk_level = "MET"
            event_type = "RESOLUTION_MET"
            res_reason = "Resolution completed within SLA deadline."

        sla.updated_at = now
        self.record_history_event(
            ticket_id=ticket_id,
            sla_id=sla.sla_id,
            event_type=event_type,
            actor=actor,
            reason=reason or res_reason,
            payload={"resolution_actual_at": now.isoformat()}
        )
        return sla

    def pause_sla(
        self,
        ticket_id: str,
        req: SLAPauseRequest
    ) -> SLAEvent:
        """
        Pauses SLA clock with authorized reason verification.
        Unauthorized pause reasons are rejected with UnauthorizedPauseError.
        """
        if req.reason not in AUTHORIZED_PAUSE_REASONS:
            raise UnauthorizedPauseError(
                f"Unauthorized pause reason '{req.reason}'. Authorized reasons: {sorted(list(AUTHORIZED_PAUSE_REASONS))}"
            )

        sla = self.db.query(SLAEvent).filter(SLAEvent.ticket_id == ticket_id).first()
        if not sla:
            raise ValueError(f"SLA record for ticket {ticket_id} not found")

        if sla.is_paused:
            return sla # Idempotent already paused

        now = datetime.datetime.now(datetime.timezone.utc)
        sla.is_paused = True
        sla.paused_at = now
        sla.pause_reason = req.reason
        sla.paused_by = req.authorized_by
        sla.status = "PAUSED"
        sla.risk_level = "PAUSED"
        sla.updated_at = now

        self.record_history_event(
            ticket_id=ticket_id,
            sla_id=sla.sla_id,
            event_type="SLA_PAUSED",
            actor=req.authorized_by,
            reason=f"SLA paused for authorized reason: {req.reason}",
            payload={"paused_at": now.isoformat(), "pause_reason": req.reason}
        )
        self.db.commit()
        self.db.refresh(sla)
        return sla

    def resume_sla(
        self,
        ticket_id: str,
        req: SLAResumeRequest
    ) -> SLAEvent:
        """
        Resumes SLA clock, extends deadlines by elapsed paused duration,
        and records SLA_RESUMED event.
        """
        sla = self.db.query(SLAEvent).filter(SLAEvent.ticket_id == ticket_id).first()
        if not sla:
            raise ValueError(f"SLA record for ticket {ticket_id} not found")

        if not sla.is_paused:
            return sla # Idempotent not paused

        now = datetime.datetime.now(datetime.timezone.utc)
        paused_since = ensure_utc(sla.paused_at) or now
        pause_delta = now - paused_since
        pause_seconds = int(pause_delta.total_seconds())

        # Extend deadlines
        sla.first_response_due_at = ensure_utc(sla.first_response_due_at) + pause_delta
        sla.resolution_due_at = ensure_utc(sla.resolution_due_at) + pause_delta
        sla.total_paused_seconds += pause_seconds
        sla.is_paused = False
        sla.paused_at = None
        sla.status = "RUNNING"
        sla.risk_level = "ON_TRACK"
        sla.updated_at = now

        self.record_history_event(
            ticket_id=ticket_id,
            sla_id=sla.sla_id,
            event_type="SLA_RESUMED",
            actor=req.authorized_by,
            reason=req.reason or "SLA resumed; deadlines extended by pause duration.",
            payload={
                "resumed_at": now.isoformat(),
                "extended_by_seconds": pause_seconds,
                "new_first_response_due": sla.first_response_due_at.isoformat(),
                "new_resolution_due": sla.resolution_due_at.isoformat()
            }
        )
        self.db.commit()
        self.db.refresh(sla)
        return sla

    def evaluate_risk_and_escalate(self, ticket_id: str) -> SLAEvent:
        """
        Evaluates remaining business time, updates risk state (ON_TRACK, AT_RISK, CRITICAL, BREACHED),
        and applies proactive multi-level escalation with idempotency keys.
        """
        sla = self.db.query(SLAEvent).filter(SLAEvent.ticket_id == ticket_id).first()
        if not sla or sla.status in ["MET", "PAUSED"]:
            return sla

        now = datetime.datetime.now(datetime.timezone.utc)
        ticket = self.db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
        created_at = ensure_utc(ticket.created_at) if ticket else ensure_utc(sla.created_at)
        target_due = ensure_utc(sla.resolution_due_at)

        total_seconds = max(1.0, (target_due - created_at).total_seconds())
        elapsed_seconds = max(0.0, (now - created_at).total_seconds())
        ratio_consumed = elapsed_seconds / total_seconds

        old_risk = sla.risk_level
        if now > target_due:
            new_risk = "BREACHED"
        elif ratio_consumed >= 0.90:
            new_risk = "CRITICAL"
        elif ratio_consumed >= 0.70:
            new_risk = "AT_RISK"
        else:
            new_risk = "ON_TRACK"

        sla.risk_level = new_risk

        # Escalation Levels 0 -> 1 -> 2 -> 3
        current_date_str = now.strftime("%Y%m%d%H")
        if new_risk == "AT_RISK" and sla.escalation_level < 1:
            sla.escalation_level = 1
            idem_key = f"ESC-{ticket_id}-L1-{current_date_str}"
            self.record_history_event(
                ticket_id=ticket_id,
                sla_id=sla.sla_id,
                event_type="SLA_AT_RISK",
                actor="SLA_MONITOR",
                reason=f"SLA reached Level 1 Warning: {int(ratio_consumed*100)}% of target time elapsed.",
                idempotency_key=idem_key
            )
        elif new_risk == "CRITICAL" and sla.escalation_level < 2:
            sla.escalation_level = 2
            idem_key = f"ESC-{ticket_id}-L2-{current_date_str}"
            self.record_history_event(
                ticket_id=ticket_id,
                sla_id=sla.sla_id,
                event_type="SLA_CRITICAL",
                actor="SLA_MONITOR",
                reason=f"SLA reached Level 2 Supervisor Escalation: {int(ratio_consumed*100)}% of target time elapsed.",
                idempotency_key=idem_key
            )
        elif new_risk == "BREACHED" and sla.escalation_level < 3:
            sla.escalation_level = 3
            sla.status = "BREACHED"
            idem_key = f"ESC-{ticket_id}-L3-{current_date_str}"
            self.record_history_event(
                ticket_id=ticket_id,
                sla_id=sla.sla_id,
                event_type="SLA_BREACHED",
                actor="SLA_MONITOR",
                reason="SLA Resolution Target Breached.",
                idempotency_key=idem_key
            )

        self.db.commit()
        self.db.refresh(sla)
        return sla
