from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class VideoIngestError(RuntimeError):
    """Raised when a video cannot be ingested into a raw session."""


class VideoSidecar(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1)
    fps: float = Field(gt=0)
