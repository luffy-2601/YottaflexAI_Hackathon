from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from backend.app.core.database import get_db
from backend.app.schemas.models import AnomalyResponse
from backend.app.services.anomalies.anomaly_service import AnomalyDetectionService

router = APIRouter(prefix="/anomalies", tags=["Anomaly Center"])

@router.get("", response_model=List[AnomalyResponse])
def list_anomalies(db: Session = Depends(get_db)):
    service = AnomalyDetectionService(db)
    return service.scan_anomalies()

@router.post("/scan", response_model=List[AnomalyResponse])
def trigger_anomaly_scan(db: Session = Depends(get_db)):
    service = AnomalyDetectionService(db)
    return service.scan_anomalies()
