from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import uuid
from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.models.entities import Skill, Language, Intent, PriorityRule, BusinessCalendar, BusinessCalendarHoliday
from backend.app.services.sla.sla_calculator import COMPANY_HOLIDAYS_2026

router = APIRouter(prefix="/config", tags=["System Configuration"])

class RoutingWeightsUpdate(BaseModel):
    weight_skill: float
    weight_language: float
    weight_capacity: float
    weight_experience: float

class HolidayCreate(BaseModel):
    calendar_id: str = "DEFAULT_CALENDAR"
    holiday_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="Date in YYYY-MM-DD format")
    name: str

class HolidayResponse(BaseModel):
    holiday_id: str
    calendar_id: str
    holiday_date: str
    name: str

@router.get("")
def get_system_config(db: Session = Depends(get_db)) -> Dict[str, Any]:
    skills = db.query(Skill).all()
    languages = db.query(Language).all()
    intents = db.query(Intent).all()
    rules = db.query(PriorityRule).all()

    return {
        "routing_weights": {
            "skill": settings.WEIGHT_SKILL,
            "language": settings.WEIGHT_LANGUAGE,
            "capacity": settings.WEIGHT_CAPACITY,
            "experience": settings.WEIGHT_EXPERIENCE
        },
        "sla_policies": {
            "first_response_minutes": settings.SLA_FIRST_RESPONSE_MINUTES,
            "resolution_minutes": settings.SLA_RESOLUTION_MINUTES
        },
        "skills": [{"id": s.skill_id, "name": s.name, "tier": s.tier_level} for s in skills],
        "languages": [{"code": l.language_code, "name": l.name, "supported": l.is_supported} for l in languages],
        "intents": [{"id": i.intent_id, "name": i.name, "category": i.category, "default_priority": i.default_priority} for i in intents],
        "safety_rules": [{"id": r.rule_id, "name": r.rule_name, "priority": r.enforced_priority, "critical": r.is_safety_critical} for r in rules]
    }

@router.put("/weights")
def update_routing_weights(req: RoutingWeightsUpdate):
    settings.WEIGHT_SKILL = req.weight_skill
    settings.WEIGHT_LANGUAGE = req.weight_language
    settings.WEIGHT_CAPACITY = req.weight_capacity
    settings.WEIGHT_EXPERIENCE = req.weight_experience
    return {"message": "Weights updated successfully", "active_weights": req.model_dump()}

@router.get("/holidays")
def list_holidays(calendar_id: Optional[str] = None, db: Session = Depends(get_db)):
    """List all registered business calendar holidays including default 2026 enterprise holidays."""
    query = db.query(BusinessCalendarHoliday)
    if calendar_id:
        query = query.filter(BusinessCalendarHoliday.calendar_id == calendar_id)
    db_holidays = query.order_by(BusinessCalendarHoliday.holiday_date).all()
    
    return {
        "default_company_holidays": sorted(list(COMPANY_HOLIDAYS_2026)),
        "dynamic_calendar_holidays": [
            {
                "holiday_id": h.holiday_id,
                "calendar_id": h.calendar_id,
                "holiday_date": h.holiday_date,
                "name": h.name
            }
            for h in db_holidays
        ]
    }

@router.post("/holidays", status_code=status.HTTP_201_CREATED)
def add_holiday(req: HolidayCreate, db: Session = Depends(get_db)):
    """Create or register a new business calendar holiday for SLA deadline calculations."""
    # Ensure calendar exists
    calendar = db.query(BusinessCalendar).filter(BusinessCalendar.calendar_id == req.calendar_id).first()
    if not calendar:
        calendar = BusinessCalendar(
            calendar_id=req.calendar_id,
            name=f"{req.calendar_id} Calendar",
            timezone=settings.BUSINESS_TIMEZONE,
            work_start_hour=settings.BUSINESS_START_HOUR,
            work_end_hour=settings.BUSINESS_END_HOUR,
            work_days="0,1,2,3,4"
        )
        db.add(calendar)
        db.flush()

    # Check if duplicate date
    existing = db.query(BusinessCalendarHoliday).filter(
        BusinessCalendarHoliday.calendar_id == req.calendar_id,
        BusinessCalendarHoliday.holiday_date == req.holiday_date
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Holiday for date {req.holiday_date} already exists in calendar {req.calendar_id}")

    holiday_id = f"HOL-{uuid.uuid4().hex[:8].upper()}"
    new_holiday = BusinessCalendarHoliday(
        holiday_id=holiday_id,
        calendar_id=req.calendar_id,
        holiday_date=req.holiday_date,
        name=req.name
    )
    db.add(new_holiday)
    db.commit()
    db.refresh(new_holiday)

    return {
        "message": "Holiday registered successfully",
        "holiday": {
            "holiday_id": new_holiday.holiday_id,
            "calendar_id": new_holiday.calendar_id,
            "holiday_date": new_holiday.holiday_date,
            "name": new_holiday.name
        }
    }

@router.delete("/holidays/{holiday_id}")
def delete_holiday(holiday_id: str, db: Session = Depends(get_db)):
    """Remove a business calendar holiday."""
    h = db.query(BusinessCalendarHoliday).filter(BusinessCalendarHoliday.holiday_id == holiday_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Holiday not found")
    db.delete(h)
    db.commit()
    return {"message": f"Holiday {holiday_id} deleted successfully"}
