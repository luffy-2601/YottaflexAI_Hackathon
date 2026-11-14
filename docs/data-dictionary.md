# Data Dictionary: Omnichannel Ticket Routing & SLA Management

| Entity | Field Name | Data Type | Nullable | Primary/Foreign Key | Allowed Values / Constraints | Description |
|---|---|---|---|---|---|---|
| **Customer** | `customer_id` | VARCHAR(32) | NO | PK | `CUS-[0-9]{6}` | Unique customer identifier |
| Customer | `name` | VARCHAR(128) | NO | | String | Customer full name |
| Customer | `email` | VARCHAR(128) | NO | | Valid email format | Customer contact email |
| Customer | `phone` | VARCHAR(32) | YES | | E.164 phone format | Customer phone number |
| Customer | `tier` | VARCHAR(20) | NO | | `STANDARD`, `VIP`, `ENTERPRISE` | Customer tier level |
| Customer | `created_at` | TIMESTAMP | NO | | ISO8601 UTC | Registration timestamp |
| **Channel** | `channel_id` | VARCHAR(20) | NO | PK | `email`, `chat`, `phone` | Omnichannel ingestion channel |
| Channel | `name` | VARCHAR(64) | NO | | String | Human readable channel name |
| Channel | `default_sla_factor` | FLOAT | NO | | > 0.0 (e.g. 1.0, 0.5) | SLA multiplier for channel |
| Channel | `is_active` | BOOLEAN | NO | | TRUE, FALSE | Active channel flag |
| **Intent** | `intent_id` | VARCHAR(64) | NO | PK | Uppercase snake_case | Unique intent classification key |
| Intent | `name` | VARCHAR(128) | NO | | String | Intent display label |
| Intent | `category` | VARCHAR(64) | NO | | `BILLING`, `TECH`, `ACCOUNT` | Broad category |
| Intent | `default_priority` | VARCHAR(10) | NO | | `P1`, `P2`, `P3`, `P4` | Baseline priority |
| Intent | `required_skill_id` | VARCHAR(64) | YES | FK -> Skill.skill_id | Valid skill ID | Mandatory skill required |
| **Language** | `language_code` | VARCHAR(10) | NO | PK | `en`, `te`, `hi`, `ta`, `kn` | ISO 639-1 language code |
| Language | `name` | VARCHAR(64) | NO | | String | Language display name |
| Language | `is_supported` | BOOLEAN | NO | | TRUE, FALSE | Operational flag |
| **Skill** | `skill_id` | VARCHAR(64) | NO | PK | Uppercase snake_case | Technical competence identifier |
| Skill | `name` | VARCHAR(128) | NO | | String | Skill display name |
| Skill | `tier_level` | INTEGER | NO | | 1, 2, 3 | Complexity tier |
| **Agent** | `agent_id` | VARCHAR(32) | NO | PK | `AGT-[0-9]{6}` | Unique agent identifier |
| Agent | `name` | VARCHAR(128) | NO | | String | Agent staff name |
| Agent | `email` | VARCHAR(128) | NO | | Valid email | Agent login email |
| Agent | `status` | VARCHAR(20) | NO | | `ACTIVE`, `INACTIVE`, `ON_BREAK` | Current presence status |
| Agent | `max_concurrency` | INTEGER | NO | | 1 to 10 | Max simultaneous open tickets |
| Agent | `current_active_tickets` | INTEGER | NO | | >= 0 | Currently assigned open tickets |
| Agent | `experience_score` | FLOAT | NO | | 0.00 to 1.00 | Agent track record metric |
| **Ticket** | `ticket_id` | VARCHAR(32) | NO | PK | `TKT-2026-[0-9]{6}` | Unique immutable ticket ID |
| Ticket | `customer_id` | VARCHAR(32) | NO | FK -> Customer | Valid Customer PK | Associated customer |
| Ticket | `channel_id` | VARCHAR(20) | NO | FK -> Channel | `email`, `chat`, `phone` | Ingestion channel |
| Ticket | `subject` | VARCHAR(256) | NO | | String | Ticket title/summary |
| Ticket | `status` | VARCHAR(32) | NO | | `NEW`, `OPEN`, `QUEUED`, `ASSIGNED`, `IN_PROGRESS`, `PENDING_CUSTOMER`, `ESCALATED`, `RESOLVED`, `REOPENED`, `CLOSED` | Explicit lifecycle state |
| Ticket | `priority` | VARCHAR(10) | NO | | `P1`, `P2`, `P3`, `P4` | Operational priority |
| Ticket | `intent_id` | VARCHAR(64) | NO | FK -> Intent | Valid Intent PK | Classified intent |
| Ticket | `language_code` | VARCHAR(10) | NO | FK -> Language | Valid Language PK | Primary ticket language |
| Ticket | `assigned_agent_id` | VARCHAR(32) | YES | FK -> Agent | Valid Agent PK | Currently assigned agent |
| Ticket | `created_at` | TIMESTAMP | NO | | ISO8601 UTC | Creation time |
| Ticket | `resolved_at` | TIMESTAMP | YES | | ISO8601 UTC | Resolution time |
| **Message** | `message_id` | VARCHAR(64) | NO | PK | `MSG-TKT-[0-9]{4}-[0-9]{6}-[0-9]{3}` | Thread message ID |
| Message | `ticket_id` | VARCHAR(32) | NO | FK -> Ticket | Valid Ticket PK | Parent ticket |
| Message | `sender_type` | VARCHAR(20) | NO | | `CUSTOMER`, `AGENT`, `SYSTEM` | Origin of message |
| Message | `sender_id` | VARCHAR(64) | NO | | String | ID of sender |
| Message | `body` | TEXT | NO | | Non-empty text | Message payload |
| Message | `created_at` | TIMESTAMP | NO | | ISO8601 UTC | Timestamp |
| **AssignmentEvent** | `assignment_id` | VARCHAR(64) | NO | PK | `ASN-TKT-[0-9]{4}-[0-9]{6}-[0-9]{3}` | Assignment log ID |
| AssignmentEvent | `ticket_id` | VARCHAR(32) | NO | FK -> Ticket | Valid Ticket PK | Ticket reassigned |
| AssignmentEvent | `agent_id` | VARCHAR(32) | NO | FK -> Agent | Valid Agent PK | Target agent |
| AssignmentEvent | `event_type` | VARCHAR(32) | NO | | `INITIAL_ASSIGN`, `TRANSFER`, `ESCALATION`, `REOPEN` | Event type |
| AssignmentEvent | `reason` | TEXT | NO | | String | Explanatory decision summary |
| AssignmentEvent | `created_at` | TIMESTAMP | NO | | ISO8601 UTC | Timestamp |
| **SLAEvent** | `sla_id` | VARCHAR(64) | NO | PK | `SLA-TKT-[0-9]{4}-[0-9]{6}` | SLA record ID |
| SLAEvent | `ticket_id` | VARCHAR(32) | NO | FK -> Ticket | Valid Ticket PK | Monitored ticket |
| SLAEvent | `first_response_due_at` | TIMESTAMP | NO | | ISO8601 UTC | First response target |
| SLAEvent | `resolution_due_at` | TIMESTAMP | NO | | ISO8601 UTC | Resolution target |
| SLAEvent | `first_response_actual_at` | TIMESTAMP | YES | | ISO8601 UTC | Actual first response |
| SLAEvent | `resolution_actual_at` | TIMESTAMP | YES | | ISO8601 UTC | Actual resolution |
| SLAEvent | `is_first_response_breached`| BOOLEAN | NO | | TRUE, FALSE | Breach indicator |
| SLAEvent | `is_resolution_breached` | BOOLEAN | NO | | TRUE, FALSE | Breach indicator |
| SLAEvent | `status` | VARCHAR(20) | NO | | `RUNNING`, `PAUSED`, `MET`, `BREACHED` | SLA monitor state |
| **Resolution** | `resolution_id` | VARCHAR(64) | NO | PK | `RES-TKT-[0-9]{4}-[0-9]{6}` | Resolution record |
| Resolution | `ticket_id` | VARCHAR(32) | NO | FK -> Ticket | Valid Ticket PK | Resolved ticket |
| Resolution | `agent_id` | VARCHAR(32) | NO | FK -> Agent | Valid Agent PK | Resolving agent |
| Resolution | `resolution_code` | VARCHAR(64) | NO | | `SOLVED`, `WORKAROUND`, `CANCELLED` | Outcome classification |
| Resolution | `csat_score` | INTEGER | YES | | 1 to 5 | Customer satisfaction rating |
