# OmniRoute AI — Comprehensive Engineering Audit & Transformation Plan

**Date:** 2026-11-14  
**Evaluator:** Principal Software Architect, Senior Backend Engineer, AI/ML & SRE Lead  
**Audit Target:** OmniRoute AI Omnichannel Ticket Routing & SLA Orchestration Platform  
**Target Submission:** Production & Hackathon Enterprise Evaluation  

---

## 1. Executive Summary & Existing Architecture

OmniRoute AI is structured as a modern 3-tier enterprise application:
- **Tier 1 (Presentation):** React 19 + TypeScript + Tailwind CSS v4 + Vite, compiled into `frontend/dist` and mounted directly via FastAPI `StaticFiles` for unified zero-CORS serving.
- **Tier 2 (Application & Orchestration):** FastAPI (Python 3.12) with REST APIs under `/api/v1/`, Pydantic v2 schemas for validation, and modular service layers (`classification`, `routing`, `sla`, `tickets`, `anomalies`, `analytics`, `evaluation`).
- **Tier 3 (Persistence):** SQLite 3 with Write-Ahead Logging (WAL) and dual-support for PostgreSQL via SQLAlchemy 2.0 ORM. Exactly 100 simulated human support-agent records generated with deterministic seed `20261022`.

---

## 2. Exhaustive Feature Classification Audit

Every capability across the platform has been audited at source code, schema, API contract, and test levels:

| Domain | Feature | Classification | Code Location | Observed Status & Gap Analysis |
|---|---|:---:|---|---|
| **SLA Engine** | Business Calendar Addition | `IMPLEMENTED_AND_TESTED` | `backend/app/services/sla/sla_calculator.py` | Accurate 09:00-18:00 IST business hours, weekend skipping, holiday calendar (`COMPANY_HOLIDAYS_2026`). |
| **SLA Engine** | Independent Dual Clocks | `PARTIALLY_IMPLEMENTED` | `backend/app/models/entities.py` | First response and resolution dates exist in `SLAEvent`, but lack separate clock start/stop state machine and automated ack rejection. |
| **SLA Engine** | Configurable SLA Policies | `PARTIALLY_IMPLEMENTED` | `backend/app/core/config.py` | Global SLA dictionaries exist in `Settings`. Tenant-specific, channel-specific, and tier-specific database-backed policy tables are missing. |
| **SLA Engine** | Authorized Pause & Resume | `PARTIALLY_IMPLEMENTED` | `backend/app/services/tickets/ticket_service.py` | Status changes to `PENDING_CUSTOMER` pause SLA, but lacks authorization guards, policy checking, and structured pause event recording. |
| **SLA Engine** | Multi-Level Escalation | `PARTIALLY_IMPLEMENTED` | `backend/app/services/tickets/ticket_service.py` | Manual priority escalation exists. Proactive Level 0–3 automatic escalation with idempotency keys is not yet centralized. |
| **SLA Engine** | SLA Audit History Events | `PARTIALLY_IMPLEMENTED` | `backend/app/models/entities.py` | `ticket_status_events` logs lifecycle changes, but dedicated immutable `sla_history_events` (`SLA_CREATED`, `SLA_AT_RISK`, `SLA_PAUSED`, etc.) are missing. |
| **AI Intelligence** | Intent Classification | `IMPLEMENTED_AND_TESTED` | `backend/app/services/classification/classifier.py` | Multi-intent extraction, keyword ranking, and fallback to `CUSTOMER_SUCCESS`. |
| **AI Intelligence** | Language Detection | `IMPLEMENTED_AND_TESTED` | `backend/app/services/classification/classifier.py` | Unicode script and romanized phonetic indicators for English, Telugu, Hindi, Tamil, and Kannada. |
| **AI Intelligence** | Priority & Safety Invariant | `IMPLEMENTED_AND_TESTED` | `backend/app/services/classification/classifier.py` | Security credentials breach or outage forces P1, overriding customer/agent downgrade attempts. |
| **AI Intelligence** | Confidence Scoring & Triage | `IMPLEMENTED_AND_TESTED` | `backend/app/services/classification/classifier.py` | Ambiguous text scores <0.65 and flags `needs_manual_review = True`. |
| **Routing Engine** | Mandatory Filtering | `IMPLEMENTED_AND_TESTED` | `backend/app/services/routing/routing_engine.py` | Disqualifies agents who are inactive, off-shift (UTC & IST checks), at capacity, or lacking skill/language. |
| **Routing Engine** | Atomic Capacity Guard | `IMPLEMENTED_AND_TESTED` | `backend/app/services/routing/routing_engine.py` | Database-level atomic conditional `UPDATE` prevents concurrent assignment overcapacity. |
| **Routing Engine** | Weighted Ranking & Tie-Break | `IMPLEMENTED_AND_TESTED` | `backend/app/services/routing/routing_engine.py` | Score = $0.35S + 0.25L + 0.25C + 0.15E$. Deterministic tie-break by free slots and Agent ID ASC. |
| **Lifecycle & Audit** | State Machine Validation | `IMPLEMENTED_AND_TESTED` | `backend/app/services/tickets/ticket_service.py` | Transitions validated against `VALID_TRANSITIONS`; invalid jumps throw `InvalidStateTransitionError`. |
| **Lifecycle & Audit** | Idempotent Ingestion | `IMPLEMENTED_AND_TESTED` | `backend/app/services/tickets/ticket_service.py` | 60-second window prevents duplicate emails/tickets (`DuplicateIngestionError`). |
| **Lifecycle & Audit** | History Immutability | `IMPLEMENTED_AND_TESTED` | `backend/app/services/tickets/ticket_service.py` | Reopening or transfers append new records; past messages and resolutions remain untouched. |
| **Multi-Tenancy** | Tenant Isolation | `NOT_IMPLEMENTED` | `backend/app/models/entities.py` | Relational schema lacks explicit `tenant_id` columns; cross-tenant boundary isolation is missing. |
| **Evaluation** | 3-Way Strategy Benchmark | `IMPLEMENTED_AND_TESTED` | `backend/app/services/evaluation/benchmark_service.py` | Round-Robin vs Skill-Based vs OmniRoute evaluated over real database tickets. |
| **Operations** | Anomaly Detection | `IMPLEMENTED_AND_TESTED` | `backend/app/services/anomalies/anomaly_service.py` | Scans for capacity violations, calendar mismatches, history loss, transfer loops, and safety violations. |
| **Operations** | Enterprise UI Control Tower | `IMPLEMENTED_AND_TESTED` | `frontend/src/pages/` | 8 operational dashboards + Omnichannel Tester, real API feeds, live scroll support. |

