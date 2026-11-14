# OmniRoute AI — Comprehensive API Reference

Base URL: `http://localhost:8000/api/v1`

---

## 1. Ticket Endpoints (`/tickets`)

### `POST /tickets/`
Creates a ticket, executes multi-intent & language classification, calculates SLA deadlines, and assigns or queues the ticket.
- **Request Body:**
  ```json
  {
    "customer_id": "CUS-000001",
    "channel_id": "email",
    "subject": "Internet outage on JioFiber",
    "body": "No network connection for 2 days. Repeated issue.",
    "tenant_id": "default_tenant"
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "ticket_id": "TKT-2026-001007",
    "tenant_id": "default_tenant",
    "customer_id": "CUS-000001",
    "channel_id": "email",
    "status": "ASSIGNED",
    "priority": "P2",
    "intent_id": "TECHNICAL_ISSUE",
    "language_code": "en",
    "assigned_agent_id": "AGT-000002"
  }
  ```

### `GET /tickets/{ticket_id}`
Retrieves complete ticket detail including customer info, messages, assignment history, SLA status, and resolution record.

### `POST /tickets/{ticket_id}/messages`
Appends a message. Human agent message (`sender_type: "AGENT"`) stops the First Response SLA clock. Automated ack (`sender_type: "SYSTEM"`) keeps the clock running.

### `POST /tickets/{ticket_id}/transfer`
Reassigns ticket to target agent. Records `TRANSFER` in `assignment_events`. Enforces transfer loop detection.

### `POST /tickets/{ticket_id}/reopen`
Reopens a `RESOLVED` ticket. Strictly preserves historical messages, assignments, and past CSAT records.

### `POST /tickets/{ticket_id}/resolve`
Marks ticket as `RESOLVED`. Releases agent capacity slot (`current_active_tickets -= 1`) and stops Resolution SLA clock.

---

## 2. SLA Orchestration Endpoints (`/sla`)

### `GET /sla/dashboard`
Returns live platform SLA metrics: compliance percentage, active clocks, at-risk/critical breakdown, and escalation level counts.

### `GET /sla/tickets/{ticket_id}`
Returns granular dual-clock status, remaining business minutes, pause tracking, and immutable history.

### `POST /sla/tickets/{ticket_id}/pause`
- **Request:** `{"reason": "WAITING_FOR_CUSTOMER", "authorized_by": "AGENT_01"}`
- **Response:** `{"status": "PAUSED", "paused_at": "...", "pause_reason": "WAITING_FOR_CUSTOMER"}`

### `POST /sla/tickets/{ticket_id}/resume`
- **Request:** `{"authorized_by": "AGENT_01", "reason": "Customer replied"}`
- **Response:** `{"status": "RESUMED", "total_paused_seconds": 3600, "new_resolution_due_at": "..."}`

### `GET /sla/policies`
Lists active SLA policies by `tenant_id`.

### `POST /sla/policies`
Creates a dynamic SLA policy for a tenant with custom working hours and escalation thresholds.

---

## 3. Intelligent Routing Endpoints (`/routing`)

### `POST /routing/evaluate`
Dry-run routing evaluation on any ticket. Returns scored candidates with metric breakdowns and rejected candidates with explicit reasons.

---

## 4. Evaluation & Benchmarking Endpoints (`/evaluation`)

### `GET /evaluation/benchmark?sample_size=500`
Executes live comparative benchmark comparing Round-Robin, Skill-Based, and OmniRoute Intelligent Routing on real database records.
