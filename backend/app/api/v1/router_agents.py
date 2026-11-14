from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from backend.app.core.database import get_db
from backend.app.models.entities import Agent
from backend.app.schemas.models import AgentResponse, AgentSkillItem, AgentLanguageItem, AgentShiftItem

router = APIRouter(prefix="/agents", tags=["Agents"])

@router.get("", response_model=List[AgentResponse])
def list_agents(
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Agent)
    if status:
        query = query.filter(Agent.status == status)
    
    agents = query.all()
    results = []
    for agt in agents:
        utilization = round((agt.current_active_tickets / agt.max_concurrency * 100.0), 1) if agt.max_concurrency else 0.0
        results.append(AgentResponse(
            agent_id=agt.agent_id,
            name=agt.name,
            email=agt.email,
            status=agt.status,
            max_concurrency=agt.max_concurrency,
            current_active_tickets=agt.current_active_tickets,
            experience_score=agt.experience_score,
            skills=[AgentSkillItem(skill_id=s.skill_id, proficiency_level=s.proficiency_level) for s in agt.skills],
            languages=[AgentLanguageItem(language_code=l.language_code, fluency_score=l.fluency_score) for l in agt.languages],
            shifts=[AgentShiftItem(day_of_week=sh.day_of_week, start_hour=sh.start_hour, end_hour=sh.end_hour, timezone=sh.timezone) for sh in agt.shifts],
            utilization_rate=utilization
        ))
    return results

@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(agent_id: str, db: Session = Depends(get_db)):
    agt = db.query(Agent).filter(Agent.agent_id == agent_id).first()
    if not agt:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    
    utilization = round((agt.current_active_tickets / agt.max_concurrency * 100.0), 1) if agt.max_concurrency else 0.0
    return AgentResponse(
        agent_id=agt.agent_id,
        name=agt.name,
        email=agt.email,
        status=agt.status,
        max_concurrency=agt.max_concurrency,
        current_active_tickets=agt.current_active_tickets,
        experience_score=agt.experience_score,
        skills=[AgentSkillItem(skill_id=s.skill_id, proficiency_level=s.proficiency_level) for s in agt.skills],
        languages=[AgentLanguageItem(language_code=l.language_code, fluency_score=l.fluency_score) for l in agt.languages],
        shifts=[AgentShiftItem(day_of_week=sh.day_of_week, start_hour=sh.start_hour, end_hour=sh.end_hour, timezone=sh.timezone) for sh in agt.shifts],
        utilization_rate=utilization
    )

@router.put("/{agent_id}/status", response_model=AgentResponse)
def update_agent_status(agent_id: str, status: str, db: Session = Depends(get_db)):
    agt = db.query(Agent).filter(Agent.agent_id == agent_id).first()
    if not agt:
        raise HTTPException(status_code=404, detail="Agent not found")
    agt.status = status.upper()
    db.commit()
    return get_agent(agent_id, db)
