import argparse
import datetime
import hashlib
import json
import math
import os
import random
import sys
from typing import Dict, List, Any
from faker import Faker

# Core Taxonomy Definitions
CHANNELS = [
    {"channel_id": "email", "name": "Email Ingestion", "default_sla_factor": 1.0, "is_active": True},
    {"channel_id": "chat", "name": "Live Chat", "default_sla_factor": 0.5, "is_active": True},
    {"channel_id": "phone", "name": "Voice / Phone", "default_sla_factor": 0.2, "is_active": True}
]

LANGUAGES = [
    {"language_code": "en", "name": "English", "is_supported": True},
    {"language_code": "te", "name": "Telugu", "is_supported": True},
    {"language_code": "hi", "name": "Hindi", "is_supported": True},
    {"language_code": "ta", "name": "Tamil", "is_supported": True},
    {"language_code": "kn", "name": "Kannada", "is_supported": True}
]

SKILLS = [
    {"skill_id": "PAYMENT_GATEWAY", "name": "Payment Gateway & UPI Protocols", "tier_level": 2},
    {"skill_id": "SECURITY_FORENSICS", "name": "Account Security & Fraud Triage", "tier_level": 3},
    {"skill_id": "INFRA_SYSADMIN", "name": "Cloud Infrastructure & Backend Systems", "tier_level": 3},
    {"skill_id": "BILLING_OPERATIONS", "name": "Invoicing & Subscription Audits", "tier_level": 1},
    {"skill_id": "CUSTOMER_SUCCESS", "name": "General Inquiries & Account Care", "tier_level": 1}
]

INTENTS = [
    {"intent_id": "ACCOUNT_SECURITY", "name": "Account Security & Fraud", "category": "SECURITY", "default_priority": "P1", "required_skill_id": "SECURITY_FORENSICS"},
    {"intent_id": "PAYMENT_FAILURE", "name": "Payment Transaction Failure", "category": "BILLING", "default_priority": "P2", "required_skill_id": "PAYMENT_GATEWAY"},
    {"intent_id": "PAYMENT_DUPLICATE", "name": "Duplicate Debit Issue", "category": "BILLING", "default_priority": "P2", "required_skill_id": "PAYMENT_GATEWAY"},
    {"intent_id": "TECHNICAL_ISSUE", "name": "Service Outage or Bug", "category": "TECH", "default_priority": "P2", "required_skill_id": "INFRA_SYSADMIN"},
    {"intent_id": "REFUND_REQUEST", "name": "Refund Claim", "category": "BILLING", "default_priority": "P3", "required_skill_id": "BILLING_OPERATIONS"},
    {"intent_id": "LOGIN_ISSUE", "name": "Authentication Error / OTP", "category": "AUTH", "default_priority": "P3", "required_skill_id": "CUSTOMER_SUCCESS"},
    {"intent_id": "BILLING_QUERY", "name": "Invoice / Pricing Explanation", "category": "BILLING", "default_priority": "P3", "required_skill_id": "BILLING_OPERATIONS"},
    {"intent_id": "ORDER_STATUS", "name": "Shipment Tracking", "category": "OPERATIONS", "default_priority": "P3", "required_skill_id": "CUSTOMER_SUCCESS"},
    {"intent_id": "ACCOUNT_UPDATE", "name": "Profile Details Update", "category": "AUTH", "default_priority": "P4", "required_skill_id": "CUSTOMER_SUCCESS"},
    {"intent_id": "GENERAL_ENQUIRY", "name": "General Platform Inquiry", "category": "GENERAL", "default_priority": "P4", "required_skill_id": "CUSTOMER_SUCCESS"}
]

