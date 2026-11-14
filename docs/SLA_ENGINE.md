# OmniRoute AI — Independent SLA Engine Specification

## 1. Architectural Philosophy

The OmniRoute SLA Engine (`backend/app/services/sla/sla_engine.py`) operates as an independent, authoritative calculation, clock management, and escalation subsystem. It decouples SLA governance from UI components and ticket ingestion logic.

## 2. Dual Independent Clocks

| Clock | Activation Trigger | Termination Condition | Calculation Model | Breach Criteria |
|---|---|---|---|---|
| **First Response SLA** | Ticket accepted into system (`SLA_CREATED`) | Qualifying human agent response (`FIRST_RESPONSE_MET`) | Continuous for P1; Business hours (09:00–18:00 IST) for P2–P4 | `first_response_actual_at > first_response_due_at` |
| **Resolution SLA** | Ticket accepted into system (`RESOLUTION_CLOCK_STARTED`) | Valid ticket resolution (`RESOLUTION_MET`) | Continuous for P1; Business hours (09:00–18:00 IST) for P2–P4 | `resolution_actual_at > resolution_due_at` |

> **Automated Acknowledgment Rule:** Automated system replies or bot greetings emit an `AUTO_ACK_RECEIVED` event and do **NOT** stop or satisfy the First Response SLA clock.

## 3. Business Calendar Engine

- **Working Hours:** 09:00 to 18:00 (540 business minutes daily).
- **Working Days:** Monday through Friday (Weekdays 0–4).
- **Weekend Skipping:** Saturdays and Sundays are excluded from business hour consumption.
- **National Holiday Skipping:** Designated company holidays (`COMPANY_HOLIDAYS_2026`: Republic Day, Independence Day, Gandhi Jayanti, Dussehra, Diwali, Christmas) are bypassed.
- **After-Hours Arrivals:** Tickets created outside 09:00–18:00 begin consuming business time at 09:00 on the subsequent business day.

## 4. Authorized Pause & Resume Subsystem

### 4.1 Permitted Pause Reasons
1. `WAITING_FOR_CUSTOMER`: Customer clarification required.
2. `WAITING_FOR_THIRD_PARTY`: Upstream ISP, payment gateway, or vendor dependency.
3. `WAITING_FOR_EXTERNAL_DEPENDENCY`: Hardware part procurement or security clearance.

Any unauthorized pause reason (e.g. `GOING_TO_LUNCH`) is strictly rejected with `UnauthorizedPauseError`.

### 4.2 Pause Extension Formula
Upon resume, total paused time is calculated and deadlines are extended:
$$\text{New Due Date} = \text{Old Due Date} + \Delta t_{\text{paused}}$$
$$\text{Total Paused Seconds} \mathrel{+}= \Delta t_{\text{paused}}$$

## 5. Transparent Risk Levels & Proactive Escalation

Risk state is continuously evaluated against remaining business time:

| Ratio Consumed | Risk Category | Escalation Action | Idempotency Key Pattern |
|---|---|---|---|
| $< 70\%$ | `ON_TRACK` | Level 0: Standard Monitoring | N/A |
| $\ge 70\%$ | `AT_RISK` | Level 1: Warning notification to assigned agent | `ESC-{ticket_id}-L1-{YYYYMMDDHH}` |
| $\ge 90\%$ | `CRITICAL` | Level 2: Supervisor notification & dashboard highlight | `ESC-{ticket_id}-L2-{YYYYMMDDHH}` |
| $> 100\%$ | `BREACHED` | Level 3: Manager escalation & priority queue bump | `ESC-{ticket_id}-L3-{YYYYMMDDHH}` |

Idempotency keys prevent repetitive notification storms for the same ticket within the same evaluation window.
