from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional
from enum import Enum


class PackageStatus(str, Enum):
    RECEIVED = "received"
    PROCESSING = "processing"
    DONE = "done"
    ERROR = "error"


class PackageCreate(BaseModel):
    filename: str


class PackageResponse(BaseModel):
    id: UUID
    filename: str
    status: PackageStatus
    document_type: Optional[str] = None
    accuracy: Optional[float] = None
    user_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
