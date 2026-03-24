"""Unit tests for packages API endpoints."""
import io
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.auth.dependencies import get_current_user
from app.database import get_db
from app.auth.models import User
from app.auth.service import hash_password
from app.models.package import Package


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user() -> User:
    user = User()
    user.id = uuid.uuid4()
    user.email = "analyst@example.com"
    user.full_name = "Analyst"
    user.role = "analyst"
    user.is_active = True
    user.hashed_password = hash_password("pass")
    return user


def _make_package(user_id: uuid.UUID, filename: str = "doc.pdf") -> Package:
    pkg = Package()
    pkg.id = uuid.uuid4()
    pkg.filename = filename
    pkg.status = "received"
    pkg.user_id = user_id
    pkg.document_type = None
    pkg.accuracy = None
    pkg.created_at = datetime.now(timezone.utc)
    pkg.updated_at = None
    return pkg


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# POST /packages — upload
# ---------------------------------------------------------------------------

def test_upload_package_success(client):
    from unittest.mock import patch

    user = _make_user()
    pkg = _make_package(user.id)

    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    mock_storage = AsyncMock()
    mock_storage.save_file = AsyncMock(return_value=f"{pkg.id}/doc.pdf")

    async def override_db():
        yield mock_db

    def override_user():
        return user

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db

    try:
        with patch("app.api.routes_packages.get_storage", return_value=mock_storage), \
             patch("app.api.routes_packages.Package", return_value=pkg), \
             patch("app.api.routes_packages.process_package", new=AsyncMock()):
            resp = client.post(
                "/packages",
                files={"file": ("doc.pdf", io.BytesIO(b"%PDF-1.4 content"), "application/pdf")},
            )
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 201
    data = resp.json()
    assert data["filename"] == "doc.pdf"
    assert data["status"] == "received"


def test_upload_non_pdf_rejected(client):
    user = _make_user()
    mock_db = AsyncMock()

    async def override_db():
        yield mock_db

    def override_user():
        return user

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db

    try:
        resp = client.post(
            "/packages",
            files={"file": ("doc.txt", io.BytesIO(b"text content"), "text/plain")},
        )
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 400


def test_upload_no_token_returns_401(client):
    resp = client.post(
        "/packages",
        files={"file": ("doc.pdf", io.BytesIO(b"%PDF content"), "application/pdf")},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /packages
# ---------------------------------------------------------------------------

def test_list_packages_returns_user_packages(client):
    user = _make_user()
    pkgs = [_make_package(user.id, f"doc{i}.pdf") for i in range(3)]

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = pkgs
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    async def override_db():
        yield mock_db

    def override_user():
        return user

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db

    try:
        resp = client.get("/packages")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert len(resp.json()) == 3


# ---------------------------------------------------------------------------
# GET /packages/{id}
# ---------------------------------------------------------------------------

def test_get_package_found(client):
    user = _make_user()
    pkg = _make_package(user.id)

    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=pkg)

    async def override_db():
        yield mock_db

    def override_user():
        return user

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db

    try:
        resp = client.get(f"/packages/{pkg.id}")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json()["id"] == str(pkg.id)


def test_get_package_not_found(client):
    user = _make_user()
    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=None)

    async def override_db():
        yield mock_db

    def override_user():
        return user

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db

    try:
        resp = client.get(f"/packages/{uuid.uuid4()}")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 404


def test_get_package_belonging_to_another_user_returns_404(client):
    user = _make_user()
    other_pkg = _make_package(uuid.uuid4())  # different user_id

    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=other_pkg)

    async def override_db():
        yield mock_db

    def override_user():
        return user

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db

    try:
        resp = client.get(f"/packages/{other_pkg.id}")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /packages/{id}
# ---------------------------------------------------------------------------

def test_delete_package_success(client):
    from unittest.mock import patch

    user = _make_user()
    pkg = _make_package(user.id)

    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=pkg)
    mock_db.delete = AsyncMock()
    mock_db.commit = AsyncMock()

    mock_storage = AsyncMock()
    mock_storage.delete_file = AsyncMock()

    async def override_db():
        yield mock_db

    def override_user():
        return user

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db

    try:
        with patch("app.api.routes_packages.get_storage", return_value=mock_storage):
            resp = client.delete(f"/packages/{pkg.id}")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 204


def test_delete_package_not_found(client):
    user = _make_user()
    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=None)

    async def override_db():
        yield mock_db

    def override_user():
        return user

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db

    try:
        resp = client.delete(f"/packages/{uuid.uuid4()}")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 404
