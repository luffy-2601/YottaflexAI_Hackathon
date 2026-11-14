# Database Design: Relational Schema & Entity Relationships

## 1. Relational Model Overview

The database uses third normal form (3NF) for master and transactional entities, augmented with event-sourcing append-only ledgers for all state transitions, assignments, and SLA computations.

### Primary Keys and Nomenclature
- **Customer**: `CUS-000001` to `CUS-999999`
- **Channel**: `email`, `chat`, `phone`
- **Agent**: `AGT-000001` to `AGT-999999`
- **Ticket**: `TKT-2026-000001` to `TKT-2026-999999`
- **Message**: `MSG-TKT-2026-000001-001`
- **Assignment Event**: `ASN-TKT-2026-000001-001`
- **SLA Event / Record**: `SLA-TKT-2026-000001`
- **Routing Decision**: `DEC-TKT-2026-000001-001`
- **Resolution**: `RES-TKT-2026-000001`

---

## 2. Entity Relationship Diagram (ERD)

```
                                  +-------------------+
                                  |     Customer      |
                                  | (PK: customer_id) |
                                  +---------+---------+
                                            | 1
                                            |
                                            | N
+-------------------+             +---------v---------+             +--------------------+
|      Channel      | 1         N |       Ticket      | N         1 |       Intent       |
| (PK: channel_id)  +-------------> (PK: ticket_id)   <-------------+  (PK: intent_id)   |
+-------------------+             +---+---+---+---+---+             +--------------------+
                                      |   |   |   |
            +-------------------------+   |   |   +--------------------------+
            | 1                           | 1 | 1                            | 1
            |                             |   |                              |
            | N                           |   |                              | 1
+-----------v-----------+                 |   |                    +---------v----------+
|        Message        |                 |   |                    |     Resolution     |
|  (PK: message_id)     |                 |   |                    | (PK: resolution_id)|
+-----------------------+                 |   |                    +--------------------+
                                          |   |
            +-----------------------------+   +-----------------------------+
            | 1                                                             | 1
            | N                                                             | N
+-----------v-----------+                                         +---------v----------+
|   AssignmentEvent     |                                         |      SLAEvent      |
|  (PK: assignment_id)  |                                         |   (PK: sla_id)     |
+-----------+-----------+                                         +--------------------+
            | N
            |
            | 1
+-----------v-----------+        N             M        +--------------------+
|         Agent         +------------------------------->|       Skill        |
|   (PK: agent_id)      |   via AgentSkill bridge       |  (PK: skill_id)    |
+-----------+-----------+                               +--------------------+
            |
            | N                  N             M        +--------------------+
            +------------------------------------------->|      Language      |
            |               via AgentLanguage bridge    |  (PK: lang_code)   |
            |                                           +--------------------+
            | N                  N             M        +--------------------+
            +------------------------------------------->|       Queue        |
                            via AgentQueue bridge       |  (PK: queue_id)    |
                                                        +--------------------+
```

---

## 3. Core Entity Definitions

### Master Entities
1. **Customer**: `customer_id` (PK), `name`, `email`, `phone`, `tier` (STANDARD, VIP, ENTERPRISE), `created_at`.
2. **Channel**: `channel_id` (PK: 'email', 'chat', 'phone'), `name`, `default_sla_factor`, `is_active`.
3. **Intent**: `intent_id` (PK), `name`, `category`, `default_priority`, `required_skill_id`.
4. **Skill**: `skill_id` (PK), `name`, `description`, `tier_level` (1, 2, 3).
5. **Language**: `language_code` (PK: 'en', 'te', 'hi', 'ta', 'kn'), `name`, `is_supported`.
6. **Queue**: `queue_id` (PK), `name`, `channel_id`, `priority_min`, `routing_strategy`.
7. **PriorityRule**: `rule_id` (PK), `rule_name`, `intent_id`, `trigger_keyword`, `enforced_priority`, `is_safety_critical`.

### Agent & Capacity Entities
8. **Agent**: `agent_id` (PK), `name`, `email`, `status` (ACTIVE, INACTIVE, ON_BREAK), `max_concurrency`, `current_active_tickets`, `experience_score` (0.00-1.00), `created_at`.
9. **AgentSkill**: `agent_id` (FK), `skill_id` (FK), `proficiency_level` (0.00-1.00) (Composite PK).
10. **AgentLanguage**: `agent_id` (FK), `language_code` (FK), `fluency_score` (0.00-1.00) (Composite PK).
11. **AgentShift**: `shift_id` (PK), `agent_id` (FK), `day_of_week` (0-6), `start_time`, `end_time`, `timezone`.
12. **AgentQueue**: `agent_id` (FK), `queue_id` (FK) (Composite PK).

### Transactional & Event Entities
13. **Ticket**: `ticket_id` (PK), `customer_id` (FK), `channel_id` (FK), `subject`, `status` (NEW, OPEN, QUEUED, ASSIGNED, IN_PROGRESS, PENDING_CUSTOMER, ESCALATED, RESOLVED, REOPENED, CLOSED), `priority` (P1, P2, P3, P4), `intent_id` (FK), `language_code` (FK), `assigned_agent_id` (FK, nullable), `queue_id` (FK, nullable), `created_at`, `updated_at`, `resolved_at`.
14. **Message**: `message_id` (PK), `ticket_id` (FK), `sender_type` (CUSTOMER, AGENT, SYSTEM), `sender_id`, `body`, `sentiment_score`, `created_at`.
15. **RoutingDecision**: `decision_id` (PK), `ticket_id` (FK), `selected_agent_id` (FK, nullable), `score`, `eligible_candidates_count`, `rejected_candidates_json`, `score_breakdown_json`, `reason`, `policy_version`, `created_at`.
16. **AssignmentEvent**: `assignment_id` (PK), `ticket_id` (FK), `agent_id` (FK), `event_type` (INITIAL_ASSIGN, REASSIGN, TRANSFER, ESCALATION), `actor_id`, `reason`, `created_at`.
17. **SLAEvent**: `sla_id` (PK), `ticket_id` (FK), `first_response_due_at`, `resolution_due_at`, `first_response_actual_at`, `resolution_actual_at`, `is_first_response_breached`, `is_resolution_breached`, `status` (RUNNING, PAUSED, MET, BREACHED), `created_at`, `updated_at`.
18. **Resolution**: `resolution_id` (PK), `ticket_id` (FK), `agent_id` (FK), `resolution_code`, `summary`, `csat_score` (1-5, nullable), `csat_feedback`, `created_at`.
19. **TicketStatusEvent**: `event_id` (PK), `ticket_id` (FK), `old_status`, `new_status`, `changed_by`, `reason`, `created_at`.
20. **Anomaly**: `anomaly_id` (PK), `ticket_id` (FK, nullable), `agent_id` (FK, nullable), `category` (CAPACITY_VIOLATION, CALENDAR_MISMATCH, HISTORY_LOSS, TRANSFER_LOOP, SAFETY_VIOLATION), `severity` (CRITICAL, HIGH, MEDIUM, LOW), `description`, `expected_behavior`, `actual_behavior`, `detected_at`.
