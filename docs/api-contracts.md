# API Contracts & OpenAPI Specification

All endpoints are versioned under `/api/v1`.

## Core Endpoint Groups

### 1. Health & Status
- `GET /api/v1/health` -> `{ status: "ok", version: "1.0.0", timestamp: "..." }`

### 2. Tickets & Ingestion
- `GET /api/v1/tickets` (query params: `page`, `page_size`, `status`, `priority`, `intent_id`, `channel_id`, `search`)
- `POST /api/v1/tickets` (body: `{ customer_id, channel_id, subject, body, language_code? }`)
- `GET /api/v1/tickets/{ticket_id}` (returns ticket details, threaded messages, current assignment, SLA status, decision audit)
- `POST /api/v1/tickets/{ticket_id}/messages` (body: `{ sender_type, sender_id, body }`)
- `POST /api/v1/tickets/{ticket_id}/assign` (manually or auto re-route)
- `POST /api/v1/tickets/{ticket_id}/transfer` (body: `{ to_agent_id, reason }`)
- `POST /api/v1/tickets/{ticket_id}/escalate` (body: `{ reason }`)
- `POST /api/v1/tickets/{ticket_id}/reopen` (body: `{ reason }`)
- `POST /api/v1/tickets/{ticket_id}/resolve` (body: `{ resolution_code, summary, csat_score?, csat_feedback? }`)

### 3. Classification Engine
- `POST /api/v1/classification/classify` (body: `{ subject, body }` -> `{ intent_id, confidence, language_code, priority, applied_rules }`)

### 4. Routing Decision Engine
- `POST /api/v1/routing/evaluate` (dry-run or real assignment: `{ ticket_id }` -> candidate scores, rejected candidates, chosen agent)
- `GET /api/v1/routing/decisions/{ticket_id}` -> historical routing decision records

### 5. Agents & Capacity
- `GET /api/v1/agents` (query params: `status`, `skill_id`, `language_code`)
- `GET /api/v1/agents/{agent_id}` -> full agent profile, skills, languages, shifts, active tickets, capacity utilization
- `PUT /api/v1/agents/{agent_id}/status` (body: `{ status: "ACTIVE" | "ON_BREAK" | "INACTIVE" }`)

### 6. Queues & Channels
- `GET /api/v1/queues` -> queue status, backlog depths, average wait times
- `GET /api/v1/channels` -> channel configuration and default SLA multipliers

### 7. SLA Monitoring
- `GET /api/v1/sla/summary` -> breach count, approaching deadlines, compliance %
- `GET /api/v1/sla/active` -> active countdown timers, urgency sorted

### 8. Anomaly & Ground Truth
- `GET /api/v1/anomalies` -> list of detected anomalies, categorized by severity
- `POST /api/v1/anomalies/scan` -> triggers audit scan against ground truth and invariant rules

### 9. Analytics & Evaluation
- `GET /api/v1/analytics/overview` -> KPI metrics (total, open, resolved, FRT, MTTR, SLA compliance, agent utilization)
- `POST /api/v1/evaluation/simulate` (body: `{ strategy: "round_robin" | "skill_based" | "intelligent", scenario: "starter" }`)
- `GET /api/v1/evaluation/benchmarks` -> 3-way strategy comparison results

### 10. System Configuration
- `GET /api/v1/config` -> routing weights, SLA thresholds, supported languages
- `PUT /api/v1/config` -> update active routing weights & parameters
