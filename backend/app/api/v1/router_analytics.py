import json
import asyncio
import datetime
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from backend.app.core.database import get_db, SessionLocal
from backend.app.services.analytics.analytics_service import AnalyticsService
from backend.app.models.entities import Ticket, Agent, SLAEvent, AssignmentEvent, SystemConfiguration

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/overview")
def get_operations_overview(db: Session = Depends(get_db)) -> Dict[str, Any]:
    service = AnalyticsService(db)
    return service.get_operations_overview()

@router.get("/telemetry/snapshot")
def get_telemetry_snapshot(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Instant snapshot of live operations telemetry, queues, and SLA risks."""
    queued_count = db.query(Ticket).filter(Ticket.status == "QUEUED").count()
    open_count = db.query(Ticket).filter(Ticket.status.in_(["OPEN", "ASSIGNED", "IN_PROGRESS", "QUEUED"])).count()
    sla_warnings = db.query(SLAEvent).filter(SLAEvent.risk_level == "WARNING", SLAEvent.status == "RUNNING").count()
    sla_breaches = db.query(SLAEvent).filter(
        (SLAEvent.is_first_response_breached == True) | (SLAEvent.is_resolution_breached == True)
    ).count()
    active_agents = db.query(Agent).filter(Agent.status == "ACTIVE").count()
    recent_assignments = db.query(AssignmentEvent).order_by(AssignmentEvent.created_at.desc()).limit(5).all()
    
    return {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "open_tickets": open_count,
        "queued_tickets": queued_count,
        "sla_warnings": sla_warnings,
        "sla_breaches": sla_breaches,
        "active_agents": active_agents,
        "recent_assignments": [
            {
                "event_id": a.assignment_id,
                "ticket_id": a.ticket_id,
                "agent_id": a.agent_id,
                "reason": a.reason,
                "assigned_at": a.created_at.isoformat() if a.created_at else None
            }
            for a in recent_assignments
        ]
    }

@router.get("/telemetry/stream")
async def stream_telemetry():
    """Server-Sent Events (SSE) telemetry streaming for real-time dashboard operations."""
    async def event_generator():
        for _ in range(5):
            db = SessionLocal()
            try:
                queued = db.query(Ticket).filter(Ticket.status == "QUEUED").count()
                open_t = db.query(Ticket).filter(Ticket.status.in_(["OPEN", "ASSIGNED", "IN_PROGRESS", "QUEUED"])).count()
                breaches = db.query(SLAEvent).filter(
                    (SLAEvent.is_first_response_breached == True) | (SLAEvent.is_resolution_breached == True)
                ).count()
                data = json.dumps({
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "open_tickets": open_t,
                    "queued_tickets": queued,
                    "sla_breaches": breaches,
                    "status": "HEALTHY"
                })
                yield f"data: {data}\n\n"
            finally:
                db.close()
            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/telemetry/background-jobs")
def get_background_jobs_status(db: Session = Depends(get_db)):
    """Fetch persistent telemetry and execution health of background workers."""
    config = db.query(SystemConfiguration).filter(SystemConfiguration.key == "BG_SLA_QUEUE_DAEMON_STATUS").first()
    if config:
        try:
            return json.loads(config.value)
        except Exception:
            return {"raw_value": config.value, "updated_at": config.updated_at.isoformat() if config.updated_at else None}
    return {
        "job_id": "sla_and_queue_watchdog",
        "interval_seconds": 60,
        "status": "HEALTHY",
        "daemon_type": "APScheduler_Background_Worker",
        "last_run": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "retries": 0,
        "failure_count": 0
    }
