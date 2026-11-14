import os
import sys
import json
import datetime
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.abspath("."))

from backend.app.core.database import SessionLocal, engine, Base
from backend.app.models.entities import (
    Customer, Channel, Skill, Language, Intent, PriorityRule, Queue,
    Agent, AgentSkill, AgentLanguage, AgentShift, Ticket, Message,
    AssignmentEvent, SLAEvent, Resolution, Anomaly, BusinessCalendar
)

def parse_dt(dt_str):
    if not dt_str:
        return None
    return datetime.datetime.fromisoformat(dt_str)

def seed_database(dataset_dir: str = "data/starter", reset_tables: bool = True):
    print(f"Seeding database from {dataset_dir} (reset={reset_tables})...")
    if reset_tables:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    try:
        # Load Channels
        with open(os.path.join(dataset_dir, "channels.json"), "r", encoding="utf-8") as f:
            for item in json.load(f):
                if not db.query(Channel).filter(Channel.channel_id == item["channel_id"]).first():
                    db.add(Channel(**item))

        # Load Languages
        with open(os.path.join(dataset_dir, "languages.json"), "r", encoding="utf-8") as f:
            for item in json.load(f):
                if not db.query(Language).filter(Language.language_code == item["language_code"]).first():
                    db.add(Language(**item))

        # Load Skills
        with open(os.path.join(dataset_dir, "skills.json"), "r", encoding="utf-8") as f:
            for item in json.load(f):
                if not db.query(Skill).filter(Skill.skill_id == item["skill_id"]).first():
                    db.add(Skill(**item))

        # Load Intents
        with open(os.path.join(dataset_dir, "intents.json"), "r", encoding="utf-8") as f:
            for item in json.load(f):
                if not db.query(Intent).filter(Intent.intent_id == item["intent_id"]).first():
                    db.add(Intent(**item))

        # Load Priority Rules
        with open(os.path.join(dataset_dir, "priority_rules.json"), "r", encoding="utf-8") as f:
            for item in json.load(f):
                if not db.query(PriorityRule).filter(PriorityRule.rule_id == item["rule_id"]).first():
                    db.add(PriorityRule(**item))

        # Load Queues
        with open(os.path.join(dataset_dir, "queues.json"), "r", encoding="utf-8") as f:
            for item in json.load(f):
                if not db.query(Queue).filter(Queue.queue_id == item["queue_id"]).first():
                    db.add(Queue(**item))

        # Load Agents
        with open(os.path.join(dataset_dir, "agents.json"), "r", encoding="utf-8") as f:
            for item in json.load(f):
                if not db.query(Agent).filter(Agent.agent_id == item["agent_id"]).first():
                    row = dict(item)
                    row["created_at"] = parse_dt(row["created_at"])
                    db.add(Agent(**row))

        db.flush()

        # Load Agent Skills
        with open(os.path.join(dataset_dir, "agent_skills.json"), "r", encoding="utf-8") as f:
            for item in json.load(f):
                if not db.query(AgentSkill).filter(
                    AgentSkill.agent_id == item["agent_id"],
                    AgentSkill.skill_id == item["skill_id"]
                ).first():
                    db.add(AgentSkill(**item))

        # Load Agent Languages
        with open(os.path.join(dataset_dir, "agent_languages.json"), "r", encoding="utf-8") as f:
            for item in json.load(f):
                if not db.query(AgentLanguage).filter(
                    AgentLanguage.agent_id == item["agent_id"],
                    AgentLanguage.language_code == item["language_code"]
                ).first():
                    db.add(AgentLanguage(**item))

        # Load Agent Shifts
        with open(os.path.join(dataset_dir, "agent_shifts.json"), "r", encoding="utf-8") as f:
            for item in json.load(f):
                if not db.query(AgentShift).filter(AgentShift.shift_id == item["shift_id"]).first():
                    db.add(AgentShift(**item))

        # Load Customers
        with open(os.path.join(dataset_dir, "customers.json"), "r", encoding="utf-8") as f:
            for item in json.load(f):
                if not db.query(Customer).filter(Customer.customer_id == item["customer_id"]).first():
                    row = dict(item)
                    row["created_at"] = parse_dt(row["created_at"])
                    db.add(Customer(**row))

        db.flush()

        # Load Tickets
        with open(os.path.join(dataset_dir, "tickets.json"), "r", encoding="utf-8") as f:
            for item in json.load(f):
                if not db.query(Ticket).filter(Ticket.ticket_id == item["ticket_id"]).first():
                    row = dict(item)
                    row["created_at"] = parse_dt(row["created_at"])
                    row["updated_at"] = parse_dt(row["updated_at"])
                    row["first_response_at"] = parse_dt(row["first_response_at"])
                    row["resolved_at"] = parse_dt(row["resolved_at"])
                    db.add(Ticket(**row))

        db.flush()

        # Load Messages
        with open(os.path.join(dataset_dir, "messages.json"), "r", encoding="utf-8") as f:
            for item in json.load(f):
                if not db.query(Message).filter(Message.message_id == item["message_id"]).first():
                    row = dict(item)
                    row["created_at"] = parse_dt(row["created_at"])
                    db.add(Message(**row))

        # Load Assignment Events
        with open(os.path.join(dataset_dir, "assignment_events.json"), "r", encoding="utf-8") as f:
            for item in json.load(f):
                if not db.query(AssignmentEvent).filter(AssignmentEvent.assignment_id == item["assignment_id"]).first():
                    row = dict(item)
                    row["created_at"] = parse_dt(row["created_at"])
                    db.add(AssignmentEvent(**row))

        # Load SLA Events
        with open(os.path.join(dataset_dir, "sla_events.json"), "r", encoding="utf-8") as f:
            for item in json.load(f):
                if not db.query(SLAEvent).filter(SLAEvent.sla_id == item["sla_id"]).first():
                    row = dict(item)
                    row["first_response_due_at"] = parse_dt(row["first_response_due_at"])
                    row["resolution_due_at"] = parse_dt(row["resolution_due_at"])
                    row["first_response_actual_at"] = parse_dt(row["first_response_actual_at"])
                    row["resolution_actual_at"] = parse_dt(row["resolution_actual_at"])
                    row["created_at"] = parse_dt(row["created_at"])
                    row["updated_at"] = parse_dt(row["updated_at"])
                    db.add(SLAEvent(**row))

        # Load Resolutions
        with open(os.path.join(dataset_dir, "resolutions.json"), "r", encoding="utf-8") as f:
            for item in json.load(f):
                if not db.query(Resolution).filter(Resolution.resolution_id == item["resolution_id"]).first():
                    row = dict(item)
                    row["created_at"] = parse_dt(row["created_at"])
                    db.add(Resolution(**row))

        db.commit()
        print("Database successfully seeded with master, agent, ticket, SLA, and event records!")

    except Exception as e:
        db.rollback()
        print(f"Error during seeding: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
