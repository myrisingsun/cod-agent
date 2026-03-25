import json
import re
from typing import Any

from app.llm.base import BaseLLMClient
from app.rag.base import BaseRetriever, RetrievedChunk
from app.schemas.document import ParsedDocument
from app.schemas.extraction import ExtractionResult, PledgeFields, FieldConfidence
from app.prompts.extraction import SYSTEM_PROMPT, build_user_prompt

_PLEDGE_FIELDS = list(PledgeFields.model_fields.keys())


def _parse_llm_json(raw: str) -> dict[str, Any]:
    """Extract JSON from LLM response, tolerating markdown code fences."""
    # Strip ```json ... ``` wrappers if present
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if match:
        raw = match.group(1)
    # Find first { ... } block
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1 or end == 0:
        return {}
    return json.loads(raw[start:end])


def _build_result(data: dict[str, Any], raw: str) -> ExtractionResult:
    fields_dict: dict[str, Any] = {}
    confidence_dict: dict[str, float] = {}

    for field in _PLEDGE_FIELDS:
        entry = data.get(field)
        if isinstance(entry, dict):
            value = entry.get("value")
            conf = float(entry.get("confidence", 0.0))
        else:
            value = entry  # fallback: LLM returned flat value
            conf = 0.5 if value is not None else 0.0

        # Coerce area_sqm to float
        if field == "area_sqm" and value is not None:
            try:
                value = float(str(value).replace(",", "."))
            except (ValueError, TypeError):
                value = None
                conf = 0.0

        fields_dict[field] = value
        confidence_dict[field] = round(min(max(conf, 0.0), 1.0), 4)

    return ExtractionResult(
        fields=PledgeFields(**fields_dict),
        confidence=FieldConfidence(**confidence_dict),
        raw_llm_response=raw,
    )


class LLMExtractor:
    def __init__(self, llm_client: BaseLLMClient, retriever: BaseRetriever) -> None:
        self._llm = llm_client
        self._retriever = retriever

    async def extract(self, parsed_doc: ParsedDocument, doc_type: str = "pledge") -> ExtractionResult:
        # Sprint 4: retriever will supply few-shot chunks from reference_templates collection
        # For now, retriever returns [] and we use static few-shot from prompts
        chunks: list[RetrievedChunk] = await self._retriever.retrieve(
            query=parsed_doc.text[:500], collection="reference_templates"
        )

        # Truncate document to avoid exceeding context window (~12k chars ≈ ~3k tokens)
        doc_text = parsed_doc.text[:12_000]
        user_prompt = build_user_prompt(doc_text, few_shot=(len(chunks) == 0))

        raw = await self._llm.complete(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            json_schema={},  # request JSON mode
        )

        try:
            data = _parse_llm_json(raw)
        except (json.JSONDecodeError, ValueError):
            data = {}

        return _build_result(data, raw)
