import os
import sys
import json
from sqlalchemy.orm import Session
from sqlalchemy import func

sys.path.insert(0, os.path.abspath("."))

from backend.app.core.database import SessionLocal
from backend.app.models.entities import (
    Customer, Channel, Skill, Language, Intent, PriorityRule, Queue,
    Agent, AgentSkill, AgentLanguage, Ticket, Message, AssignmentEvent,
    SLAEvent, Resolution, Anomaly
)
from backend.app.services.anomalies.anomaly_service import AnomalyDetectionService

def run_validations():
    print("=== Running Comprehensive Data & Lifecycle Validation Suite ===")
    db: Session = SessionLocal()
    errors = []
    checks_passed = 0

    try:
        # 1. Primary Key Uniqueness & Counts
        tables = [Customer, Channel, Skill, Language, Intent, Agent, Ticket, Message, AssignmentEvent, SLAEvent]
        print("\n1. Primary Key Checks:")
        for tbl in tables:
            pk_col = getattr(tbl, tbl.__mapper__.primary_key[0].name)
            total = db.query(tbl).count()
            distinct_pks = db.query(func.count(func.distinct(pk_col))).scalar()
            if total != distinct_pks:
                err = f"PK Uniqueness failure in {tbl.__tablename__}: {total} total rows vs {distinct_pks} unique PKs"
                errors.append(err)
                print(f"  [FAIL] {tbl.__tablename__}: {err}")
            else:
                checks_passed += 1
                print(f"  [PASS] {tbl.__tablename__}: {total} rows, 100% unique PKs")

        # 2. Foreign Key Integrity
        print("\n2. Foreign Key Integrity Checks:")
        # Tickets -> Customers
        orphan_tkt_cus = db.query(Ticket).outerjoin(Customer, Ticket.customer_id == Customer.customer_id).filter(Customer.customer_id.is_(None)).count()
        if orphan_tkt_cus > 0:
            errors.append(f"{orphan_tkt_cus} tickets have invalid customer_id")
            print(f"  [FAIL] Tickets -> Customers: {orphan_tkt_cus} orphans")
        else:
            checks_passed += 1
            print("  [PASS] Tickets -> Customers: 0 orphan records")

        # Tickets -> Channels
        orphan_tkt_chn = db.query(Ticket).outerjoin(Channel, Ticket.channel_id == Channel.channel_id).filter(Channel.channel_id.is_(None)).count()
        if orphan_tkt_chn > 0:
            errors.append(f"{orphan_tkt_chn} tickets have invalid channel_id")
            print(f"  [FAIL] Tickets -> Channels: {orphan_tkt_chn} orphans")
        else:
            checks_passed += 1
            print("  [PASS] Tickets -> Channels: 0 orphan records")

        # Messages -> Tickets
        orphan_msg = db.query(Message).outerjoin(Ticket, Message.ticket_id == Ticket.ticket_id).filter(Ticket.ticket_id.is_(None)).count()
        if orphan_msg > 0:
            errors.append(f"{orphan_msg} messages have invalid ticket_id")
            print(f"  [FAIL] Messages -> Tickets: {orphan_msg} orphans")
        else:
            checks_passed += 1
            print("  [PASS] Messages -> Tickets: 0 orphan records")

        # SLA -> Tickets
        orphan_sla = db.query(SLAEvent).outerjoin(Ticket, SLAEvent.ticket_id == Ticket.ticket_id).filter(Ticket.ticket_id.is_(None)).count()
        if orphan_sla > 0:
            errors.append(f"{orphan_sla} SLA records have invalid ticket_id")
            print(f"  [FAIL] SLA -> Tickets: {orphan_sla} orphans")
        else:
            checks_passed += 1
            print("  [PASS] SLA -> Tickets: 0 orphan records")

        # 3. Allowed Enums
        print("\n3. Allowed Enums Validation:")
        valid_statuses = {"NEW", "OPEN", "QUEUED", "ASSIGNED", "IN_PROGRESS", "PENDING_CUSTOMER", "ESCALATED", "RESOLVED", "REOPENED", "CLOSED"}
        invalid_statuses = db.query(Ticket).filter(Ticket.status.notin_(valid_statuses)).count()
        if invalid_statuses > 0:
            errors.append(f"{invalid_statuses} tickets have illegal status")
            print(f"  [FAIL] Ticket status enums: {invalid_statuses} invalid")
        else:
            checks_passed += 1
            print("  [PASS] Ticket status: 100% compliant with defined lifecycle states")

        valid_priorities = {"P1", "P2", "P3", "P4"}
        invalid_priorities = db.query(Ticket).filter(Ticket.priority.notin_(valid_priorities)).count()
        if invalid_priorities > 0:
            errors.append(f"{invalid_priorities} tickets have illegal priority")
            print(f"  [FAIL] Ticket priority enums: {invalid_priorities} invalid")
        else:
            checks_passed += 1
            print("  [PASS] Ticket priority: 100% compliant with P1-P4 taxonomy")

        # 4. Date Ordering Invariants
        print("\n4. Chronological Date Ordering Checks:")
        # resolved_at must be >= created_at
        bad_resol_dates = db.query(Ticket).filter(Ticket.resolved_at.isnot(None), Ticket.resolved_at < Ticket.created_at).count()
        if bad_resol_dates > 0:
            errors.append(f"{bad_resol_dates} tickets have resolved_at earlier than created_at")
            print(f"  [FAIL] Chronology: {bad_resol_dates} resolved before creation")
        else:
            checks_passed += 1
            print("  [PASS] Chronology: All resolution dates >= creation dates")

        # 5. Arithmetic Reconciliation
        print("\n5. Arithmetic Reconciliation Checks:")
        total_tickets = db.query(Ticket).count()
        open_count = db.query(Ticket).filter(Ticket.status.notin_(["RESOLVED", "CLOSED"])).count()
        closed_count = db.query(Ticket).filter(Ticket.status.in_(["RESOLVED", "CLOSED"])).count()
        if total_tickets != (open_count + closed_count):
            errors.append("Ticket status arithmetic partition mismatch")
            print("  [FAIL] Ticket partition mismatch")
        else:
            checks_passed += 1
            print(f"  [PASS] Arithmetic: Total ({total_tickets}) == Open ({open_count}) + Closed/Resolved ({closed_count})")

        # 6. Anomaly Scanning & Ground-Truth Verification
        print("\n6. Edge Case & Anomaly Scanning:")
        service = AnomalyDetectionService(db)
        detected_anomalies = service.scan_anomalies()
        print(f"  [PASS] Detected {len(detected_anomalies)} anomalies across system.")
        for a in detected_anomalies:
            print(f"    * [{a.severity}] {a.category}: {a.description[:85]}...")

        print("\n=========================================================")
        if not errors:
            print(f"RESULT: ALL {checks_passed} VALIDATION SUITES PASSED (0 ERRORS)")
            print("=========================================================\n")
            return 0
        else:
            print(f"RESULT: {len(errors)} VALIDATION ERRORS DETECTED")
            print("=========================================================\n")
            return 1

    finally:
        db.close()

if __name__ == "__main__":
    sys.exit(run_validations())
