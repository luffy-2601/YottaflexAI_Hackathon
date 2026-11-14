import os
import sys
import random
import datetime
from faker import Faker

sys.path.insert(0, os.path.abspath("."))

from backend.app.core.database import SessionLocal, Base, engine
from backend.app.models.entities import (
    Agent, AgentSkill, AgentLanguage, AgentShift, AgentQueue,
    Skill, Language, Queue
)

def generate_workforce(target_count: int = 100, seed: int = 20261022):
    print(f"=== Generating {target_count} Simulated Human Support Agents (Seed: {seed}) ===")
    random.seed(seed)
    Faker.seed(seed)
    fake = Faker(['en_IN', 'en_US'])

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Verify master skills exist
        available_skills = db.query(Skill).all()
        if not available_skills:
            print("Master skills table empty. Ensuring master skills...")
            default_skills = [
                Skill(skill_id="PAYMENT_GATEWAY", name="Payment Gateway & UPI Protocols", tier_level=2),
                Skill(skill_id="SECURITY_FORENSICS", name="Account Security & Fraud Triage", tier_level=3),
                Skill(skill_id="INFRA_SYSADMIN", name="Cloud Infrastructure & Backend Systems", tier_level=3),
                Skill(skill_id="BILLING_OPERATIONS", name="Invoicing & Subscription Audits", tier_level=1),
                Skill(skill_id="CUSTOMER_SUCCESS", name="General Inquiries & Account Care", tier_level=1)
            ]
            db.add_all(default_skills)
            db.flush()
            available_skills = default_skills

        # Verify languages exist
        available_languages = db.query(Language).all()
        if not available_languages:
            default_langs = [
                Language(language_code="en", name="English", is_supported=True),
                Language(language_code="te", name="Telugu", is_supported=True),
                Language(language_code="hi", name="Hindi", is_supported=True),
                Language(language_code="ta", name="Tamil", is_supported=True),
                Language(language_code="kn", name="Kannada", is_supported=True)
            ]
            db.add_all(default_langs)
            db.flush()
            available_languages = default_langs

        # Verify queues exist
        available_queues = db.query(Queue).all()
        if not available_queues:
            default_queues = [
                Queue(queue_id="Q_CRITICAL_INCIDENTS", name="Critical Incidents & Security", channel_id="email", priority_min="P1"),
                Queue(queue_id="Q_TIER2_PAYMENTS", name="Payment Processing Escalations", channel_id="chat", priority_min="P2"),
                Queue(queue_id="Q_GENERAL_SUPPORT", name="Omnichannel General Support", channel_id="email", priority_min="P4")
            ]
            db.add_all(default_queues)
            db.flush()
            available_queues = default_queues

        skill_ids = [s.skill_id for s in available_skills]
        lang_codes = [l.language_code for l in available_languages]
        queue_ids = [q.queue_id for q in available_queues]

        # Clear existing agents to strictly guarantee fresh 100 normalized records
        db.query(AgentSkill).delete()
        db.query(AgentLanguage).delete()
        db.query(AgentShift).delete()
        db.query(AgentQueue).delete()
        db.query(Agent).delete()
        db.commit()

        base_time = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
        agents_created = 0
        agent_skills_created = 0
        agent_langs_created = 0
        agent_shifts_created = 0
        agent_queues_created = 0

        for i in range(1, target_count + 1):
            agt_id = f"AGT-{i:06d}"
            name = fake.name()
            # Clean email from name
            clean_name = "".join(c for c in name.lower() if c.isalnum() or c == ' ').strip().replace(' ', '.')
            email = f"{clean_name}.{i}@supportops.internal"
            
            # Availability status: 85% Active, 10% On Break, 5% Inactive
            status = random.choices(["ACTIVE", "ON_BREAK", "INACTIVE"], weights=[0.85, 0.10, 0.05])[0]
            max_concurrency = random.choice([2, 3, 4, 5])
            experience_score = round(random.uniform(0.65, 0.99), 2)
            created_at = base_time + datetime.timedelta(days=random.randint(1, 250))

            agent = Agent(
                agent_id=agt_id,
                name=name,
                email=email,
                status=status,
                max_concurrency=max_concurrency,
                current_active_tickets=0,
                experience_score=experience_score,
                created_at=created_at
            )
            db.add(agent)
            db.flush()
            agents_created += 1

            # 1. Assign 2 to 5 Skills with realistic proficiency
            num_skills = random.randint(2, min(5, len(skill_ids)))
            assigned_skills = random.sample(skill_ids, k=num_skills)
            for sk_id in assigned_skills:
                # Primary skill has higher proficiency
                prof = round(random.uniform(0.75, 1.00), 2)
                db.add(AgentSkill(agent_id=agt_id, skill_id=sk_id, proficiency_level=prof))
                agent_skills_created += 1

            # 2. Assign Languages (English + 1 or 2 regional Indian languages)
            assigned_langs = ["en"]
            regional = [l for l in lang_codes if l != "en"]
            extra = random.sample(regional, k=random.randint(1, min(2, len(regional))))
            assigned_langs.extend(extra)
            for l_code in assigned_langs:
                fluency = 1.0 if l_code == "en" else round(random.uniform(0.80, 1.00), 2)
                db.add(AgentLanguage(agent_id=agt_id, language_code=l_code, fluency_score=fluency))
                agent_langs_created += 1

            # 3. Assign Shift Schedules (including 24/7 and weekend shift coverage)
            shift_pattern = random.choice([
                {"start": 9, "end": 18},   # Regular business hours
                {"start": 6, "end": 15},   # Early shift
                {"start": 14, "end": 23},  # Evening shift
                {"start": 0, "end": 24}    # 24/7 emergency & weekend coverage
            ])
            # 60% standard Mon-Fri, 40% full 7-day weekend support rotation
            days_covered = range(7) if i % 2 == 0 else range(5)
            for day in days_covered:
                db.add(AgentShift(
                    shift_id=f"SHF-{agt_id}-{day}",
                    agent_id=agt_id,
                    day_of_week=day,
                    start_hour=shift_pattern["start"],
                    end_hour=shift_pattern["end"],
                    timezone="Asia/Kolkata"
                ))
                agent_shifts_created += 1

            # 4. Assign Queues (General support + specialized queue if skill present)
            assigned_q = ["Q_GENERAL_SUPPORT"]
            if "PAYMENT_GATEWAY" in assigned_skills:
                assigned_q.append("Q_TIER2_PAYMENTS")
            if "SECURITY_FORENSICS" in assigned_skills:
                assigned_q.append("Q_CRITICAL_INCIDENTS")
            for q_id in set(assigned_q):
                if q_id in queue_ids:
                    db.add(AgentQueue(agent_id=agt_id, queue_id=q_id))
                    agent_queues_created += 1

        db.commit()

        print(f"\nSUCCESS: Generated and Persisted Exactly {agents_created} Simulated Support Agents.")
        print(f"  - Agents in database: {agents_created}")
        print(f"  - Agent Skills mapped: {agent_skills_created}")
        print(f"  - Agent Languages mapped: {agent_langs_created}")
        print(f"  - Agent Shifts mapped: {agent_shifts_created}")
        print(f"  - Agent Queues mapped: {agent_queues_created}")
        return agents_created

    except Exception as e:
        db.rollback()
        print(f"Error generating workforce: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    generate_workforce(target_count=100, seed=20261022)
