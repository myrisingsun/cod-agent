import uuid
import pytest
from unittest.mock import AsyncMock, patch
from jose import jwt, JWTError

from app.auth.service import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.config import settings


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

def test_hash_password_produces_different_hashes():
    h1 = hash_password("secret")
    h2 = hash_password("secret")
    assert h1 != h2  # bcrypt random salt


def test_verify_password_correct():
    hashed = hash_password("mypassword")
    assert verify_password("mypassword", hashed) is True


def test_verify_password_wrong():
    hashed = hash_password("mypassword")
    assert verify_password("wrong", hashed) is False


# ---------------------------------------------------------------------------
# JWT tokens
# ---------------------------------------------------------------------------

def test_access_token_payload():
    user_id = str(uuid.uuid4())
    token = create_access_token(user_id, "analyst")
    payload = decode_token(token)
    assert payload["sub"] == user_id
    assert payload["role"] == "analyst"
    assert payload["type"] == "access"


def test_refresh_token_payload():
    user_id = str(uuid.uuid4())
    token = create_refresh_token(user_id)
    payload = decode_token(token)
    assert payload["sub"] == user_id
    assert payload["type"] == "refresh"


def test_decode_token_garbage_raises():
    with pytest.raises(JWTError):
        decode_token("not.a.token")


def test_decode_token_wrong_secret_raises():
    user_id = str(uuid.uuid4())
    token = jwt.encode(
        {"sub": user_id, "type": "access"},
        "wrong-secret",
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(JWTError):
        decode_token(token)


def test_access_token_distinct_from_refresh():
    user_id = str(uuid.uuid4())
    access = create_access_token(user_id, "analyst")
    refresh = create_refresh_token(user_id)
    assert access != refresh


# ---------------------------------------------------------------------------
# Auth endpoints via TestClient + mocked DB layer
# ---------------------------------------------------------------------------

from fastapi.testclient import TestClient
from app.main import app
from app.auth.models import User


def _make_user(email: str = "test@example.com") -> User:
    user = User()
    user.id = uuid.uuid4()
    user.email = email
    user.full_name = "Test User"
    user.role = "analyst"
    user.is_active = True
    user.hashed_password = hash_password("password123")
    return user


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=True)


def test_register_success(client):
    with patch("app.auth.routes.get_user_by_email", new=AsyncMock(return_value=None)), \
         patch("app.auth.routes.create_user", new=AsyncMock(return_value=_make_user())), \
         patch("app.database.get_db", return_value=AsyncMock()):
        resp = client.post("/auth/register", json={
            "email": "new@example.com",
            "password": "password123",
            "full_name": "New User",
        })
    assert resp.status_code == 201
    assert "user_id" in resp.json()


def test_register_duplicate_email(client):
    with patch("app.auth.routes.get_user_by_email", new=AsyncMock(return_value=_make_user())), \
         patch("app.database.get_db", return_value=AsyncMock()):
        resp = client.post("/auth/register", json={
            "email": "test@example.com",
            "password": "password123",
            "full_name": "Test",
        })
    assert resp.status_code == 409


def test_login_success(client):
    user = _make_user()
    with patch("app.auth.routes.authenticate_user", new=AsyncMock(return_value=user)), \
         patch("app.database.get_db", return_value=AsyncMock()):
        resp = client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "password123",
        })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_credentials(client):
    with patch("app.auth.routes.authenticate_user", new=AsyncMock(return_value=None)), \
         patch("app.database.get_db", return_value=AsyncMock()):
        resp = client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "wrong",
        })
    assert resp.status_code == 401


def test_me_no_token_returns_401(client):
    # HTTPBearer raises 401 when Authorization header is absent (FastAPI >=0.135)
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_me_invalid_token_returns_401(client):
    resp = client.get("/auth/me", headers={"Authorization": "Bearer invalidtoken"})
    assert resp.status_code == 401
