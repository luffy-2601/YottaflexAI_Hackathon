# OmniRoute AI — API Reference & Contract Specification

## Base URL
All API v1 endpoints are mounted under:
```
http://localhost:8000/api/v1
```

---

## 1. Authentication & RBAC (`/auth`)

### `POST /auth/login`
Authenticates a user and returns a Bearer JWT access token.
- **Request Body**:
  ```json
  {
    "email": "admin.evaluator@hackathon.org",
    "password": "Password123!"
  }
  ```
- **Response**: `200 OK`
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1...",
    "token_type": "bearer",
    "user_id": "USR-ADMIN-01",
    "role": "ADMIN",
    "tenant_id": "default_tenant"
  }
  ```

### `GET /auth/me`
Retrieves authenticated session profile. Requires `Authorization: Bearer <token>`.

---

## 2. Tickets & Lifecycle (`/tickets`)

### `POST /tickets`
Ingests a customer ticket across channels (`email`, `chat`, `phone`).
- **Request Body**:
  ```json
  {
    "customer_id": "CUS-000001",
    "channel_id": "email",
    "subject": "Payment issue",
    "body": "Card was charged twice during checkout.",
    "language_code": "en",
    "priority": "P2"
  }
  ```
- **Response**: `201 Created`

### `POST /tickets/{ticket_id}/resolve`
Resolves ticket, halts SLA timers, records CSAT, and releases agent concurrency atomically.

---

## 3. Intelligent Routing & Queues (`/routing`)

### `POST /routing/dispatch-queue`
Runs dynamic in-queue dispatcher, matching waiting tickets with available agents.

### `POST /routing/evaluate/{ticket_id}`
Computes candidate scores with explainable rejection reasons.

---

## 4. SLA & Predictive AI (`/sla`)

### `GET /sla/tickets/{ticket_id}/predict`
Returns machine learning SLA breach probability, risk tier, and top contributing factors.

### `GET /sla/monitors`
Returns active SLA timers, countdowns, warning states, and breach counts.

---

## 5. Telemetry & Analytics (`/analytics`)

### `GET /analytics/telemetry/snapshot`
Returns instant real-time telemetry snapshot (open tickets, queued tickets, SLA risks, recent assignments).

### `GET /analytics/telemetry/stream`
Server-Sent Events (SSE) streaming endpoint for live operations dashboards.

### `GET /analytics/telemetry/background-jobs`
Returns persistent execution health of the background SLA and queue dispatcher daemon.
