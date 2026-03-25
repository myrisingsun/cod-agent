"""Unit tests for Sprint 5: PII filtering."""
import re
from unittest.mock import MagicMock, patch

import pytest

from app.pii.noop_filter import NoopFilter


# ---------------------------------------------------------------------------
# NoopFilter — always available (no presidio dep)
# ---------------------------------------------------------------------------

def test_noop_filter_passthrough():
    f = NoopFilter()
    text = "Иванов Иван Иванович, ИНН 770123456789"
    assert f.filter(text) == text


def test_noop_restore_passthrough():
    f = NoopFilter()
    text = "Залогодатель <PERSON_1>"
    assert f.restore(text) == text


def test_noop_filter_and_restore_roundtrip():
    f = NoopFilter()
    original = "Договор №123 от 01.01.2024"
    assert f.restore(f.filter(original)) == original


# ---------------------------------------------------------------------------
# Factory — switching by settings
# ---------------------------------------------------------------------------

def test_factory_returns_noop_by_default():
    from app.pii.factory import get_pii_filter
    from app.config import Settings

    cfg = Settings(pii_filter="noop")
    filt = get_pii_filter(cfg)
    assert isinstance(filt, NoopFilter)


def test_factory_returns_presidio_when_configured():
    from app.pii.factory import get_pii_filter
    from app.config import Settings

    mock_instance = MagicMock()
    mock_cls = MagicMock(return_value=mock_instance)
    mock_module = MagicMock()
    mock_module.PresidioFilter = mock_cls

    # Patch the module that factory imports from at call time
    with patch.dict("sys.modules", {"app.pii.presidio_filter": mock_module}):
        cfg = Settings(pii_filter="presidio")
        filt = get_pii_filter(cfg)
        assert filt is mock_instance


# ---------------------------------------------------------------------------
# PresidioFilter — mocked to avoid heavy dep in dev image
# ---------------------------------------------------------------------------

class _MockAnalyzerResult:
    def __init__(self, entity_type, start, end):
        self.entity_type = entity_type
        self.start = start
        self.end = end


def _make_presidio_filter_with_mocks():
    """Build a PresidioFilter with mocked Presidio internals."""
    mock_analyzer = MagicMock()
    mock_anonymizer = MagicMock()

    with patch.dict("sys.modules", {
        "presidio_analyzer": MagicMock(),
        "presidio_analyzer.nlp_engine": MagicMock(),
        "presidio_anonymizer": MagicMock(),
        "presidio_anonymizer.entities": MagicMock(),
    }):
        import importlib
        import app.pii.presidio_filter as pf_mod
        importlib.reload(pf_mod)
        filt = pf_mod.PresidioFilter.__new__(pf_mod.PresidioFilter)
        filt._analyzer = mock_analyzer
        filt._anonymizer = mock_anonymizer
        filt._mapping = {}
    return filt, mock_analyzer


def test_presidio_filter_replaces_entity():
    filt, mock_analyzer = _make_presidio_filter_with_mocks()
    text = "Залогодатель Иванов Иван Иванович."
    mock_analyzer.analyze.return_value = [
        _MockAnalyzerResult("PERSON", 13, 33),
    ]
    result = filt.filter(text)
    assert "<PERSON_1>" in result
    assert "Иванов Иван Иванович" not in result


def test_presidio_filter_stores_mapping():
    filt, mock_analyzer = _make_presidio_filter_with_mocks()
    text = "ИНН 770123456789"
    mock_analyzer.analyze.return_value = [
        _MockAnalyzerResult("RU_INN", 4, 16),
    ]
    filt.filter(text)
    assert "<RU_INN_1>" in filt._mapping
    assert filt._mapping["<RU_INN_1>"] == "770123456789"


def test_presidio_restore_replaces_placeholders():
    filt, mock_analyzer = _make_presidio_filter_with_mocks()
    filt._mapping = {
        "<PERSON_1>": "Иванов Иван Иванович",
        "<RU_INN_1>": "770123456789",
    }
    text = "Залогодатель <PERSON_1>, ИНН <RU_INN_1>."
    restored = filt.restore(text)
    assert "Иванов Иван Иванович" in restored
    assert "770123456789" in restored
    assert "<PERSON_1>" not in restored
    assert "<RU_INN_1>" not in restored


def test_presidio_roundtrip():
    filt, mock_analyzer = _make_presidio_filter_with_mocks()
    text = "Залогодатель Петров Пётр Петрович, ИНН 770987654321."
    mock_analyzer.analyze.return_value = [
        _MockAnalyzerResult("PERSON", 13, 33),
        _MockAnalyzerResult("RU_INN", 40, 52),
    ]
    filtered = filt.filter(text)
    restored = filt.restore(filtered)
    assert "Петров Пётр Петрович" in restored
    assert "770987654321" in restored


def test_presidio_multiple_entities_same_type():
    filt, mock_analyzer = _make_presidio_filter_with_mocks()
    text = "Иванов Иван работает с Петровым Петром."
    mock_analyzer.analyze.return_value = [
        _MockAnalyzerResult("PERSON", 0, 11),
        _MockAnalyzerResult("PERSON", 23, 37),
    ]
    result = filt.filter(text)
    assert "<PERSON_1>" in result
    assert "<PERSON_2>" in result
    assert len(filt._mapping) == 2


def test_presidio_no_entities_returns_original():
    filt, mock_analyzer = _make_presidio_filter_with_mocks()
    text = "Договор залога недвижимого имущества."
    mock_analyzer.analyze.return_value = []
    result = filt.filter(text)
    assert result == text


def test_presidio_restore_empty_mapping():
    filt, mock_analyzer = _make_presidio_filter_with_mocks()
    filt._mapping = {}
    text = "Текст без плейсхолдеров"
    assert filt.restore(text) == text
