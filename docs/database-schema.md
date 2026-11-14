# OmniRoute AI — Relational Database Schema & Entities

The OmniRoute AI database enforces strict third normal form (3NF), foreign-key relational integrity, row-level locks, and append-only audit event ledgers.

---

## 1. Core Tables & Responsibilities

| Table Name | Description | Key Columns |
|---|---|---|
| `users` | Authenticated operators & roles | `user_id`, `email`, `hashed_password`, `role`, `tenant_id` |
| `customers` | Normalized customer master | `customer_id`, `name`, `email`, `tier`, `tenant_id` |
| `channels` | Ingestion channels | `channel_id` (`email`, `chat`, `phone`), `default_sla_factor` |
| `skills` | Technical competencies | `skill_id`, `name`, `tier_level` |
| `languages` | Supported languages | `language_code`, `name`, `is_supported` |
| `intents` | AI intent taxonomy | `intent_id`, `name`, `category`, `default_priority`, `required_skill_id` |
| `agents` | Support workforce roster | `agent_id`, `name`, `status`, `max_concurrency`, `current_active_tickets` |
| `agent_skills` | Agent skill proficiency | `agent_id`, `skill_id`, `proficiency_level` (0.00 - 1.00) |
| `agent_languages` | Agent fluency scores | `agent_id`, `language_code`, `fluency_score` (0.00 - 1.00) |
| `agent_shifts` | Agent scheduled hours | `agent_id`, `shift_start_hour`, `shift_end_hour`, `timezone` |
| `tickets` | Core support tickets | `ticket_id`, `customer_id`, `channel_id`, `status`, `priority`, `intent_id`, `assigned_agent_id` |
| `messages` | Threaded customer & agent conversations | `message_id`, `ticket_id`, `sender_type`, `body`, `sentiment_score` |
| `routing_decisions` | Transparent routing audit log | `decision_id`, `ticket_id`, `selected_agent_id`, `final_score`, `reason` |
| `assignment_events` | Immutable assignment audit trail | `assignment_id`, `ticket_id`, `agent_id`, `event_type`, `reason`, `created_at` |
| `sla_policies` | SLA policy rules per tenant/priority | `policy_id`, `tenant_id`, `priority`, `first_response_minutes`, `resolution_minutes` |
| `sla_events` | Dual independent SLA clock records | `sla_id`, `ticket_id`, `first_response_due_at`, `resolution_due_at`, `status`, `risk_level` |
| `sla_history_events` | Append-only SLA clock state changes | `history_id`, `ticket_id`, `event_type`, `actor`, `reason`, `created_at` |
| `resolutions` | Resolution notes & CSAT scores | `resolution_id`, `ticket_id`, `agent_id`, `summary`, `csat_score` |
| `ticket_status_events` | State machine transitions | `event_id`, `ticket_id`, `old_status`, `new_status`, `reason`, `created_at` |
| `anomalies` | Detected operational anomalies & supervisor alerts | `anomaly_id`, `ticket_id`, `agent_id`, `category`, `severity`, `description` |
| `business_calendars` | Business hours schedules | `calendar_id`, `timezone`, `work_start_hour`, `work_end_hour`, `work_days` |
| `business_calendar_holidays`| Enterprise calendar holidays | `holiday_id`, `calendar_id`, `holiday_date`, `name` |
| `system_configurations` | Dynamic weights & persistent worker telemetry | `key`, `value`, `description`, `updated_at` |
