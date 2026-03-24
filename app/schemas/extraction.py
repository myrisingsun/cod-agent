from pydantic import BaseModel, Field
from typing import Optional


class PledgeFields(BaseModel):
    """10 fields extracted from a pledge contract."""
    contract_number: Optional[str] = None
    contract_date: Optional[str] = None
    pledgee: Optional[str] = None
    pledgor: Optional[str] = None
    pledgor_inn: Optional[str] = None
    pledge_subject: Optional[str] = None
    cadastral_number: Optional[str] = None
    area_sqm: Optional[float] = None
    pledge_value: Optional[str] = None
    validity_period: Optional[str] = None


class FieldConfidence(BaseModel):
    """Confidence score for each field."""
    contract_number: float = 0.0
    contract_date: float = 0.0
    pledgee: float = 0.0
    pledgor: float = 0.0
    pledgor_inn: float = 0.0
    pledge_subject: float = 0.0
    cadastral_number: float = 0.0
    area_sqm: float = 0.0
    pledge_value: float = 0.0
    validity_period: float = 0.0


class ExtractionResult(BaseModel):
    """Combined extraction output."""
    fields: PledgeFields
    confidence: FieldConfidence
    raw_llm_response: str = ""