---

## 3. Discovered Vulnerabilities, Bottlenecks & Missing Features

1. **Multi-Tenant Data Leakage Risk:**  
   *Problem:* The current database entities (`tickets`, `agents`, `sla_events`) lack a `tenant_id` foreign or discriminator key.  
   *Risk:* In multi-tenant enterprise deployments (e.g., separating `jio_demo`, `amazon_demo`, `flipkart_demo`), agents from one tenant could view or be assigned tickets from another tenant.  
   *Action:* Introduce `tenant_id` across `Customer`, `Agent`, `Ticket`, and `SLAPolicy` entities with backend query filtering and cross-tenant rejection tests.

2. **Centralized SLA Policy Resolver Gap:**  
   *Problem:* SLA parameters are partially configured in static `core/config.py` dictionaries rather than dynamic, database-backed, tenant-aware SLA policies.  
   *Risk:* Cannot support differentiated customer tiers (e.g. VIP 15-min vs Standard 60-min) or tenant-specific working hours without restarting the backend.  
   *Action:* Build `SLAPolicy` table and a dedicated `SLAPolicyResolver` supporting tenant, channel, priority, category, and customer tier.

3. **Dual Independent SLA Clocks & Pause Traceability:**  
   *Problem:* The existing `SLAEvent` tracks due dates but lacks separate clock timestamps (`first_response_clock_started_at`, `first_response_clock_stopped_at`, `resolution_clock_started_at`), automated acknowledgement exclusion, and structured pause event logs (`SLAHistoryEvent`).  
   *Action:* Upgrade `SLAEvent` and implement `backend/app/services/sla/sla_engine.py` with dedicated methods for clock lifecycle, authorized pauses, and transparent risk states (`ON_TRACK`, `AT_RISK`, `CRITICAL`, `BREACHED`, `MET`, `PAUSED`).

4. **Proactive Multi-Level Escalation with Idempotency:**  
   *Problem:* Current escalation is reactive/manual via supervisor endpoint. Proactive escalation (Level 1: Agent alert, Level 2: Supervisor notification, Level 3: Queue reprioritization) needs automatic evaluation and idempotency keys to prevent notification storms.  
   *Action:* Implement an escalation evaluator and notification simulator in the SLA engine.

---

## 4. Phased Implementation Roadmap

1. **Phase 1 (Complete):** Codebase audit and baseline documentation in `docs/ENGINEERING_AUDIT.md`.
2. **Phase 2:** Multi-tenant schema migration & Centralized Independent SLA Engine (`SLAPolicy`, Dual Clocks, Pause/Resume, Multi-Level Escalation, `SLAHistoryEvent`).
3. **Phase 3:** Upgraded Explainable AI Intelligence (Secondary intents, structured explainability payload, complexity estimation).
4. **Phase 4:** Hardened Routing Engine with Tenant Isolation & Queue Routing.
5. **Phase 5:** Expanded Lifecycle State Machine (`WAITING_FOR_CUSTOMER`, `WAITING_FOR_EXTERNAL_DEPENDENCY`).
6. **Phase 6:** Predictive SLA Risk Evaluator & Operational Intelligence.
7. **Phase 7:** Automated Test Suite Expansion (covering 20 mandatory failure injection and negative tests).
8. **Phase 8:** Complete Enterprise Documentation Package (`docs/ARCHITECTURE.md`, `docs/SLA_ENGINE.md`, `docs/ROUTING_ENGINE.md`, etc.).
