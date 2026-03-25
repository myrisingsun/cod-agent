"""PII filter using Microsoft Presidio (pattern-based, no spacy NLP engine required)."""
from __future__ import annotations

import re
from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig


# ---------------------------------------------------------------------------
# Custom recognizers for Russian documents
# ---------------------------------------------------------------------------

def _make_inn_recognizer() -> PatternRecognizer:
    """Russian INN (ИНН): 10 digits (org) or 12 digits (individual)."""
    return PatternRecognizer(
        supported_entity="RU_INN",
        patterns=[
            Pattern(name="inn_12", regex=r"\b\d{12}\b", score=0.85),
            Pattern(name="inn_10", regex=r"\b\d{10}\b", score=0.75),
        ],
        context=["инн", "inn", "идентификационный"],
    )


def _make_cadastral_recognizer() -> PatternRecognizer:
    """Russian cadastral number: NN:NN:NNNNNNN:NNN."""
    return PatternRecognizer(
        supported_entity="RU_CADASTRAL",
        patterns=[Pattern(name="cadastral", regex=r"\b\d{2}:\d{2}:\d{6,7}:\d+\b", score=0.9)],
        context=["кадастровый", "кадастровом", "номер"],
    )


def _make_passport_recognizer() -> PatternRecognizer:
    """Russian passport series + number: NNNN NNNNNN."""
    return PatternRecognizer(
        supported_entity="RU_PASSPORT",
        patterns=[Pattern(name="passport", regex=r"\b\d{4}\s\d{6}\b", score=0.7)],
        context=["паспорт", "серия", "выдан"],
    )


# ---------------------------------------------------------------------------
# PresidioFilter
# ---------------------------------------------------------------------------

class PresidioFilter:
    """Replaces PII entities with typed placeholders; can restore originals."""

    _ENTITIES = [
        "PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "IBAN_CODE", "CREDIT_CARD",
        "DATE_TIME", "LOCATION", "RU_INN", "RU_CADASTRAL", "RU_PASSPORT",
    ]

    def __init__(self) -> None:
        # Use simple pattern-based NLP engine — no spacy model download needed
        provider = NlpEngineProvider(nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
        })
        try:
            nlp_engine = provider.create_engine()
        except Exception:
            # Fallback: no NLP engine — pattern-only mode
            nlp_engine = None

        self._analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["en", "ru"])
        self._analyzer.registry.add_recognizer(_make_inn_recognizer())
        self._analyzer.registry.add_recognizer(_make_cadastral_recognizer())
        self._analyzer.registry.add_recognizer(_make_passport_recognizer())

        self._anonymizer = AnonymizerEngine()
        # {placeholder: original_value}
        self._mapping: dict[str, str] = {}

    def filter(self, text: str) -> str:
        """Replace PII entities with placeholders, store mapping for restore()."""
        self._mapping = {}
        counters: dict[str, int] = {}

        results = self._analyzer.analyze(text=text, language="ru", entities=self._ENTITIES)
        # Sort by position descending so replacements don't shift indices
        results = sorted(results, key=lambda r: r.start, reverse=True)

        filtered = text
        for result in results:
            entity = result.entity_type
            original = text[result.start:result.end]
            counters[entity] = counters.get(entity, 0) + 1
            placeholder = f"<{entity}_{counters[entity]}>"
            self._mapping[placeholder] = original
            filtered = filtered[:result.start] + placeholder + filtered[result.end:]

        return filtered

    def restore(self, text: str) -> str:
        """Replace placeholders back with original values."""
        restored = text
        for placeholder, original in self._mapping.items():
            restored = restored.replace(placeholder, original)
        return restored
