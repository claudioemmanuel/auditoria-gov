"""
Public Response Filter — Data Protection Layer (Phase 6)

Ensures that API responses served to the public never contain:
- Raw enriched dataset fields
- Internal scoring weights or typology factor details
- Proprietary aggregations or heuristic metadata
- Internal entity identifiers beyond what is needed

All public endpoints must pass their output through these filters.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Approved public output schemas — ONLY these fields may be returned
# ---------------------------------------------------------------------------

class PublicSignalSummary(BaseModel):
    """Filtered signal for public radar view. No weights, no factor details."""
    id: uuid.UUID
    typology_code: str
    typology_name: str
    severity: str
    title: str
    summary: Optional[str] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    created_at: datetime
    disclaimer: str


class PublicEntitySummary(BaseModel):
    """Filtered entity for public search. No internal cluster IDs."""
    id: uuid.UUID
    name: str
    type: str
    signal_count: int = 0
    max_severity: Optional[str] = None


class PublicCaseSummary(BaseModel):
    """Filtered case summary. No internal scores or weights."""
    id: uuid.UUID
    title: str
    severity: str
    signal_count: int
    entity_count: int
    created_at: datetime
    updated_at: datetime


class PublicSourceInfo(BaseModel):
    """Source veracity entry — no internal weighting details."""
    connector_id: str
    label: str
    veracity_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    last_ingested_at: Optional[datetime] = None
    is_active: bool


# ---------------------------------------------------------------------------
# Field-level strip helpers
# ---------------------------------------------------------------------------

_SIGNAL_INTERNAL_FIELDS = frozenset({
    "factors",
    "evidence_refs",
    "completeness_score",
    "completeness_status",
    "evidence_package_id",
    "event_ids",
    "entity_ids",
    "explanation_md",
})

_ENTITY_INTERNAL_FIELDS = frozenset({
    "cluster_id",
    "cpf_hash",
    "source_ids",
    "raw_source_ids",
    "embedding_id",
})


def strip_signal_internals(signal_dict: dict[str, Any]) -> dict[str, Any]:
    """Remove internal fields from a serialized RiskSignalOut dict."""
    return {k: v for k, v in signal_dict.items() if k not in _SIGNAL_INTERNAL_FIELDS}


def strip_entity_internals(entity_dict: dict[str, Any]) -> dict[str, Any]:
    """Remove internal fields from a serialized canonical entity dict."""
    return {k: v for k, v in entity_dict.items() if k not in _ENTITY_INTERNAL_FIELDS}


def to_public_signal(signal_dict: dict[str, Any]) -> PublicSignalSummary:
    """Convert an internal signal dict to the approved public schema."""
    clean = strip_signal_internals(signal_dict)
    return PublicSignalSummary(**{
        k: clean[k] for k in PublicSignalSummary.model_fields if k in clean
    })


def to_public_entity(entity_dict: dict[str, Any]) -> PublicEntitySummary:
    """Convert an internal entity dict to the approved public schema."""
    clean = strip_entity_internals(entity_dict)
    return PublicEntitySummary(**{
        k: clean[k] for k in PublicEntitySummary.model_fields if k in clean
    })
