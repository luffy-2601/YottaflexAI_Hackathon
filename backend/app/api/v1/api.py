from fastapi import APIRouter
from backend.app.api.v1.router_tickets import router as tickets_router
from backend.app.api.v1.router_agents import router as agents_router
from backend.app.api.v1.router_routing import router as routing_router
from backend.app.api.v1.router_sla import router as sla_router
from backend.app.api.v1.router_anomalies import router as anomalies_router
from backend.app.api.v1.router_analytics import router as analytics_router
from backend.app.api.v1.router_evaluation import router as evaluation_router
from backend.app.api.v1.router_config import router as config_router
from backend.app.api.v1.router_auth import router as auth_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(tickets_router)
api_router.include_router(agents_router)
api_router.include_router(routing_router)
api_router.include_router(sla_router)
api_router.include_router(anomalies_router)
api_router.include_router(analytics_router)
api_router.include_router(evaluation_router)
api_router.include_router(config_router)
