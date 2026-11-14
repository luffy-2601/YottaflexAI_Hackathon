# OmniRoute AI — Normalized Relational Data Model Specification

## 1. Schema Overview

The database (`omnichannel.db`) consists of 23 normalized tables adhering to Boyce-Codd Normal Form (BCNF) where applicable, indexed on primary and foreign keys.

---

## 2. Entity Relationship Summary

```
   [Customer] (tenant_id)
        |
        | 1:N
        v
    [Ticket] (tenant_id) <----------------+
        |                                 |
        +---> [Message] (1:N)             |
        +---> [AssignmentEvent] (1:N)     |
        +---> [TicketStatusEvent] (1:N)   |
        +---> [SLAEvent] (1:1)            |
        |        |                        |
        |        +--> [SLAPolicy]         |
        +---> [SLAHistoryEvent] (1:N)     |
        +---> [RoutingDecision] (1:N)     |
        +---> [Resolution] (1:1)          |
        |                                 |
        v                                 |
     [Agent] (tenant_id) -----------------+
        |
        +---> [AgentSkill] (1:N) ---> [Skill]
        +---> [AgentLanguage] (1:N) -> [Language]
        +---> [AgentShift] (1:N)
        +---> [AgentQueue] (1:N) ----> [Queue] (tenant_id)
```

---

## 3. Core Table Specifications

### 3.1 `agents`
- `agent_id`: VARCHAR(32) PRIMARY KEY (`AGT-000001` to `AGT-000100`)
- `tenant_id`: VARCHAR(32) NOT NULL DEFAULT 'default_tenant' INDEX
- `name`: VARCHAR(128) NOT NULL (Synthetic via Faker Seed `20261022`)
- `email`: VARCHAR(128) NOT NULL UNIQUE
- `status`: VARCHAR(20) NOT NULL (`ACTIVE`, `INACTIVE`, `ON_BREAK`)
- `max_concurrency`: INTEGER NOT NULL (2 to 5 concurrent slots)
- `current_active_tickets`: INTEGER NOT NULL DEFAULT 0
- `experience_score`: FLOAT NOT NULL (0.60 to 1.0)
- `created_at`: TIMESTAMP WITH TIME ZONE

### 3.2 `tickets`
- `ticket_id`: VARCHAR(32) PRIMARY KEY (`TKT-2026-000001`)
- `tenant_id`: VARCHAR(32) NOT NULL DEFAULT 'default_tenant' INDEX
- `customer_id`: VARCHAR(32) FK -> `customers.customer_id`
- `channel_id`: VARCHAR(20) FK -> `channels.channel_id` (`email`, `chat`, `phone`)
- `subject`: VARCHAR(256) NOT NULL
- `status`: VARCHAR(32) NOT NULL (`NEW`, `ASSIGNED`, `IN_PROGRESS`, `WAITING_FOR_CUSTOMER`, `WAITING_FOR_EXTERNAL_DEPENDENCY`, `PENDING_CUSTOMER`, `ESCALATED`, `RESOLVED`, `REOPENED`, `CLOSED`)
- `priority`: VARCHAR(10) NOT NULL (`P1`, `P2`, `P3`, `P4`)
- `intent_id`: VARCHAR(64) FK -> `intents.intent_id`
- `language_code`: VARCHAR(10) FK -> `languages.language_code`
- `assigned_agent_id`: VARCHAR(32) FK -> `agents.agent_id` NULLABLE INDEX
- `queue_id`: VARCHAR(64) FK -> `queues.queue_id` NULLABLE
- `first_response_at`: TIMESTAMP WITH TIME ZONE NULLABLE
- `resolved_at`: TIMESTAMP WITH TIME ZONE NULLABLE
- `created_at`: TIMESTAMP WITH TIME ZONE INDEX

### 3.3 `sla_events`
- `sla_id`: VARCHAR(64) PRIMARY KEY (`SLA-TKT-2026-000001`)
- `ticket_id`: VARCHAR(32) FK -> `tickets.ticket_id` INDEX
- `policy_id`: VARCHAR(64) FK -> `sla_policies.policy_id` NULLABLE
- `first_response_clock_started_at`: TIMESTAMP WITH TIME ZONE
- `first_response_clock_stopped_at`: TIMESTAMP WITH TIME ZONE NULLABLE
- `first_response_due_at`: TIMESTAMP WITH TIME ZONE NOT NULL
- `first_response_actual_at`: TIMESTAMP WITH TIME ZONE NULLABLE
- `is_first_response_breached`: BOOLEAN DEFAULT FALSE
- `resolution_clock_started_at`: TIMESTAMP WITH TIME ZONE
- `resolution_clock_stopped_at`: TIMESTAMP WITH TIME ZONE NULLABLE
- `resolution_due_at`: TIMESTAMP WITH TIME ZONE NOT NULL
- `resolution_actual_at`: TIMESTAMP WITH TIME ZONE NULLABLE
- `is_resolution_breached`: BOOLEAN DEFAULT FALSE
- `status`: VARCHAR(20) (`RUNNING`, `PAUSED`, `MET`, `BREACHED`)
- `risk_level`: VARCHAR(20) (`ON_TRACK`, `AT_RISK`, `CRITICAL`, `BREACHED`, `MET`, `PAUSED`)
- `escalation_level`: INTEGER DEFAULT 0 (0, 1, 2, 3)
- `is_paused`: BOOLEAN DEFAULT FALSE
- `total_paused_seconds`: INTEGER DEFAULT 0

### 3.4 `sla_history_events`
- `history_id`: VARCHAR(64) PRIMARY KEY (`SLAHIST-TKT-2026-000001-001`)
- `ticket_id`: VARCHAR(32) FK -> `tickets.ticket_id` INDEX
- `sla_id`: VARCHAR(64) INDEX
- `event_type`: VARCHAR(64) NOT NULL
- `actor`: VARCHAR(64) NOT NULL
- `reason`: TEXT NULLABLE
- `idempotency_key`: VARCHAR(128) UNIQUE NULLABLE INDEX
- `payload`: JSON NULLABLE
- `created_at`: TIMESTAMP WITH TIME ZONE
