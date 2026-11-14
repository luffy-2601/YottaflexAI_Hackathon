# OmniRoute AI — Constraint-Based Intelligent Routing Engine

## 1. Overview

The OmniRoute Routing Engine (`backend/app/services/routing/routing_engine.py`) executes a two-stage evaluation:
1. **Stage 1: Hard Constraint Disqualification Filters** (Non-negotiable).
2. **Stage 2: Multi-Factor Weighted Scoring & Deterministic Tie-Breaking**.

An agent failing any Stage 1 filter is disqualified immediately and recorded with rejection reasons.

---

## 2. Stage 1: Mandatory Disqualification Filters

```
                    Incoming Ticket
                           |
                           v
              +--------------------------+
              | Multi-Tenant Check       | --> [Mismatch] --> REJECT (Tenant Mismatch)
              +--------------------------+
                           |
              +--------------------------+
              | Agent Status Check       | --> [!= ACTIVE] --> REJECT (Inactive/Break)
              +--------------------------+
                           |
              +--------------------------+
              | Shift Schedule Check     | --> [Off-Shift] --> REJECT (Outside Schedule)
              +--------------------------+
                           |
              +--------------------------+
              | Concurrency Capacity     | --> [Load >= Max] --> REJECT (At Capacity Limit)
              +--------------------------+
                           |
              +--------------------------+
              | Mandatory Skill Check    | --> [Missing/ <0.60] --> REJECT (Skill Deficit)
              +--------------------------+
                           |
              +--------------------------+
              | Language Match Check     | --> [Missing/ <0.60] --> REJECT (Language Deficit)
              +--------------------------+
                           |
                           v
                   ELIGIBLE CANDIDATE
```

---

## 3. Stage 2: Weighted Multi-Factor Scoring

Eligible candidates are scored on a normalized 0–100 scale:

$$\text{Final Score} = (w_S \times S) + (w_L \times L) + (w_C \times C) + (w_E \times E)$$

Where default configuration weights are:
- $w_S = 0.35$ (Skill Match & Proficiency)
- $w_L = 0.25$ (Language Proficiency)
- $w_C = 0.25$ (Available Capacity Margin: $\frac{\text{Free Slots}}{\text{Max Concurrency}} \times 100$)
- $w_E = 0.15$ (Agent Experience Score)

### Deterministic Tie-Breaking Hierarchy
When two agents yield identical scores, ties are resolved deterministically:
1. **Total Routing Score DESC**
2. **Remaining Free Capacity Slots DESC**
3. **Agent ID ASC** (e.g. `AGT-000001` prioritized over `AGT-000002`)

---

## 4. Concurrency Safety & Atomic Reservation

To prevent race conditions during high-concurrency ticket arrival, capacity reservation executes at the SQL engine level:

```python
rows_updated = self.db.query(Agent).filter(
    Agent.agent_id == selected_agent_id,
    Agent.current_active_tickets < Agent.max_concurrency
).update(
    {Agent.current_active_tickets: Agent.current_active_tickets + 1},
    synchronize_session=False
)
if rows_updated == 0:
    return False  # Concurrency safe: slot already consumed
```

If another worker consumed the last slot concurrently, `rows_updated` returns `0`, the assignment fails safely, and the ticket is queued without exceeding capacity.
