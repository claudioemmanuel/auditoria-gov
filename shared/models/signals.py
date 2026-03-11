import uuid
from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


class SignalSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CompletenessStatus(str, Enum):
    SUFFICIENT = "sufficient"
    INSUFFICIENT = "insufficient"


class RefType(str, Enum):
    RAW_SOURCE = "raw_source"
    EVENT = "event"
    ENTITY = "entity"
    BASELINE = "baseline"
    EXTERNAL_URL = "external_url"


class EvidenceRef(BaseModel):
    ref_type: RefType
    ref_id: Optional[str] = None
    url: Optional[str] = None
    source_hash: Optional[str] = None
    captured_at: Optional[datetime] = None
    snapshot_uri: Optional[str] = None
    description: str


_SIGNAL_DISCLAIMER = (
    "Este resultado representa um indicador estatístico para triagem e controle social. "
    "Não configura acusação, prova definitiva ou juízo de culpa. "
    "A verificação adicional por autoridade competente é necessária antes de qualquer conclusão."
)


class RiskSignalOut(BaseModel):
    id: uuid.UUID
    typology_code: str
    typology_name: str
    severity: SignalSeverity
    confidence: float = Field(ge=0.0, le=1.0)
    title: str
    summary: Optional[str] = None
    explanation_md: Optional[str] = None
    completeness_score: float = Field(default=0.0, ge=0.0, le=1.0)
    completeness_status: CompletenessStatus = CompletenessStatus.INSUFFICIENT
    evidence_package_id: Optional[uuid.UUID] = None
    factors: dict = Field(default_factory=dict)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    entity_ids: list[uuid.UUID] = Field(default_factory=list)
    event_ids: list[uuid.UUID] = Field(default_factory=list)
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    created_at: datetime
    disclaimer: Literal[
        "Este resultado representa um indicador estatístico para triagem e controle social. "
        "Não configura acusação, prova definitiva ou juízo de culpa. "
        "A verificação adicional por autoridade competente é necessária antes de qualquer conclusão."
    ] = Field(default=_SIGNAL_DISCLAIMER, description="Aviso obrigatório: este sinal é hipótese estatística, não acusação.")


class EvidencePackageOut(BaseModel):
    id: uuid.UUID
    source_url: Optional[str] = None
    source_hash: Optional[str] = None
    captured_at: Optional[datetime] = None
    parser_version: Optional[str] = None
    model_version: Optional[str] = None
    raw_snapshot_uri: Optional[str] = None
    normalized_snapshot_uri: Optional[str] = None
    signature: Optional[str] = None


class SignalReplayOut(BaseModel):
    signal_id: uuid.UUID
    replay_hash: str
    stored_signature: Optional[str] = None
    deterministic_match: bool
    checked_at: datetime


class CaseEntityBrief(BaseModel):
    id: uuid.UUID
    name: str
    type: str          # "person" | "company" | "org"
    cnpj_masked: Optional[str] = None
    roles: list[str] = Field(default_factory=list)
    signal_ids: list[uuid.UUID] = Field(default_factory=list)


class ContestationCreate(BaseModel):
    signal_id: Optional[uuid.UUID] = None
    requester_name: str = Field(min_length=2, max_length=255)
    requester_email: Optional[str] = Field(default=None, max_length=255)
    reason: str = Field(min_length=8, max_length=5000)
    details: dict = Field(default_factory=dict, max_length=50)


class ContestationOut(BaseModel):
    id: uuid.UUID
    signal_id: Optional[uuid.UUID] = None
    status: str
    requester_name: str
    requester_email: Optional[str] = None
    reason: str
    details: dict = Field(default_factory=dict)
    resolution: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
