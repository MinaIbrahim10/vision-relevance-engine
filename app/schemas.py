from typing import Literal

from pydantic import BaseModel, Field


class VisionMetadata(BaseModel):
    subject: str = Field(min_length=1, max_length=255)
    category: str = Field(min_length=1, max_length=100)
    attributes: list[str] = Field(default_factory=list)
    caption: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)


class ImageCreate(BaseModel):
    filename: str = Field(min_length=1)
    path: str = Field(min_length=1)


class PostCreate(BaseModel):
    title: str = Field(min_length=1)
    body: str = Field(min_length=1)
    expected_subject: str | None = None
    expected_category: str | None = None


class ReviewCreate(BaseModel):
    suggestion_id: int
    decision: Literal["approve", "reject"]
    notes: str | None = None


class MatchResult(BaseModel):
    post_id: int
    image_id: int | None
    similarity: float
    accepted: bool
    reason: str
