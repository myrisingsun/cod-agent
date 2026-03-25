"""Unit tests for extraction module and API endpoints."""
import uuid
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.extraction.llm_extractor import LLMExtractor, _parse_llm_json, _build_result
from app.schemas.extraction import PledgeFields, FieldConfidence, ExtractionResult
from app.schemas.document import ParsedDocument


# ---------------------------------------------------------------------------
# _parse_llm_json
# ---------------------------------------------------------------------------

def test_parse_llm_json_clean():
    raw = '{"contract_number": {"value": "123", "confidence": 0.9}}'
    data = _parse_llm_json(raw)
    assert data["contract_number"]["value"] == "123"


def test_parse_llm_json_with_markdown_fence():
    raw = '```json\n{"contract_number": {"value": "456", "confidence": 0.8}}\n```'
    data = _parse_llm_json(raw)
    assert data["contract_number"]["value"] == "456"


def test_parse_llm_json_returns_empty_on_garbage():
    data = _parse_llm_json("не JSON текст")
    assert data == {}


def test_parse_llm_json_extracts_inner_json():
    raw = 'Вот результат:\n{"key": {"value": "v", "confidence": 1.0}}\nConclusion.'
    data = _parse_llm_json(raw)
    assert data["key"]["value"] == "v"


# ---------------------------------------------------------------------------
# _build_result
# ---------------------------------------------------------------------------

def test_build_result_full_response():
    data = {
        "contract_number": {"value": "2024/001", "confidence": 1.0},
        "contract_date": {"value": "15.01.2024", "confidence": 0.95},
        "pledgee": {"value": "ПАО Банк", "confidence": 1.0},
        "pledgor": {"value": "Иванов И.И.", "confidence": 1.0},
        "pledgor_inn": {"value": "770123456789", "confidence": 0.9},
        "pledge_subject": {"value": "квартира", "confidence": 0.8},
        "cadastral_number": {"value": "77:01:0001:1", "confidence": 0.95},
        "area_sqm": {"value": 62.4, "confidence": 1.0},
        "pledge_value": {"value": "8 500 000 руб.", "confidence": 1.0},
        "validity_period": {"value": "до 2029 года", "confidence": 0.85},
    }
    result = _build_result(data, "raw")
    assert result.fields.contract_number == "2024/001"
    assert result.fields.area_sqm == 62.4
    assert result.confidence.pledgee == 1.0
    assert result.confidence.area_sqm == 1.0


def test_build_result_null_fields():
    data = {f: {"value": None, "confidence": 0.0} for f in PledgeFields.model_fields}
    result = _build_result(data, "raw")
    assert result.fields.contract_number is None
    assert result.confidence.contract_number == 0.0


def test_build_result_area_sqm_string_coercion():
    data = {f: {"value": None, "confidence": 0.0} for f in PledgeFields.model_fields}
    data["area_sqm"] = {"value": "62,4", "confidence": 0.9}
    result = _build_result(data, "raw")
    assert result.fields.area_sqm == 62.4


def test_build_result_confidence_clamped():
    data = {f: {"value": "x", "confidence": 1.5} for f in PledgeFields.model_fields}
    data["area_sqm"] = {"value": 10.0, "confidence": 1.5}
    result = _build_result(data, "raw")
    assert result.confidence.contract_number == 1.0


def test_build_result_flat_value_fallback():
    """LLM returned flat values instead of {value, confidence} dicts."""
    data = {"contract_number": "2024/XYZ"}
    result = _build_result(data, "raw")
    assert result.fields.contract_number == "2024/XYZ"
    assert result.confidence.contract_number == 0.5


# ---------------------------------------------------------------------------
# LLMExtractor.extract (async)
# ---------------------------------------------------------------------------

async def test_llm_extractor_calls_llm_and_returns_result():
    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(return_value=json.dumps({
        "contract_number": {"value": "TEST-001", "confidence": 0.99},
        "contract_date": {"value": "01.01.2024", "confidence": 0.9},
        "pledgee": {"value": None, "confidence": 0.0},
        "pledgor": {"value": None, "confidence": 0.0},
        "pledgor_inn": {"value": None, "confidence": 0.0},
        "pledge_subject": {"value": None, "confidence": 0.0},
        "cadastral_number": {"value": None, "confidence": 0.0},
        "area_sqm": {"value": None, "confidence": 0.0},
        "pledge_value": {"value": None, "confidence": 0.0},
        "validity_period": {"value": None, "confidence": 0.0},
    }))
    mock_retriever = AsyncMock()
    mock_retriever.retrieve = AsyncMock(return_value=[])

    extractor = LLMExtractor(llm_client=mock_llm, retriever=mock_retriever)
    parsed = ParsedDocument(text="Договор №TEST-001 от 01.01.2024", pages=1, filename="t.pdf")

    result = await extractor.extract(parsed)

    assert result.fields.contract_number == "TEST-001"
    assert result.confidence.contract_number == 0.99
    mock_llm.complete.assert_called_once()


