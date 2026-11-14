from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from backend.app.core.database import get_db
from backend.app.models.entities import Ticket, RoutingDecision
from backend.app.schemas.models import RoutingEvaluationResponse, ClassificationRequest, ClassificationResult
from backend.app.services.routing.routing_engine import IntelligentRoutingEngine
from backend.app.services.classification.classifier import ClassificationEngine

router = APIRouter(prefix="/routing", tags=["Routing Engine"])

@router.post("/evaluate/{ticket_id}", response_model=RoutingEvaluationResponse)
def evaluate_routing(ticket_id: str, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    engine = IntelligentRoutingEngine(db)
    return engine.evaluate_routing(ticket)

@router.get("/decisions/{ticket_id}")
def get_routing_decisions(ticket_id: str, db: Session = Depends(get_db)):
    decisions = db.query(RoutingDecision).filter(RoutingDecision.ticket_id == ticket_id).order_by(RoutingDecision.created_at.desc()).all()
    return decisions

@router.post("/classify", response_model=ClassificationResult)
def classify_text(req: ClassificationRequest):
    return ClassificationEngine.classify(req.subject, req.body)

@router.post("/dispatch-queue")
def dispatch_queue(tenant_id: Optional[str] = "default_tenant", db: Session = Depends(get_db)):
    from backend.app.services.routing.queue_dispatcher import QueueDispatcher
    dispatcher = QueueDispatcher(db)
    return dispatcher.dispatch_all(tenant_id=tenant_id)
