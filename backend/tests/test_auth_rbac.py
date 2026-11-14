import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.app.core.database import Base, get_db
from backend.app.main import app
from backend.app.models.entities import User
from backend.app.core.security import hash_password, verify_password, create_access_token, decode_access_token
from backend.app.core.auth_middleware import verify_tenant_access

@pytest.fixture(scope="function")
def auth_client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

def test_password_hashing_and_verification():
    raw_pwd = "EnterpriseSecretPassword123!"
    hashed = hash_password(raw_pwd)
    assert hashed.startswith("pbkdf2_sha256$")
    assert verify_password(raw_pwd, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False

def test_jwt_token_creation_and_decoding():
    payload = {"sub": "USR-12345", "role": "ADMIN", "tenant_id": "tenant_alpha"}
    token = create_access_token(payload)
    decoded = decode_access_token(token)
    assert decoded["sub"] == "USR-12345"
    assert decoded["role"] == "ADMIN"
    assert decoded["tenant_id"] == "tenant_alpha"

def test_user_registration_and_login_flow(auth_client):
    # 1. Register new agent
    reg_payload = {
        "email": "agent.smith@matrix.com",
        "password": "CorrectHorseBatteryStaple123",
        "role": "AGENT",
        "tenant_id": "tenant_matrix"
    }
    reg_resp = auth_client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_resp.status_code == 201
    user_data = reg_resp.json()
    assert user_data["email"] == "agent.smith@matrix.com"
    assert user_data["role"] == "AGENT"
    assert user_data["tenant_id"] == "tenant_matrix"

    # 2. Login with correct password
    login_resp = auth_client.post("/api/v1/auth/login", json={
        "email": "agent.smith@matrix.com",
        "password": "CorrectHorseBatteryStaple123"
    })
    assert login_resp.status_code == 200
    token_data = login_resp.json()
    assert "access_token" in token_data
    token = token_data["access_token"]

    # 3. Login with wrong password -> 401 Unauthorized
    bad_login = auth_client.post("/api/v1/auth/login", json={
        "email": "agent.smith@matrix.com",
        "password": "WrongPassword!"
    })
    assert bad_login.status_code == 401

    # 4. Access protected /auth/me with Bearer token
    me_resp = auth_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "agent.smith@matrix.com"

    # 5. Access protected /auth/me WITHOUT token -> 401 Unauthorized
    unauth_resp = auth_client.get("/api/v1/auth/me")
    assert unauth_resp.status_code == 401

def test_role_based_access_control(auth_client):
    # Register an AGENT
    auth_client.post("/api/v1/auth/register", json={
        "email": "agent@test.com", "password": "Password123!", "role": "AGENT"
    })
    agent_token = auth_client.post("/api/v1/auth/login", json={
        "email": "agent@test.com", "password": "Password123!"
    }).json()["access_token"]

    # Register an ADMIN
    auth_client.post("/api/v1/auth/register", json={
        "email": "admin@test.com", "password": "Password123!", "role": "ADMIN"
    })
    admin_token = auth_client.post("/api/v1/auth/login", json={
        "email": "admin@test.com", "password": "Password123!"
    }).json()["access_token"]

    # AGENT attempting admin-only endpoint -> 403 Forbidden!
    forbidden_resp = auth_client.get(
        "/api/v1/auth/admin-only",
        headers={"Authorization": f"Bearer {agent_token}"}
    )
    assert forbidden_resp.status_code == 403

    # ADMIN attempting admin-only endpoint -> 200 OK!
    allowed_resp = auth_client.get(
        "/api/v1/auth/admin-only",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert allowed_resp.status_code == 200
    assert allowed_resp.json()["status"] == "AUTHORIZED"

def test_cross_tenant_isolation_enforcement():
    agent_user = User(user_id="U1", email="a@t1.com", role="AGENT", tenant_id="tenant_one")
    admin_user = User(user_id="U2", email="adm@root.com", role="ADMIN", tenant_id="tenant_master")

    # Same tenant access -> OK
    verify_tenant_access("tenant_one", agent_user)

    # Cross-tenant access by standard agent -> Must raise 403 Forbidden!
    with pytest.raises(HTTPException) as exc:
        verify_tenant_access("tenant_two", agent_user)
    assert exc.value.status_code == 403

    # Cross-tenant access by ADMIN -> Allowed
    verify_tenant_access("tenant_two", admin_user)