async def test_llm_extractor_handles_bad_llm_response():
    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(return_value="Ошибка: не могу обработать")
    mock_retriever = AsyncMock()
    mock_retriever.retrieve = AsyncMock(return_value=[])

    extractor = LLMExtractor(llm_client=mock_llm, retriever=mock_retriever)
    parsed = ParsedDocument(text="some text", pages=1, filename="t.pdf")

    result = await extractor.extract(parsed)
    # Should return all nulls, not raise
    assert result.fields.contract_number is None
    assert isinstance(result, ExtractionResult)


# ---------------------------------------------------------------------------
# Extraction API endpoints
# ---------------------------------------------------------------------------

from fastapi.testclient import TestClient
from app.main import app
from app.auth.dependencies import get_current_user
from app.database import get_db
from app.auth.models import User
from app.auth.service import hash_password
from app.models.package import Package
from app.models.extraction_result import ExtractionResult as ExtractionResultModel


def _make_user() -> User:
    user = User()
    user.id = uuid.uuid4()
    user.email = "a@b.com"
    user.full_name = "A"
    user.role = "analyst"
    user.is_active = True
    user.hashed_password = hash_password("x")
    return user


def _make_package(user_id: uuid.UUID, status: str = "done") -> Package:
    pkg = Package()
    pkg.id = uuid.uuid4()
    pkg.filename = "doc.pdf"
    pkg.status = status
    pkg.user_id = user_id
    pkg.accuracy = 0.92
    pkg.document_type = None
    pkg.created_at = datetime.now(timezone.utc)
    pkg.updated_at = None
    return pkg


def _make_db_extraction(package_id: uuid.UUID) -> ExtractionResultModel:
    er = ExtractionResultModel()
    er.id = uuid.uuid4()
    er.package_id = package_id
    er.fields = {f: None for f in PledgeFields.model_fields}
    er.fields["contract_number"] = "2024/001"
    er.confidence = {f: 0.0 for f in FieldConfidence.model_fields}
    er.confidence["contract_number"] = 0.95
    er.raw_llm_response = "{}"
    er.created_at = datetime.now(timezone.utc)
    er.updated_at = None
    return er


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


def test_get_extraction_success(client):
    user = _make_user()
    pkg = _make_package(user.id)
    extraction = _make_db_extraction(pkg.id)

    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=pkg)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = extraction
    mock_db.execute = AsyncMock(return_value=mock_result)

    async def override_db():
        yield mock_db

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = override_db

    try:
        resp = client.get(f"/packages/{pkg.id}/extraction")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    data = resp.json()
    assert data["fields"]["contract_number"] == "2024/001"
    assert data["confidence"]["contract_number"] == 0.95


def test_get_extraction_not_found_package(client):
    user = _make_user()
    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=None)

    async def override_db():
        yield mock_db

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = override_db

    try:
        resp = client.get(f"/packages/{uuid.uuid4()}/extraction")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 404


def test_get_extraction_no_result_yet(client):
    user = _make_user()
    pkg = _make_package(user.id, status="processing")
    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=pkg)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    async def override_db():
        yield mock_db

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = override_db

    try:
        resp = client.get(f"/packages/{pkg.id}/extraction")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 404


def test_retry_extraction_accepted(client):
    user = _make_user()
    pkg = _make_package(user.id, status="error")
    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=pkg)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.commit = AsyncMock()

    async def override_db():
        yield mock_db

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = override_db

    try:
        with patch("app.api.routes_extraction.process_package", new=AsyncMock()):
            resp = client.post(f"/packages/{pkg.id}/extraction/retry")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 202
    assert resp.json()["status"] == "accepted"


def test_retry_extraction_conflict_when_processing(client):
    user = _make_user()
    pkg = _make_package(user.id, status="processing")
    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=pkg)

    async def override_db():
        yield mock_db

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = override_db

    try:
        resp = client.post(f"/packages/{pkg.id}/extraction/retry")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 409
