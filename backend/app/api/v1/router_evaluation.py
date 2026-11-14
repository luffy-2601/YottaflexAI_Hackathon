from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.schemas.models import BenchmarkComparisonResponse
from backend.app.services.evaluation.benchmark_service import EvaluationBenchmarkService

router = APIRouter(prefix="/evaluation", tags=["Evaluation & Benchmarks"])

@router.get("/benchmarks", response_model=BenchmarkComparisonResponse)
def get_benchmarks(sample_limit: int = Query(200, ge=20, le=1000), db: Session = Depends(get_db)):
    service = EvaluationBenchmarkService(db)
    return service.run_benchmark(sample_limit=sample_limit)

@router.post("/simulate", response_model=BenchmarkComparisonResponse)
def run_simulation(sample_limit: int = Query(200, ge=20, le=1000), db: Session = Depends(get_db)):
    service = EvaluationBenchmarkService(db)
    return service.run_benchmark(sample_limit=sample_limit)
