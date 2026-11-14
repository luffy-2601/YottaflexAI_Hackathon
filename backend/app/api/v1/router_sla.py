import datetime
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from backend.app.core.database import get_db
from backend.app.models.entities import SLAEvent, Ticket, SLAPolicy, SLAHistoryEvent
from backend.app.schemas.models import (
    SLAPauseRequest, SLAResumeRequest, SLAPolicyCreate, SLAPolicyResponse,
    SLAHistoryEventResponse, SLATicketDetailResponse
)
from backend.app.services.sla.sla_engine import SLAEngine, UnauthorizedPauseError

router = APIRouter(prefix="/sla", tags=["SLA Orchestration & Engine"])

# -----------------------------------------------------------------------------
# Existing Summary and Active endpoints (Preserved for Frontend compatibility)
# -----------------------------------------------------------------------------

@router.get("/summary")
def get_sla_summary(db: Session = Depends(get_db)):
    total = db.query(SLAEvent).count()
    breached = db.query(SLAEvent).filter(
        (SLAEvent.is_first_response_breached == True) | (SLAEvent.is_resolution_breached == True)
    ).count()
    compliance_pct = round(((total - breached) / total * 100.0) if total > 0 else 100.0, 1)

    now = datetime.datetime.now(datetime.timezone.utc)
    approaching = db.query(SLAEvent).join(Ticket).filter(
        Ticket.status.notin_(["RESOLVED", "CLOSED"]),
        SLAEvent.resolution_due_at > now,
        SLAEvent.resolution_due_at <= (now + datetime.timedelta(hours=2))
    ).count()

    return {
        "total_monitored": total,
        "breached_count": breached,
        "compliance_pct": compliance_pct,
        "approaching_breach_count": approaching
    }

@router.get("/active")
def get_active_slas(limit: int = Query(50, ge=1, le=100), db: Session = Depends(get_db)):
    now = datetime.datetime.now(datetime.timezone.utc)
    active_records = (
        db.query(SLAEvent, Ticket)
        .join(Ticket, SLAEvent.ticket_id == Ticket.ticket_id)
        .filter(Ticket.status.notin_(["RESOLVED", "CLOSED"]))
        .order_by(SLAEvent.resolution_due_at.asc())
        .limit(limit)
        .all()
    )

    results = []
    for sla, tkt in active_records:
        mins_remaining = int((sla.resolution_due_at - now).total_seconds() / 60)
        results.append({
            "ticket_id": tkt.ticket_id,
            "subject": tkt.subject,
            "priority": tkt.priority,
            "channel_id": tkt.channel_id,
            "status": tkt.status,
            "assigned_agent_id": tkt.assigned_agent_id,
            "first_response_due_at": sla.first_response_due_at,
            "resolution_due_at": sla.resolution_due_at,
            "minutes_remaining": mins_remaining,
            "risk_level": getattr(sla, "risk_level", "ON_TRACK"),
            "is_breached": mins_remaining < 0 or sla.is_first_response_breached or sla.is_resolution_breached
        })
    return results

# -----------------------------------------------------------------------------
# Enterprise Centralized SLA Engine Endpoints (Phase 2.8)
# -----------------------------------------------------------------------------

@router.get("/dashboard")
def get_sla_dashboard(db: Session = Depends(get_db)):
    """
    Centralized SLA dashboard metrics with dual-clock compliance,
    risk breakdowns (ON_TRACK, AT_RISK, CRITICAL, BREACHED, PAUSED), and escalation counts.
    """
    total = db.query(SLAEvent).count()
    breached = db.query(SLAEvent).filter(
        (SLAEvent.is_first_response_breached == True) | (SLAEvent.is_resolution_breached == True)
    ).count()
    compliance_pct = round(((total - breached) / total * 100.0) if total > 0 else 100.0, 1)

    on_track_count = db.query(SLAEvent).filter(SLAEvent.risk_level == "ON_TRACK", SLAEvent.status == "RUNNING").count()
    at_risk_count = db.query(SLAEvent).filter(SLAEvent.risk_level == "AT_RISK").count()
    critical_count = db.query(SLAEvent).filter(SLAEvent.risk_level == "CRITICAL").count()
    paused_count = db.query(SLAEvent).filter(SLAEvent.is_paused == True).count()

    return {
        "total_slas": total,
        "compliance_pct": compliance_pct,
        "breached_count": breached,
        "on_track_count": on_track_count,
        "at_risk_count": at_risk_count,
        "critical_count": critical_count,
        "paused_count": paused_count,
        "escalations": {
            "level_1_warnings": db.query(SLAEvent).filter(SLAEvent.escalation_level == 1).count(),
            "level_2_supervisor": db.query(SLAEvent).filter(SLAEvent.escalation_level == 2).count(),
            "level_3_manager": db.query(SLAEvent).filter(SLAEvent.escalation_level >= 3).count()
        }
    }