PRIORITY_RULES = [
    {"rule_id": "PR-001", "rule_name": "Account Compromise Safety Invariant", "intent_id": "ACCOUNT_SECURITY", "trigger_keyword": "stolen", "enforced_priority": "P1", "is_safety_critical": True},
    {"rule_id": "PR-002", "rule_name": "Payment Gateway Hard Down", "intent_id": "PAYMENT_FAILURE", "trigger_keyword": "production down", "enforced_priority": "P1", "is_safety_critical": True},
    {"rule_id": "PR-003", "rule_name": "Standard Billing High", "intent_id": "PAYMENT_DUPLICATE", "trigger_keyword": "double charge", "enforced_priority": "P2", "is_safety_critical": False}
]

QUEUES = [
    {"queue_id": "Q_CRITICAL_INCIDENTS", "name": "Critical Incidents & Security", "channel_id": "email", "priority_min": "P1", "routing_strategy": "INTELLIGENT"},
    {"queue_id": "Q_TIER2_PAYMENTS", "name": "Payment Processing Escalations", "channel_id": "chat", "priority_min": "P2", "routing_strategy": "INTELLIGENT"},
    {"queue_id": "Q_GENERAL_SUPPORT", "name": "Omnichannel General Support", "channel_id": "email", "priority_min": "P4", "routing_strategy": "INTELLIGENT"}
]

SAMPLE_SUBJECTS = {
    "ACCOUNT_SECURITY": ["Unauthorized login attempt detected from foreign IP", "Someone compromised my account credentials", "Suspicious password reset SMS received", "Credit card stolen and added to account"],
    "PAYMENT_FAILURE": ["UPI payment debited from bank but transaction failed", "Credit card payment declined at checkout", "Gateway error 504 on net banking payment", "Money deducted during subscription renewal"],
    "PAYMENT_DUPLICATE": ["Charged twice for order #58392", "Double deduction on monthly renewal", "Duplicate invoice created for single transaction"],
    "TECHNICAL_ISSUE": ["Application crashing immediately upon launch", "500 Internal server error on reporting API", "Blank white dashboard after recent deployment"],
    "REFUND_REQUEST": ["Requesting immediate refund for cancelled subscription", "Order returned please process refund", "Refund not credited after 7 business days"],
    "LOGIN_ISSUE": ["OTP not coming on registered phone number", "Account locked after 3 attempts", "2FA authentication code invalid"],
    "BILLING_QUERY": ["Need GST tax invoice for last quarter", "Clarification on foreign currency conversion fee", "Explanation for unexpected charge on statement"],
    "ORDER_STATUS": ["Where is my courier shipment", "Delivery tracking link expired", "Shipment stuck in transit for 4 days"],
    "ACCOUNT_UPDATE": ["Request to update primary business email", "Phone number migration request", "Company address change for billing"],
    "GENERAL_ENQUIRY": ["Inquiry regarding annual enterprise plans", "Do you offer on-premise deployment", "Customer support phone operating hours"]
}

AGENT_FIRST_NAMES = ["Aarav", "Priya", "Vikram", "Ananya", "Rohan", "Sneha", "Karthik", "Divya", "Rahul", "Pooja", "Arjun", "Meera", "Sanjay", "Neha", "Aditya", "Deepa", "Naveen", "Swathi", "Harish", "Kavita"]
AGENT_LAST_NAMES = ["Sharma", "Verma", "Rao", "Reddy", "Patel", "Nair", "Iyer", "Kumar", "Choudhury", "Menon", "Joshi", "Bhat", "Deshmukh", "Pillai", "Gupta"]

CUSTOMER_FIRST_NAMES = ["John", "Sarah", "Michael", "Emily", "David", "Jessica", "James", "Laura", "Daniel", "Samantha", "Amit", "Sunita", "Ramesh", "Geeta", "Venkat", "Lakshmi"]
CUSTOMER_LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Wilson", "Taylor", "Anderson", "Thomas", "Jackson", "White", "Harris", "Martin"]

