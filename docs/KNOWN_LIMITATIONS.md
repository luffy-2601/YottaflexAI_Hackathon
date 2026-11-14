# OmniRoute AI — Known Limitations & Production Roadmap

In the interest of full engineering transparency, here are the known boundaries and future roadmap items for OmniRoute AI.

---

## 1. Relational Persistence & Concurrency
- **SQLite Single-Writer Boundary:** In the local demonstration environment, SQLite in WAL mode is used. While concurrent reads scale across multiple threads, SQLite serializes write transactions with a database-level lock. For large-scale production deployments (>1,000 writes/sec), changing `DATABASE_URL` in `.env` to PostgreSQL is required (fully supported by our SQLAlchemy ORM models).

---

## 2. Shift Boundary Transition Policy
- **Active In-Progress Work during Shift Rollover:** When an agent's working shift concludes while they are actively working on an `IN_PROGRESS` ticket, the ticket is not automatically yanked from their workspace. Instead, enterprise policy allows the agent to conclude the call/chat or initiate an explicit supervisor transfer to the incoming shift lead.

---

## 3. Multilingual Nuance & Dialects
- **Informal Transliteration Slang:** While Unicode Indic scripts (Telugu, Hindi, Tamil, Kannada) and common phonetic transliterations are recognized, colloquial SMS-slang without standard phonetic roots yields confidence $<0.65$. The engine safely flags these tickets with `needs_manual_review = True` and routes them to human supervisor triage rather than guessing incorrectly.

---

## 4. Multi-Tenant Administration
- **Tenant Self-Service UI:** Multi-tenancy is enforced at the database and API query levels (`tenant_id`), with cross-tenant isolation tested and passing. A dedicated super-admin tenant provisioning portal with custom domain CNAME mapping can be added in a future milestone.
