# SLA Engine Specification: Calendars, Deadlines, Warnings & Escalations

## 1. SLA Objectives by Priority

| Priority | Level Description | First Response Target (Wall / Business) | Resolution Target (Wall / Business) | Escalation Warning Threshold |
|---|---|---|---|---|
| **P1** | Critical (Security, Outage, Severe Financial) | 5 minutes | 60 minutes | At 75% elapsed (45 mins) |
| **P2** | High (Degraded Service, Payment Failure) | 15 minutes | 240 minutes (4 hours) | At 80% elapsed (192 mins) |
| **P3** | Medium (Standard Technical, Billing Query) | 60 minutes | 480 minutes (8 hours) | At 85% elapsed (408 mins) |
| **P4** | Low (General Enquiry, Minor Feedback) | 240 minutes (4 hours) | 1440 minutes (24 hours) | At 90% elapsed (1296 mins) |

---

## 2. Channel Multipliers & Business Calendar Rules

- **Voice/Phone Channel**: Synchronous channel. Requires immediate routing (First Response Target is 1 minute for P1/P2, 2 minutes for P3/P4).
- **Live Chat Channel**: Near-synchronous channel. First response targets multiplied by 0.5.
- **Email Channel**: Asynchronous channel. Standard priority targets apply.
- **Business Calendar Hours**: Standard business hours run Monday through Friday, 09:00 to 18:00 IST (UTC+05:30).
- **P1 Critical Exceptions**: P1 tickets ignore business calendar hours and run 24x7x365 wall-clock deadlines. P2-P4 calculate business working hours excluding company holidays and weekends.
- **Status Pauses**: When a ticket transitions to `PENDING_CUSTOMER`, the SLA clock pauses until the customer replies.
