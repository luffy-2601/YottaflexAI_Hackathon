from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from backend.app.core.database import get_db
from backend.app.models.entities import Ticket, Message, AssignmentEvent, SLAEvent, Resolution
from backend.app.schemas.models import (
    TicketCreateRequest, TicketResponse, TicketDetailResponse, MessageCreate,
    MessageResponse, TicketTransferRequest, TicketEscalateRequest,
    TicketReopenRequest, TicketResolveRequest, ResolutionResponse
)
from backend.app.services.tickets.ticket_service import TicketService

router = APIRouter(prefix="/tickets", tags=["Tickets"])

@router.get("", response_model=List[TicketResponse])
def list_tickets(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    channel_id: Optional[str] = None,
    intent_id: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    query = db.query(Ticket)
    if status:
        query = query.filter(Ticket.status == status)
    if priority:
        query = query.filter(Ticket.priority == priority)
    if channel_id:
        query = query.filter(Ticket.channel_id == channel_id)
    if intent_id:
        query = query.filter(Ticket.intent_id == intent_id)
    if search:
        query = query.filter(Ticket.subject.ilike(f"%{search}%") | Ticket.ticket_id.ilike(f"%{search}%"))
    
    return query.order_by(Ticket.created_at.desc()).offset(offset).limit(limit).all()

@router.post("", response_model=TicketResponse, status_code=201)
def create_ticket(req: TicketCreateRequest, db: Session = Depends(get_db)):
    service = TicketService(db)
    return service.create_ticket(req)

@router.get("/{ticket_id}", response_model=TicketDetailResponse)
def get_ticket_detail(ticket_id: str, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    return ticket

@router.post("/{ticket_id}/messages", response_model=MessageResponse, status_code=201)
def add_message(ticket_id: str, req: MessageCreate, db: Session = Depends(get_db)):
    service = TicketService(db)
    try:
        return service.add_message(ticket_id, req.sender_type, req.sender_id, req.body)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{ticket_id}/transfer", response_model=TicketResponse)
def transfer_ticket(ticket_id: str, req: TicketTransferRequest, db: Session = Depends(get_db)):
    service = TicketService(db)
    try:
        return service.transfer_ticket(ticket_id, req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{ticket_id}/escalate", response_model=TicketResponse)
def escalate_ticket(ticket_id: str, req: TicketEscalateRequest, db: Session = Depends(get_db)):
    service = TicketService(db)
    try:
        return service.escalate_ticket(ticket_id, req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{ticket_id}/reopen", response_model=TicketResponse)
def reopen_ticket(ticket_id: str, req: TicketReopenRequest, db: Session = Depends(get_db)):
    service = TicketService(db)
    try:
        return service.reopen_ticket(ticket_id, req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{ticket_id}/resolve", response_model=ResolutionResponse)
def resolve_ticket(ticket_id: str, req: TicketResolveRequest, db: Session = Depends(get_db)):
    service = TicketService(db)
    try:
        return service.resolve_ticket(ticket_id, req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
