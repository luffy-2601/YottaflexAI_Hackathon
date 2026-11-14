# Routing Algorithm Specification: Two-Stage Multi-Factor Routing Engine

## 1. Overview

The Intelligent Routing Engine solves the NP-hard constraint satisfaction and optimal matching problem in customer service dispatching. It eliminates subjective, ad-hoc ticket distribution and guarantees adherence to SLAs, language barriers, and agent workload boundaries.

---

## 2. Two-Stage Decision Architecture

```
[ Incoming Classified Ticket ]
  (Intent, Priority, Language, Channel, Timestamp)
             |
             v
+-------------------------------------------------------------+
| Stage 1: Hard Eligibility Filtering (Deterministic Boolean) |
+-------------------------------------------------------------+
| Check 1: Is Agent ACTIVE and not in status ON_BREAK/OFFLINE?|
| Check 2: Is Agent on current scheduled SHIFT?               |
| Check 3: Does Agent speak required Language or fallback?    |
| Check 4: Does Agent possess mandatory Intent Skill?         |
| Check 5: Does Agent have Available Concurrency Capacity?    |
| Check 6: Is Agent assigned to Ticket's Target Queue?        |
+-------------------------------------------------------------+
             |
             +---- If Count(Eligible) == 0 ----> [ NO_ELIGIBLE_AGENT Path ]
             |                                     * Place in Queue Backlog
             |                                     * Record reason in DB
             |                                     * Start SLA Escalation Clock
             v
+-------------------------------------------------------------+
| Stage 2: Weighted Multi-Factor Scoring (0.0 to 100.0)       |
+-------------------------------------------------------------+
| Score = (0.35 * S) + (0.25 * L) + (0.25 * C) + (0.15 * E)   |
|   S = Skill Proficiency Level (0-100)                       |
|   L = Language Fluency Score (0-100)                        |
|   C = Remaining Capacity Percentage (0-100)                 |
|   E = Historical Experience / CSAT Performance (0-100)      |
+-------------------------------------------------------------+
             |
             v
+-------------------------------------------------------------+
| Tie-Breaking & Atomic Capacity Reservation                  |
+-------------------------------------------------------------+
| 1. Sort by Final Score DESC                                 |
| 2. Tie-break: Agent with longest idle time since last ticket|
| 3. Atomic Database Lock (SELECT FOR UPDATE) on Agent row    |
| 4. Increment agent.current_active_tickets                   |
| 5. Persist RoutingDecision with full candidate score matrix |
| 6. Append AssignmentEvent record                            |
+-------------------------------------------------------------+
```

---

## 3. Configuration & Parameterization

Weights are parameterized in `SystemConfiguration`:
- `WEIGHT_SKILL`: 0.35 (Default)
- `WEIGHT_LANGUAGE`: 0.25 (Default)
- `WEIGHT_CAPACITY`: 0.25 (Default)
- `WEIGHT_EXPERIENCE`: 0.15 (Default)

The sum of weights is normalized to 1.00 at runtime.
