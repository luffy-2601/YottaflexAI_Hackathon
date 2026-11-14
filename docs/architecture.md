# OmniRoute AI — Enterprise Architecture Specification

## 1. System Philosophy & Architecture Overview

OmniRoute AI is an enterprise-grade intelligent omnichannel ticket routing, dual-clock SLA orchestration, and workload governance platform. It is engineered with a strict 3-tier architecture ensuring deterministic decision-making, explainability, multi-tenant isolation, and zero concurrency overcapacity.

```
       +--------------------------------------------------------------+
       |                  PRESENTATION TIER (TIER 1)                  |
       |  React 19 + TypeScript + Tailwind CSS v4 + Vite + Recharts  |
       |  - Operations Dashboard         - SLA Control Center         |
       |  - Omnichannel Live Simulator   - Decision Intelligence      |
       |  - Agent Workload Roster        - 3-Way Simulation Lab       |
       +------------------------------+-------------------------------+
                                      | HTTP REST / JSON
                                      v
       +--------------------------------------------------------------+
       |                 APPLICATION SERVICES (TIER 2)                |
       |                 FastAPI (Python 3.12 Engine)                 |
       |  +--------------------+  +--------------------------------+  |
       |  |  Classification    |  |       Routing Engine           |  |
       |  |  Rule + NLP Fallback|  | 0.35S + 0.25L + 0.25C + 0.15E  |  |
       |  +--------------------+  +--------------------------------+  |
       |  +--------------------+  +--------------------------------+  |
       |  |  Independent SLA   |  |   Lifecycle & Audit Machine    |  |
       |  |  Dual Clocks/Pause |  |   Immutable Event Sourcing     |  |
       |  +--------------------+  +--------------------------------+  |
       +------------------------------+-------------------------------+
                                      | SQLAlchemy 2.0 ORM
                                      v
       +--------------------------------------------------------------+
       |                  PERSISTENCE TIER (TIER 3)                   |
       |          SQLite 3 WAL / PostgreSQL Relational DB             |
       |  - 23 Normalized Tables     - 100 Human Support Agents       |
       |  - Atomic SQL Guards        - Full Multi-Tenant Indexing     |
       +--------------------------------------------------------------+
```

## 2. Core Architectural Pillars

### 2.1 Multi-Tenant Data Isolation
- Every domain entity (`customers`, `agents`, `tickets`, `queues`, `sla_policies`) carries a first-class `tenant_id` column.
- Queries are tenant-scoped at the ORM repository layer.
- Routing explicitly forbids cross-tenant candidate assignment (`Agent.tenant_id == Ticket.tenant_id`).

### 2.2 Independent Dual-Clock SLA Engine
- Separate tracking for **First Response SLA** and **Resolution SLA**.
- **Automated Ack Exclusion:** Automated acknowledgments or bot greetings do not stop human response clocks.
- **Authorized Pause/Resume:** Pauses require valid business reasons (`WAITING_FOR_CUSTOMER`, `WAITING_FOR_THIRD_PARTY`, `WAITING_FOR_EXTERNAL_DEPENDENCY`) and extend deadlines by exact paused durations.
- **Business Calendar:** Non-P1 tickets calculate deadlines strictly within 09:00–18:00 business hours, skipping weekends and designated holidays (`COMPANY_HOLIDAYS_2026`).

### 2.3 Constraint-Based Intelligent Routing
- **Hard Disqualification Filters:** Agents must be active, on-shift (checked against both UTC and IST shifts), possess mandatory skills with proficiency $\ge 0.60$, match language requirements, have available capacity, and belong to the ticket's tenant.
- **Atomic Capacity Guard:** SQL-level atomic updates (`UPDATE agents SET current_active_tickets = current_active_tickets + 1 WHERE current_active_tickets < max_concurrency`) eliminate race-condition overcapacity across parallel threads.
- **Explainable Scoring:** Weighted score $0.35S + 0.25L + 0.25C + 0.15E$ with deterministic tie-breaking.

### 2.4 Immutable Event Sourcing & Auditability
- State transitions are validated by an explicit finite-state machine.
- Every assignment, status change, and SLA clock event is immutably appended to `assignment_events`, `ticket_status_events`, and `sla_history_events`.
- Prior histories and CSAT ratings are permanently retained upon reopening.
