from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class RawItem(BaseModel):
    raw_id: str
    data: dict


class RawRunMeta(BaseModel):
    connector: str
    job: str
    cursor_start: Optional[str] = None
    cursor_end: Optional[str] = None
    items_fetched: int = 0
    started_at: datetime = Field(default_factory=datetime.now)
