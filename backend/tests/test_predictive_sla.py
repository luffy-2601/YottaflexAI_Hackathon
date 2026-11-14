import pytest
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from backend.app.core.database import Base, get_db
from backend.app.main import app
from backend.app.models.entities import Ticket, SLAEvent, Customer, Channel, Skill, Intent
from backend.app.services.sla.predictive_model import SLAPredictiveModel

@pytest.fixture(scope="function")
def ml_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSession()

    # Seed 60 synthetic tickets with SLA events for training verification
    db.add_all([
        Channel(channel_id="email", name="Email", default_sla_factor=1.0, is_active=True),
        Channel(channel_id="phone", name="Phone", default_sla_factor=0.2, is_active=True),
        Channel(channel_id="chat", name="Chat", default_sla_factor=0.5, is_active=True),
        Skill(skill_id="PAYMENT_GATEWAY", name="Payment Gateway", tier_level=2),
        Intent(intent_id="PAYMENT_FAILURE", name="Payment Failure", category="BILLING", default_priority="P2", required_skill_id="PAYMENT_GATEWAY"),
        Customer(customer_id="CUS-001", tenant_id="default_tenant", name="Rohan", email="r@test.com", tier="STANDARD"),
        Customer(customer_id="CUS-002", tenant_id="default_tenant", name="Priya", email="p@test.com", tier="ENTERPRISE"),
    ])

    now = datetime.datetime(2026, 11, 10, 10, 0, tzinfo=datetime.timezone.utc)
    for i in range(60):
        t_id = f"TKT-ML-{i:03d}"
        is_breach = True if (i % 4 == 0) else False # 25% breach rate
        priority = "P1" if (i % 4 == 0) else "P3"
        channel = "email" if (i % 4 == 0) else "phone"
        
        t = Ticket(
            ticket_id=t_id,
            tenant_id="default_tenant",
            customer_id="CUS-001" if (i % 2 == 0) else "CUS-002",
            channel_id=channel,
            intent_id="PAYMENT_FAILURE",
            language_code="en",
            subject=f"Issue {i} regarding service",
            status="RESOLVED",
            priority=priority,
            created_at=now - datetime.timedelta(days=i)
        )
        sla = SLAEvent(
            sla_id=f"SLA-ML-{i:03d}",
            ticket_id=t_id,
            first_response_due_at=now,
            resolution_due_at=now,
            is_resolution_breached=is_breach,
            created_at=now - datetime.timedelta(days=i)
        )
        db.add(t)
        db.add(sla)
    db.commit()

    yield db
    db.close()

def test_feature_extraction_no_target_leakage():
    model = SLAPredictiveModel()
    now = datetime.datetime(2026, 11, 14, 21, 30, tzinfo=datetime.timezone.utc) # Saturday night 21:30 (weekend + after hours)
    tkt = Ticket(
        ticket_id="TKT-TEST",
        priority="P1",
        channel_id="email",
        subject="Critical Production Down Outage Payment Gateway",
        created_at=now
    )
    cust = Customer(customer_id="CUS-ENT", tier="ENTERPRISE", email="e@corp.com", name="Corp")

    feats = model.extract_features_from_ticket(tkt, cust, now)

    # 11 features defined
    assert len(feats) == 11
    assert feats[0] == 1.0 # priority P1
    assert feats[1] == 1.0 # is_p1_critical
    assert feats[4] == 1.0 # channel_email
    assert feats[5] == 3.0 # tier_enterprise
    assert feats[6] == 21.0 # hour 21
    assert feats[7] == 1.0 # is_weekend Saturday
    assert feats[8] == 1.0 # is_after_hours (21 >= 18)

def test_model_training_and_evaluation_metrics(ml_session):
    model = SLAPredictiveModel()
    res = model.train_from_database(ml_session, seed=20261022)

    assert res["status"] == "SUCCESS"
    metrics = res["metrics"]
    assert metrics["training_samples"] == 48 # 80% of 60
    assert metrics["testing_samples"] == 12  # 20% of 60
    assert metrics["accuracy"] >= 0.50
    assert "roc_auc" in metrics
    assert "f1_score" in metrics
    assert metrics["model_type"].startswith("Calibrated Logistic Regression")

def test_breach_prediction_sensitivity():
    model = SLAPredictiveModel()
    # Dummy weights for reproducible unit testing
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    import numpy as np

    X_dummy = np.array([
        [1.0, 1.0, 0, 0, 1, 1.0, 22.0, 1.0, 1.0, 100.0, 400.0], # high risk
        [4.0, 0.0, 1, 0, 0, 1.0, 11.0, 0.0, 0.0, 10.0, 50.0],   # low risk
    ])
    y_dummy = np.array([1, 0])
    scaler = StandardScaler().fit(X_dummy)
    clf = LogisticRegression().fit(scaler.transform(X_dummy), y_dummy)

    model.model = clf
    model.scaler = scaler

    high_risk_tkt = Ticket(
        ticket_id="TKT-HIGH",
        priority="P1",
        channel_id="email",
        subject="Critical Outage Emergency Immediate Assistance Needed",
        created_at=datetime.datetime(2026, 11, 14, 22, 0, tzinfo=datetime.timezone.utc)
    )
    low_risk_tkt = Ticket(
        ticket_id="TKT-LOW",
        priority="P4",
        channel_id="phone",
        subject="Quick call question",
        created_at=datetime.datetime(2026, 11, 10, 11, 0, tzinfo=datetime.timezone.utc)
    )

    pred_high = model.predict_breach_probability(high_risk_tkt)
    pred_low = model.predict_breach_probability(low_risk_tkt)

    assert pred_high["breach_probability"] > pred_low["breach_probability"]
    assert "Critical Priority P1 workload" in pred_high["top_risk_factors"]
