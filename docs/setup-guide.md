# OmniRoute AI — Local Setup and Deployment Guide

## 1. System Requirements

- **Python**: Version 3.12 or newer.
- **Node.js**: Version 20 or newer (with `npm`).
- **Operating System**: Windows, Linux, or macOS.
- **Database**: SQLite3 (bundled zero-setup runtime) or PostgreSQL 14+ for production.

---

## 2. Quickstart Installation (Single Command)

### Step 1: Install Python Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Install Frontend Dependencies & Build Bundle
```bash
cd frontend
npm install
npm run build
cd ..
```
*Note: The FastAPI backend automatically serves the compiled `frontend/dist` static assets at `http://localhost:8000/`.*

---

## 3. Running the Server

Start the FastAPI application with Uvicorn:
```bash
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

- **Frontend User Interface**: `http://localhost:8000/`
- **Interactive OpenAPI Docs**: `http://localhost:8000/docs`
- **ReDoc Documentation**: `http://localhost:8000/redoc`

---

## 4. Environment Configuration (`.env`)

Copy the example environment configuration:
```bash
cp .env.example .env
```

| Variable | Default Value | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./omnichannel.db` | Relational database connection string |
| `SECRET_KEY` | `omniroute-enterprise-secure-jwt-key-2026` | Cryptographic secret for signing JWT tokens |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` | JWT token validity lifespan (8 hours) |
| `API_V1_STR` | `/api/v1` | Base API prefix |
| `RATE_LIMIT_PER_MINUTE` | `300` | Sliding-window API rate limit per client IP |

---

## 5. Docker Deployment

Deploy with Docker Compose:
```bash
docker-compose up --build -d
```
Stop services:
```bash
docker-compose down
```

---

## 6. Default Demo Credentials (Configured for Evaluators)

| Role | Email | Password | Permissions |
|---|---|---|---|
| **System Admin** | `admin.evaluator@hackathon.org` | `Password123!` | Full administrative access, tenant settings, analytics |
| **Support Agent** | `agent.smith@matrix.com` | `Password123!` | Ticket assignment, messages, resolution |
