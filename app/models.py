from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utc_now():
    return datetime.now(timezone.utc)


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255))

    api_key_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )


class ImageAsset(Base):
    __tablename__ = "images"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "filename",
            name="uq_image_tenant_filename",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id"),
        index=True,
    )

    filename: Mapped[str] = mapped_column(
        String(255),
        index=True,
    )
    path: Mapped[str] = mapped_column(String(500))

    subject: Mapped[str | None] = mapped_column(
        String(255),
        index=True,
    )
    category: Mapped[str | None] = mapped_column(
        String(100),
        index=True,
    )

    attributes_json: Mapped[str | None] = mapped_column(Text)
    caption: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Float)

    embedding_json: Mapped[str | None] = mapped_column(Text)

    alt_text: Mapped[str | None] = mapped_column(Text)

    perceptual_hash: Mapped[str | None] = mapped_column(
        String(128),
        index=True,
    )

    needs_review: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )
    processed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id"),
        index=True,
    )

    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)

    expected_subject: Mapped[str | None] = mapped_column(String(255))
    expected_category: Mapped[str | None] = mapped_column(String(100))

    embedding_json: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )


class Suggestion(Base):
    __tablename__ = "suggestions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id"),
        index=True,
    )

    post_id: Mapped[int] = mapped_column(
        ForeignKey("posts.id"),
        index=True,
    )

    image_id: Mapped[int | None] = mapped_column(
        ForeignKey("images.id"),
        nullable=True,
        index=True,
    )

    similarity: Mapped[float] = mapped_column(
        Float,
        default=0.0,
    )

    accepted_by_guard: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    reason: Mapped[str] = mapped_column(Text)

    human_decision: Mapped[str | None] = mapped_column(
        String(32)
    )
    human_notes: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )


class BackgroundJob(Base):
    __tablename__ = "background_jobs"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "idempotency_key",
            name="uq_job_tenant_idempotency",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id"),
        index=True,
    )

    kind: Mapped[str] = mapped_column(String(100))

    idempotency_key: Mapped[str] = mapped_column(
        String(255),
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        index=True,
    )

    attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    max_attempts: Mapped[int] = mapped_column(
        Integer,
        default=3,
    )

    total_items: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    completed_items: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    error: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )


class JobAlert(Base):
    __tablename__ = "job_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id"),
        index=True,
    )

    job_id: Mapped[int] = mapped_column(
        ForeignKey("background_jobs.id"),
        index=True,
    )

    level: Mapped[str] = mapped_column(String(32))
    message: Mapped[str] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )


class AIUsage(Base):
    __tablename__ = "ai_usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    tenant_id: Mapped[int | None] = mapped_column(
        ForeignKey("tenants.id"),
        nullable=True,
        index=True,
    )

    operation: Mapped[str] = mapped_column(
        String(100),
        index=True,
    )

    provider: Mapped[str] = mapped_column(String(100))
    model: Mapped[str] = mapped_column(String(255))

    units: Mapped[int] = mapped_column(
        Integer,
        default=1,
    )

    cost_usd: Mapped[float] = mapped_column(
        Float,
        default=0.0,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )


Index(
    "ix_suggestion_post_image",
    Suggestion.post_id,
    Suggestion.image_id,
)
