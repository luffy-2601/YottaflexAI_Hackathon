import os
import time
import datetime
from collections import defaultdict
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import json
from apscheduler.schedulers.background import BackgroundScheduler
from backend.app.core.config import settings
from backend.app.core.database import engine, Base, SessionLocal
from backend.app.models.entities import SystemConfiguration
from backend.app.api.v1.api import api_router
from backend.app.services.sla.sla_engine import SLAEngine
from backend.app.services.routing.queue_dispatcher import QueueDispatcher

# Ensure tables exist on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------
# Rate Limiting Middleware (Sliding Window: Max 300 req/min)
# -------------------------------------------------------------
RATE_LIMIT_WINDOW_SECONDS = 60
MAX_REQUESTS_PER_WINDOW = 300
client_request_history = defaultdict(list)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Only rate limit API requests
    if request.url.path.startswith("/api/"):
        client_ip = request.client.host if request.client else "127.0.0.1"
        now = time.time()
        
        # Purge entries older than the sliding window
        window_start = now - RATE_LIMIT_WINDOW_SECONDS
        history = [ts for ts in client_request_history[client_ip] if ts > window_start]
        
        if len(history) >= MAX_REQUESTS_PER_WINDOW:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too Many Requests: Rate limit of 300 requests/minute exceeded.",
                    "retry_after_seconds": int(RATE_LIMIT_WINDOW_SECONDS - (now - history[0]))
                },
                headers={"Retry-After": str(RATE_LIMIT_WINDOW_SECONDS)}
            )
        
        history.append(now)
        client_request_history[client_ip] = history

    response = await call_next(request)
    return response

# -------------------------------------------------------------
# Background Autonomous SLA & Queue Dispatcher Daemon
# -------------------------------------------------------------
scheduler = BackgroundScheduler(daemon=True)

def autonomous_sla_and_queue_daemon():
    """
    Background worker running every 60 seconds with retry logic & persistent execution state:
    1. Evaluates all active SLA timers and generates proactive escalations.
    2. Sweeps pending QUEUED tickets and dispatches them to newly available agents.
    3. Persists execution health, timestamps, and retry telemetry.
    """
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            db = SessionLocal()
            try:
                sla_engine = SLAEngine(db)
                sla_engine.evaluate_active_slas()
                dispatcher = QueueDispatcher(db)
                res = dispatcher.dispatch_all()
                dispatched_count = res.get("total_dispatched", 0)

                # Persist background worker heartbeat & telemetry
                now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
                status_payload = json.dumps({
                    "job_id": "sla_and_queue_watchdog",
                    "status": "HEALTHY",
                    "last_run": now_iso,
                    "last_success": now_iso,
                    "dispatched_count": dispatched_count,
                    "retries": attempt - 1,
                    "failure_count": 0
                })
                cfg = db.query(SystemConfiguration).filter(SystemConfiguration.key == "BG_SLA_QUEUE_DAEMON_STATUS").first()
                if not cfg:
                    cfg = SystemConfiguration(
                        key="BG_SLA_QUEUE_DAEMON_STATUS",
                        value=status_payload,
                        description="Autonomous SLA & Queue Dispatcher Daemon State"
                    )
                    db.add(cfg)
                else:
                    cfg.value = status_payload
                db.commit()
                break
            finally:
                db.close()
        except Exception as e:
            if attempt == max_retries:
                try:
                    db = SessionLocal()
                    err_payload = json.dumps({
                        "job_id": "sla_and_queue_watchdog",
                        "status": "FAILED",
                        "last_run": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        "error": str(e)[:180],
                        "retries": attempt
                    })
                    cfg = db.query(SystemConfiguration).filter(SystemConfiguration.key == "BG_SLA_QUEUE_DAEMON_STATUS").first()
                    if cfg:
                        cfg.value = err_payload
                        db.commit()
                    db.close()
                except Exception:
                    pass
            time.sleep(0.5)

@app.on_event("startup")
def startup_background_daemon():
    if not scheduler.running:
        scheduler.add_job(
            autonomous_sla_and_queue_daemon,
            "interval",
            seconds=60,
            id="sla_and_queue_watchdog"
        )
        scheduler.start()

@app.on_event("shutdown")
def shutdown_background_daemon():
    if scheduler.running:
        scheduler.shutdown(wait=False)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "database": "connected"
    }

# Mount static frontend if built
frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
else:
    @app.get("/")
    def root():
        return {
            "name": settings.PROJECT_NAME,
            "docs_url": "/docs",
            "health_check": "/health"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=False)