def generate_dataset(scale: str, seed: int, output_dir: str):
    random.seed(seed)
    Faker.seed(seed)
    fake = Faker(['en_IN', 'en_US'])
    base_time = datetime.datetime(2026, 8, 1, 9, 0, 0, tzinfo=datetime.timezone.utc)
    now = datetime.datetime(2026, 11, 1, 18, 0, 0, tzinfo=datetime.timezone.utc)
    
    target_agents = 100 # Exactly 100 human support agents
    if scale == "full":
        target_tickets = 30000
        target_messages = 100000
    else: # starter scale
        target_tickets = 1000
        target_messages = 3500

    print(f"=== Synthetic Data Generation ({scale.upper()} SCALE) ===")
    print(f"Seed: {seed} | Tickets: {target_tickets} | Agents: {target_agents} | Target Messages: {target_messages}")

    os.makedirs(output_dir, exist_ok=True)

    # 1. Generate 100 Agents using Faker
    agents = []
    agent_skills = []
    agent_languages = []
    agent_shifts = []

    for i in range(1, target_agents + 1):
        agt_id = f"AGT-{i:06d}"
        name = fake.name()
        clean_name = "".join(c for c in name.lower() if c.isalnum() or c == ' ').strip().replace(' ', '.')
        email = f"{clean_name}.{i}@supportops.internal"
        max_conc = random.choice([2, 3, 4, 5])
        exp = round(random.uniform(0.65, 0.99), 2)
        status = random.choices(["ACTIVE", "ON_BREAK", "INACTIVE"], weights=[0.85, 0.10, 0.05])[0]
        
        agents.append({
            "agent_id": agt_id,
            "name": name,
            "email": email,
            "status": status,
            "max_concurrency": max_conc,
            "current_active_tickets": 0,
            "experience_score": exp,
            "created_at": (base_time - datetime.timedelta(days=random.randint(30, 365))).isoformat()
        })

        # Assign 2 to 5 skills with proficiency
        num_skills = random.randint(2, min(5, len(SKILLS)))
        assigned_skills = random.sample(SKILLS, k=num_skills)
        for sk in assigned_skills:
            agent_skills.append({
                "agent_id": agt_id,
                "skill_id": sk["skill_id"],
                "proficiency_level": round(random.uniform(0.70, 1.00), 2)
            })

        # Assign English + 1 or 2 regional languages
        assigned_langs = ["en"]
        extra_langs = random.sample(["te", "hi", "ta", "kn"], k=random.randint(1, 2))
        assigned_langs.extend(extra_langs)
        for lang in assigned_langs:
            agent_languages.append({
                "agent_id": agt_id,
                "language_code": lang,
                "fluency_score": 1.0 if lang == "en" else round(random.uniform(0.80, 1.00), 2)
            })

        # Assign Shifts (including 24/7 and weekend shift coverage)
        shift_pattern = random.choice([
            {"start": 9, "end": 18},
            {"start": 6, "end": 15},
            {"start": 14, "end": 23},
            {"start": 0, "end": 24}
        ])
        days_covered = range(7) if i % 2 == 0 else range(5)
        for day in days_covered:
            agent_shifts.append({
                "shift_id": f"SHF-{agt_id}-{day}",
                "agent_id": agt_id,
                "day_of_week": day,
                "start_hour": shift_pattern["start"],
                "end_hour": shift_pattern["end"],
                "timezone": "Asia/Kolkata"
            })

    # 2. Generate Customers
    num_customers = max(50, target_tickets // 5)
    customers = []
    for i in range(1, num_customers + 1):
        cus_id = f"CUS-{i:06d}"
        c_fname = random.choice(CUSTOMER_FIRST_NAMES)
        c_lname = random.choice(CUSTOMER_LAST_NAMES)
        tier = random.choices(["STANDARD", "VIP", "ENTERPRISE"], weights=[0.75, 0.20, 0.05])[0]
        customers.append({
            "customer_id": cus_id,
            "name": f"{c_fname} {c_lname}",
            "email": f"{c_fname.lower()}.{c_lname.lower()}{i}@clientcorp.com",
            "phone": f"+9198{random.randint(10000000, 99999999)}",
            "tier": tier,
            "created_at": (base_time - datetime.timedelta(days=random.randint(10, 180))).isoformat()
        })

    # 3. Generate Tickets, Messages, SLAs, Assignments, Decisions
    tickets = []
    messages = []
    assignment_events = []
    sla_events = []
    routing_decisions = []
    resolutions = []
    status_events = []
    ground_truth_anomalies = []

    # Pre-select deterministic indices for injecting the 5 required edge cases
    # Anomaly 1: Agent assigned beyond capacity
    anom_1_idx = 14
    # Anomaly 2: SLA ignores channel calendar
    anom_2_idx = 28
    # Anomaly 3: Reopened ticket loses historical records
    anom_3_idx = 42
    # Anomaly 4: Repeated transfer loop
    anom_4_idx = 56
    # Anomaly 5: Priority contradicts defined safety rule
    anom_5_idx = 70

    for idx in range(1, target_tickets + 1):
        tkt_id = f"TKT-2026-{idx:06d}"
        cus = random.choice(customers)
        channel = random.choices(CHANNELS, weights=[0.45, 0.35, 0.20])[0]
        intent = random.choice(INTENTS)
        lang = random.choices(["en", "te", "hi", "ta", "kn"], weights=[0.55, 0.15, 0.15, 0.10, 0.05])[0]
        
        # Determine priority
        priority = intent["default_priority"]
        if cus["tier"] == "VIP" and priority in ["P3", "P4"]:
            priority = "P2"
        elif cus["tier"] == "ENTERPRISE" and priority != "P1":
            priority = "P2"

        # Edge Case 5: Priority contradicts defined safety rule
        if idx == anom_5_idx:
            intent = next(item for item in INTENTS if item["intent_id"] == "ACCOUNT_SECURITY")
            priority = "P4" # Deliberate contradiction of safety invariant!
            ground_truth_anomalies.append({
                "anomaly_id": f"GT-ANOM-005-{tkt_id}",
                "ticket_id": tkt_id,
                "category": "SAFETY_VIOLATION",
                "severity": "CRITICAL",
                "description": "Account security breach ticket downgraded to P4, violating deterministic safety rule.",
                "expected_behavior": "Intent ACCOUNT_SECURITY must strictly enforce P1 priority.",
                "actual_behavior": f"Priority set to {priority}."
            })

        # Creation timestamp within the 90 days span
        created_sec_offset = random.randint(0, int((now - base_time).total_seconds()))
        tkt_created = base_time + datetime.timedelta(seconds=created_sec_offset)

        subject = random.choice(SAMPLE_SUBJECTS[intent["intent_id"]])
        body = f"Hello support team, {subject}. Please assist urgently. Reference ID: REF-{random.randint(1000, 9999)}."

        # Assign Agent matching skill and language
        eligible = [
            a for a in agents
            if any(s["skill_id"] == intent["required_skill_id"] for s in agent_skills if s["agent_id"] == a["agent_id"])
            and a["current_active_tickets"] < a["max_concurrency"]
        ]

        assigned_agent = None
        if eligible:
            # Score eligible
            assigned_agent = random.choice(eligible)
            assigned_agent["current_active_tickets"] += 1
            status = random.choices(["RESOLVED", "IN_PROGRESS", "ASSIGNED"], weights=[0.70, 0.20, 0.10])[0]
        else:
            status = "QUEUED"

        # Edge Case 1: Agent assigned beyond capacity
        if idx == anom_1_idx:
            overload_agent = agents[0]
            overload_agent["current_active_tickets"] = overload_agent["max_concurrency"] + 3 # Exceeds limit
            assigned_agent = overload_agent
            status = "ASSIGNED"
            ground_truth_anomalies.append({
                "anomaly_id": f"GT-ANOM-001-{tkt_id}",
                "ticket_id": tkt_id,
                "agent_id": overload_agent["agent_id"],
                "category": "CAPACITY_VIOLATION",
                "severity": "HIGH",
                "description": f"Agent {overload_agent['agent_id']} assigned ticket despite active ticket count ({overload_agent['current_active_tickets']}) exceeding limit ({overload_agent['max_concurrency']}).",
                "expected_behavior": f"Agent must never receive assignments exceeding max concurrency.",
                "actual_behavior": f"Active tickets: {overload_agent['current_active_tickets']} vs limit {overload_agent['max_concurrency']}."
            })

        # Edge Case 4: Repeated transfer loop
        is_transfer_loop = (idx == anom_4_idx)

        # Edge Case 3: Reopened ticket loses historical records
        is_history_loss = (idx == anom_3_idx)
        if is_history_loss:
            status = "REOPENED"
            ground_truth_anomalies.append({
                "anomaly_id": f"GT-ANOM-003-{tkt_id}",
                "ticket_id": tkt_id,
                "category": "HISTORY_LOSS",
                "severity": "HIGH",
                "description": f"Ticket {tkt_id} was reopened but its previous thread messages and assignment events were wiped.",
                "expected_behavior": "Reopened tickets must retain complete chronological message and event audit trail.",
                "actual_behavior": "Prior historical records truncated."
            })

        # SLA Deadlines
        prio_frt_mins = {"P1": 5, "P2": 15, "P3": 60, "P4": 240}[priority]
        prio_res_mins = {"P1": 60, "P2": 240, "P3": 480, "P4": 1440}[priority]
        sla_factor = channel["default_sla_factor"]

        # Edge Case 2: SLA ignores channel calendar
        if idx == anom_2_idx:
            channel = next(c for c in CHANNELS if c["channel_id"] == "phone")
            prio_frt_mins = 360 # Slow async deadline given to synchronous phone call!
            ground_truth_anomalies.append({
                "anomaly_id": f"GT-ANOM-002-{tkt_id}",
                "ticket_id": tkt_id,
                "category": "CALENDAR_MISMATCH",
                "severity": "MEDIUM",
                "description": f"Phone ticket {tkt_id} assigned 360 min SLA, completely ignoring synchronous phone channel policies.",
                "expected_behavior": "Phone tickets must enforce synchronous immediate SLA (< 15 mins).",
                "actual_behavior": "Assigned async 360 mins deadline."
            })

        first_resp_due = tkt_created + datetime.timedelta(minutes=int(prio_frt_mins * sla_factor))
        resol_due = tkt_created + datetime.timedelta(minutes=int(prio_res_mins * sla_factor))

        first_resp_actual = None
        resol_actual = None
        is_frt_breach = False
        is_res_breach = False

        if status in ["IN_PROGRESS", "ASSIGNED", "RESOLVED"]:
            upper_frt = max(2, int(prio_frt_mins * sla_factor * 1.5))
            resp_lag = random.randint(1, upper_frt)
            first_resp_actual = tkt_created + datetime.timedelta(minutes=resp_lag)
            if first_resp_actual > first_resp_due:
                is_frt_breach = True

        if status == "RESOLVED":
            upper_res = max(10, int(prio_res_mins * sla_factor * 1.3))
            res_lag = random.randint(5, upper_res)
            resol_actual = tkt_created + datetime.timedelta(minutes=res_lag)
            if resol_actual > resol_due:
                is_res_breach = True
            # Release concurrency capacity for resolved ticket
            if assigned_agent and assigned_agent["current_active_tickets"] > 0:
                assigned_agent["current_active_tickets"] -= 1

        # Append Ticket
        tickets.append({
            "ticket_id": tkt_id,
            "customer_id": cus["customer_id"],
            "channel_id": channel["channel_id"],
            "subject": subject,
            "status": status,
            "priority": priority,
            "intent_id": intent["intent_id"],
            "language_code": lang,
            "assigned_agent_id": assigned_agent["agent_id"] if assigned_agent else None,
            "queue_id": "Q_CRITICAL_INCIDENTS" if priority == "P1" else "Q_GENERAL_SUPPORT",
            "created_at": tkt_created.isoformat(),
            "updated_at": (resol_actual or first_resp_actual or tkt_created).isoformat(),
            "first_response_at": first_resp_actual.isoformat() if first_resp_actual else None,
            "resolved_at": resol_actual.isoformat() if resol_actual else None
        })

        # Append Initial Message
        if not is_history_loss:
            messages.append({
                "message_id": f"MSG-{tkt_id}-001",
                "ticket_id": tkt_id,
                "sender_type": "CUSTOMER",
                "sender_id": cus["customer_id"],
                "body": body,
                "sentiment_score": round(random.uniform(-0.5, 0.1), 2),
                "created_at": tkt_created.isoformat()
            })

            # Append Agent Response Message if replied
            if first_resp_actual and assigned_agent:
                messages.append({
                    "message_id": f"MSG-{tkt_id}-002",
                    "ticket_id": tkt_id,
                    "sender_type": "AGENT",
                    "sender_id": assigned_agent["agent_id"],
                    "body": f"Hello {cus['name']}, thank you for contacting us. I am investigating this issue right away.",
                    "sentiment_score": 0.40,
                    "created_at": first_resp_actual.isoformat()
                })

        # Append Assignment Event
        if assigned_agent and not is_history_loss:
            assignment_events.append({
                "assignment_id": f"ASN-{tkt_id}-001",
                "ticket_id": tkt_id,
                "agent_id": assigned_agent["agent_id"],
                "event_type": "INITIAL_ASSIGN",
                "actor_id": "SYSTEM_ROUTER",
                "reason": f"Matched required skill '{intent['required_skill_id']}' and language '{lang}'.",
                "created_at": tkt_created.isoformat()
            })

            # If transfer loop edge case, inject repetitive transfers
            if is_transfer_loop:
                agent_a = assigned_agent["agent_id"]
                agent_b = agents[1]["agent_id"] if agents[1]["agent_id"] != agent_a else agents[2]["agent_id"]
                assignment_events.append({
                    "assignment_id": f"ASN-{tkt_id}-002",
                    "ticket_id": tkt_id,
                    "agent_id": agent_b,
                    "event_type": "TRANSFER",
                    "actor_id": "AGENT",
                    "reason": "Transferred to colleague",
                    "created_at": (tkt_created + datetime.timedelta(minutes=10)).isoformat()
                })
                assignment_events.append({
                    "assignment_id": f"ASN-{tkt_id}-003",
                    "ticket_id": tkt_id,
                    "agent_id": agent_a,
                    "event_type": "TRANSFER",
                    "actor_id": "AGENT",
                    "reason": "Transferred back",
                    "created_at": (tkt_created + datetime.timedelta(minutes=20)).isoformat()
                })
                ground_truth_anomalies.append({
                    "anomaly_id": f"GT-ANOM-004-{tkt_id}",
                    "ticket_id": tkt_id,
                    "category": "TRANSFER_LOOP",
                    "severity": "HIGH",
                    "description": f"Ticket {tkt_id} caught in cyclic ping-pong transfer between {agent_a} and {agent_b}.",
                    "expected_behavior": "Reassignments must advance ticket towards resolution; cyclic bounce is an anomaly.",
                    "actual_behavior": f"Cyclic transfer pattern: {agent_a} -> {agent_b} -> {agent_a}."
                })

        # Append SLA Event
        sla_events.append({
            "sla_id": f"SLA-{tkt_id}",
            "ticket_id": tkt_id,
            "first_response_due_at": first_resp_due.isoformat(),
            "resolution_due_at": resol_due.isoformat(),
            "first_response_actual_at": first_resp_actual.isoformat() if first_resp_actual else None,
            "resolution_actual_at": resol_actual.isoformat() if resol_actual else None,
            "is_first_response_breached": is_frt_breach,
            "is_resolution_breached": is_res_breach,
            "status": "BREACHED" if (is_frt_breach or is_res_breach) else ("MET" if status == "RESOLVED" else "RUNNING"),
            "created_at": tkt_created.isoformat(),
            "updated_at": (resol_actual or first_resp_actual or tkt_created).isoformat()
        })

        # Append Resolution if resolved
        if status == "RESOLVED" and assigned_agent and resol_actual:
            resolutions.append({
                "resolution_id": f"RES-{tkt_id}",
                "ticket_id": tkt_id,
                "agent_id": assigned_agent["agent_id"],
                "resolution_code": "SOLVED",
                "summary": f"Issue resolved successfully by updating system configuration and notifying client.",
                "csat_score": random.choices([5, 4, 3, 2, 1], weights=[0.55, 0.25, 0.12, 0.05, 0.03])[0],
                "csat_feedback": "Prompt and clear resolution, thank you!",
                "created_at": resol_actual.isoformat()
            })

    # Export to JSON and CSV files
    data_bundles = {
        "channels": CHANNELS,
        "languages": LANGUAGES,
        "skills": SKILLS,
        "intents": INTENTS,
        "priority_rules": PRIORITY_RULES,
        "queues": QUEUES,
        "agents": agents,
        "agent_skills": agent_skills,
        "agent_languages": agent_languages,
        "agent_shifts": agent_shifts,
        "customers": customers,
        "tickets": tickets,
        "messages": messages,
        "assignment_events": assignment_events,
        "sla_events": sla_events,
        "resolutions": resolutions
    }

    manifest = {"generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "seed": seed, "scale": scale, "files": {}}

    for name, records in data_bundles.items():
        # JSON export
        json_path = os.path.join(output_dir, f"{name}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)

        # CSV export
        csv_path = os.path.join(output_dir, f"{name}.csv")
        if records:
            keys = list(records[0].keys())
            with open(csv_path, "w", encoding="utf-8") as f:
                f.write(",".join(keys) + "\n")
                for r in records:
                    row_vals = []
                    for k in keys:
                        v = str(r.get(k, "")).replace('"', '""')
                        if "," in v or "\n" in v or '"' in v:
                            row_vals.append(f'"{v}"')
                        else:
                            row_vals.append(v)
                    f.write(",".join(row_vals) + "\n")

        # Compute checksum
        with open(json_path, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
        manifest["files"][f"{name}.json"] = {"count": len(records), "sha256": file_hash}

    # Save Ground Truth Anomalies separately
    gt_dir = os.path.join(os.path.dirname(output_dir), "ground_truth")
    os.makedirs(gt_dir, exist_ok=True)
    gt_json = os.path.join(gt_dir, f"ground_truth_{scale}.json")
    with open(gt_json, "w", encoding="utf-8") as f:
        json.dump(ground_truth_anomalies, f, indent=2)

    # Save Manifest
    manifest_path = os.path.join(output_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Generated {len(tickets)} tickets, {len(agents)} agents, {len(messages)} messages.")
    print(f"Injected {len(ground_truth_anomalies)} labeled anomalies into ground truth.")
    print(f"Manifest and SHA-256 checksums written to {manifest_path}")

    return manifest

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Synthetic Omnichannel Ticket & SLA Data Generator")
    parser.add_argument("--scale", choices=["starter", "full"], default="starter", help="Dataset scale")
    parser.add_argument("--seed", type=int, default=20261022, help="Fixed deterministic seed")
    parser.add_argument("--output", type=str, default="", help="Custom output directory")
    args = parser.parse_args()

    out_dir = args.output or os.path.join("data", args.scale)
    generate_dataset(scale=args.scale, seed=args.seed, output_dir=out_dir)
