import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CanonicalEntity(BaseModel):
    source_connector: str
    source_id: str
    type: str  # person, company, org
    name: str
    identifiers: dict = Field(default_factory=dict)
    attrs: dict = Field(default_factory=dict)


class CanonicalEventParticipant(BaseModel):
    entity_ref: CanonicalEntity
    role: str
    attrs: dict = Field(default_factory=dict)


class CanonicalEvent(BaseModel):
    source_connector: str
    source_id: str
    type: str
    subtype: Optional[str] = None
    description: Optional[str] = None
    occurred_at: Optional[datetime] = None
    value_brl: Optional[float] = None
    attrs: dict = Field(default_factory=dict)
    participants: list[CanonicalEventParticipant] = Field(default_factory=list)


class CanonicalEdge(BaseModel):
    from_entity_ref: CanonicalEntity
    to_entity_ref: CanonicalEntity
    type: str
    weight: float = 1.0
    attrs: dict = Field(default_factory=dict)


class NormalizeResult(BaseModel):
    entities: list[CanonicalEntity] = Field(default_factory=list)
    events: list[CanonicalEvent] = Field(default_factory=list)
    edges: list[CanonicalEdge] = Field(default_factory=list)
