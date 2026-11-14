# OmniRoute AI — Explainable AI Decision Logic & Classification Architecture

## 1. Hybrid Classifier Philosophy

The classification subsystem (`backend/app/services/classification/classifier.py`) combines keyword token extraction with hard deterministic safety rules. AI suggestions provide intent, duration, and recurrence recommendations, but **deterministic enterprise safety rules strictly govern final priority**.

---

## 2. Multi-Intent Extraction & Skill Mapping

The engine parses the incoming text and ranks detected intents:

| Intent Category | Primary Skill Required | Default Priority | Trigger Keywords (Sample) |
|---|---|:---:|---|
| `ACCOUNT_SECURITY` | `SECURITY_FORENSICS` | **P1** | hacked, compromised, unauthorized, breach, stolen credentials, fraud |
| `TECHNICAL_ISSUE` | `INFRA_SYSADMIN` | **P2** | no internet, outage, router, wifi, connectivity, 500 error, crash |
| `PAYMENT_FAILURE` | `PAYMENT_GATEWAY` | **P2** | payment failed, transaction declined, card rejected, upi error |
| `PAYMENT_DUPLICATE`| `PAYMENT_GATEWAY` | **P2** | charged twice, double payment, duplicate debit |
| `REFUND_REQUEST` | `BILLING_OPERATIONS`| **P3** | refund, money back, reimbursement, cancel order |
| `BILLING_QUERY` | `BILLING_OPERATIONS`| **P3** | invoice, gst, tax receipt, subscription charge |
| `LOGIN_ISSUE` | `CUSTOMER_SUCCESS` | **P3** | cannot login, otp not received, password reset |
| `GENERAL_ENQUIRY` | `CUSTOMER_SUCCESS` | **P4** | how to use, contact support, office address |

---

## 3. Multilingual Detection

Supported languages include English (`en`), Telugu (`te`), Hindi (`hi`), Tamil (`ta`), and Kannada (`kn`). Detection utilizes Unicode script ranges combined with word-boundary (`\b`) romanized phonetic triggers to prevent false positives:
- Telugu: `[\u0C00-\u0C7F]`, `\bnamaskaram\b`, `\bnenu\b`, `\bdabbu\b`, `\bcheyandi\b`
- Hindi: `[\u0900-\u097F]`, `\bnamaste\b`, `\bmadad\b`, `\bchahiye\b`, `\bpaisa\b`, `\bkhata\b`
- Tamil: `[\u0B80-\u0BFF]`, `\bvanakkam\b`, `\budavi\b`, `\bpanam\b`, `\bseiyavum\b`
- Kannada: `[\u0C80-\u0CFF]`, `\bnamaskara\b`, `\bsahaya\b`, `\bhana\b`, `\bmadikodi\b`

---

## 4. Confidence-Aware Processing & Safety Invariants

### 4.1 Confidence Evaluation
- **High Confidence ($\ge 0.80$):** High hit frequency across unambiguous terms. Automated routing proceeds.
- **Medium Confidence ($0.65 \le \text{Conf} < 0.80$):** Single hit or multiple close matches. Proceeds with policy audit tag.
- **Low Confidence ($< 0.65$):** Ambiguous or zero-hit text. Flags `needs_manual_review = True` and defaults to supervisor triage.

### 4.2 Hard Safety Invariants (Override ordinary AI)
1. **Rule SR-001 (Security Compromise Override):** Mentions of "hacked", "stolen", "unauthorized login", or "compromised" immediately force **P1** and `ACCOUNT_SECURITY`, overriding any customer or agent downgrade attempt.
2. **Rule SR-002 (System Outage Override):** Mentions of "production down", "emergency", or "complete outage" immediately enforce **P1**.
