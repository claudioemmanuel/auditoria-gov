import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import Base


class Contestation(Base):
    """Public-facing error report / challenge submitted for a signal or entity."""

    __tablename__ = "contestation"

    signal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("risk_signal.id")
    )
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entity.id")
    )
    report_type: Mapped[str] = mapped_column(String(50), default="signal_error")
    evidence_url: Mapped[str | None] = mapped_column(String(2048))
    status: Mapped[str] = mapped_column(String(20), default="open")
    requester_name: Mapped[str] = mapped_column(String(255))
    requester_email: Mapped[str | None] = mapped_column(String(255))
    reason: Mapped[str] = mapped_column(Text)
    details: Mapped[dict] = mapped_column(JSONB, default=dict)
    resolution: Mapped[str | None] = mapped_column(Text)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            "signal_id IS NOT NULL OR entity_id IS NOT NULL",
            name="ck_contestation_has_target",
        ),
        CheckConstraint(
            "report_type IN ('signal_error','entity_error','duplicate','other')",
            name="ck_contestation_report_type",
        ),
        Index("ix_contestation_signal_status", "signal_id", "status"),
        Index("ix_contestation_entity_status", "entity_id", "status"),
        Index("ix_contestation_created_at", "created_at"),
    )