@router.get("/tickets/{ticket_id}", response_model=SLATicketDetailResponse)
def get_ticket_sla_details(ticket_id: str, db: Session = Depends(get_db)):
    """
    Fetches dual independent clock status, remaining business minutes,
    risk state, pause duration, and immutable SLA audit history.
    """
    engine = SLAEngine(db)
    engine.evaluate_risk_and_escalate(ticket_id)

    sla = db.query(SLAEvent).filter(SLAEvent.ticket_id == ticket_id).first()
    if not sla:
        raise HTTPException(status_code=404, detail=f"SLA record for ticket {ticket_id} not found")

    now = datetime.datetime.now(datetime.timezone.utc)
    fr_remaining = max(0.0, (sla.first_response_due_at - now).total_seconds() / 60) if not sla.first_response_clock_stopped_at else 0.0
    res_remaining = max(0.0, (sla.resolution_due_at - now).total_seconds() / 60) if not sla.resolution_clock_stopped_at else 0.0

    history_events = db.query(SLAHistoryEvent).filter(
        SLAHistoryEvent.ticket_id == ticket_id
    ).order_by(SLAHistoryEvent.created_at.asc()).all()

    return SLATicketDetailResponse(
        sla_id=sla.sla_id,
        ticket_id=sla.ticket_id,
        policy_id=sla.policy_id,
        status=sla.status,
        risk_level=sla.risk_level,
        escalation_level=sla.escalation_level,
        is_paused=sla.is_paused,
        pause_reason=sla.pause_reason,
        total_paused_seconds=sla.total_paused_seconds,
        first_response_due_at=sla.first_response_due_at,
        first_response_actual_at=sla.first_response_actual_at,
        is_first_response_breached=sla.is_first_response_breached,
        first_response_remaining_business_minutes=round(fr_remaining, 1),
        resolution_due_at=sla.resolution_due_at,
        resolution_actual_at=sla.resolution_actual_at,
        is_resolution_breached=sla.is_resolution_breached,
        resolution_remaining_business_minutes=round(res_remaining, 1),
        history_events=[
            SLAHistoryEventResponse.model_validate(e) for e in history_events
        ]
    )

@router.get("/tickets/{ticket_id}/history", response_model=List[SLAHistoryEventResponse])
def get_ticket_sla_history(ticket_id: str, db: Session = Depends(get_db)):
    """
    Returns full immutable audit trail of SLA clock changes, pauses, resumes, and escalations.
    """
    events = db.query(SLAHistoryEvent).filter(
        SLAHistoryEvent.ticket_id == ticket_id
    ).order_by(SLAHistoryEvent.created_at.asc()).all()
    return events

@router.post("/tickets/{ticket_id}/pause")
def pause_ticket_sla(ticket_id: str, req: SLAPauseRequest, db: Session = Depends(get_db)):
    """
    Authorized SLA clock pause. Requires recognized policy reason.
    """
    engine = SLAEngine(db)
    try:
        sla = engine.pause_sla(ticket_id, req)
        return {
            "status": "PAUSED",
            "ticket_id": ticket_id,
            "paused_at": sla.paused_at,
            "pause_reason": sla.pause_reason,
            "authorized_by": sla.paused_by
        }
    except UnauthorizedPauseError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/tickets/{ticket_id}/resume")
def resume_ticket_sla(ticket_id: str, req: SLAResumeRequest, db: Session = Depends(get_db)):
    """
    Resumes SLA clock, extends deadlines by total paused duration, and emits SLA_RESUMED.
    """
    engine = SLAEngine(db)
    sla = engine.resume_sla(ticket_id, req)
    return {
        "status": "RESUMED",
        "ticket_id": ticket_id,
        "total_paused_seconds": sla.total_paused_seconds,
        "new_first_response_due_at": sla.first_response_due_at,
        "new_resolution_due_at": sla.resolution_due_at
    }

# -----------------------------------------------------------------------------
# SLA Policy CRUD (Tenant, Channel, Priority, Customer Tier configurable)
# -----------------------------------------------------------------------------

@router.get("/policies", response_model=List[SLAPolicyResponse])
def list_sla_policies(
    tenant_id: str = Query("default_tenant"),
    db: Session = Depends(get_db)
):
    policies = db.query(SLAPolicy).filter(
        SLAPolicy.tenant_id == tenant_id
    ).all()
    return policies

@router.post("/policies", response_model=SLAPolicyResponse, status_code=status.HTTP_201_CREATED)
def create_sla_policy(
    policy: SLAPolicyCreate,
    db: Session = Depends(get_db)
):
    existing = db.query(SLAPolicy).filter(SLAPolicy.policy_id == policy.policy_id).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Policy with ID '{policy.policy_id}' already exists")

    new_policy = SLAPolicy(**policy.model_dump())
    db.add(new_policy)
    db.commit()
    db.refresh(new_policy)
    return new_policy

@router.patch("/policies/{policy_id}", response_model=SLAPolicyResponse)
def update_sla_policy(
    policy_id: str,
    update_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    pol = db.query(SLAPolicy).filter(SLAPolicy.policy_id == policy_id).first()
    if not pol:
        raise HTTPException(status_code=404, detail=f"Policy '{policy_id}' not found")

    for key, val in update_data.items():
        if hasattr(pol, key):
            setattr(pol, key, val)

    db.commit()
    db.refresh(pol)
    return pol

# -----------------------------------------------------------------------------
# Genuine Machine Learning Predictive Endpoints
# -----------------------------------------------------------------------------

@router.get("/tickets/{ticket_id}/predict")
def predict_ticket_breach(ticket_id: str, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    from backend.app.services.sla.predictive_model import sla_predictor
    if not sla_predictor.model:
        # Train on demand if not already trained
        sla_predictor.train_from_database(db)

    pred = sla_predictor.predict_breach_probability(ticket)
    return pred

@router.post("/train-predictive-model")
def train_predictive_model(db: Session = Depends(get_db)):
    from backend.app.services.sla.predictive_model import sla_predictor
    result = sla_predictor.train_from_database(db)
    return result
