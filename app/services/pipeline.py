import json

from sqlalchemy import func
from sqlalchemy.orm import Session
from tenacity import (
    retry,
    stop_after_attempt,
    wait_fixed,
)

from app.config import get_settings
from app.models import (
    AIUsage,
    BackgroundJob,
    ImageAsset,
    JobAlert,
)
from app.services.providers import (
    get_embedding_provider,
    get_vision_provider,
)


def log_usage(
    db: Session,
    *,
    tenant_id: int | None,
    operation: str,
    provider: str,
    model: str,
    cost_usd: float = 0.0,
):
    db.add(
        AIUsage(
            tenant_id=tenant_id,
            operation=operation,
            provider=provider,
            model=model,
            units=1,
            cost_usd=cost_usd,
        )
    )

    db.commit()


def assert_budget(
    db: Session,
    tenant_id: int,
):
    settings = get_settings()

    total = (
        db.query(
            func.coalesce(
                func.sum(AIUsage.cost_usd),
                0.0,
            )
        )
        .filter(
            AIUsage.tenant_id
            == tenant_id
        )
        .scalar()
    )

    if float(total) >= settings.ai_budget_usd:
        raise RuntimeError(
            "AI budget guard reached: "
            f"${float(total):.4f}"
        )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(1),
    reraise=True,
)
def process_single_image(
    db: Session,
    image: ImageAsset,
):
    assert_budget(
        db,
        image.tenant_id,
    )

    vision = get_vision_provider()
    embedder = get_embedding_provider()

    metadata = vision.analyze(
        image.path
    )

    log_usage(
        db,
        tenant_id=image.tenant_id,
        operation="vision",
        provider=vision.name,
        model=vision.model,
    )

    image.subject = metadata.subject
    image.category = metadata.category
    image.attributes_json = json.dumps(
        metadata.attributes
    )
    image.caption = metadata.caption
    image.confidence = metadata.confidence
    image.alt_text = metadata.caption
    image.needs_review = (
        metadata.confidence
        < get_settings().min_vision_confidence
    )

    embedding = embedder.embed(
        metadata.caption
    )

    log_usage(
        db,
        tenant_id=image.tenant_id,
        operation="embedding",
        provider=embedder.name,
        model=embedder.model,
    )

    image.embedding_json = json.dumps(
        embedding
    )
    image.processed = True

    db.add(image)
    db.commit()


def add_alert(
    db: Session,
    *,
    job: BackgroundJob,
    level: str,
    message: str,
):
    db.add(
        JobAlert(
            tenant_id=job.tenant_id,
            job_id=job.id,
            level=level,
            message=message,
        )
    )


def execute_job_attempt(
    db: Session,
    job: BackgroundJob,
):
    if job.status not in {
        "queued",
        "retry",
    }:
        return

    job.status = "running"
    job.attempts += 1
    job.error = None
    db.commit()

    try:
        images = (
            db.query(ImageAsset)
            .filter(
                ImageAsset.tenant_id
                == job.tenant_id,
                ImageAsset.processed.is_(False),
            )
            .all()
        )

        job.total_items = len(images)
        job.completed_items = 0
        db.commit()

        for image in images:
            process_single_image(
                db,
                image,
            )

            job.completed_items += 1
            db.commit()

        job.status = "completed"
        job.error = None
        db.commit()

    except Exception as exc:
        message = str(exc)
        job.error = message

        if job.attempts < job.max_attempts:
            job.status = "retry"

            add_alert(
                db,
                job=job,
                level="warning",
                message=(
                    f"Job attempt "
                    f"{job.attempts} failed; "
                    f"retry scheduled: "
                    f"{message}"
                ),
            )
        else:
            job.status = "failed"

            add_alert(
                db,
                job=job,
                level="error",
                message=(
                    f"Job failed after "
                    f"{job.attempts} attempts: "
                    f"{message}"
                ),
            )

        db.commit()


def process_images_job(
    session_factory,
    job_id: int,
):
    db = session_factory()

    try:
        job = db.get(
            BackgroundJob,
            job_id,
        )

        if not job:
            return False

        execute_job_attempt(
            db,
            job,
        )

        return True

    finally:
        db.close()


def run_next_job(
    session_factory,
) -> bool:
    db = session_factory()

    try:
        job = (
            db.query(BackgroundJob)
            .filter(
                BackgroundJob.status.in_(
                    ["queued", "retry"]
                )
            )
            .order_by(
                BackgroundJob.created_at.asc()
            )
            .first()
        )

        if not job:
            return False

        job_id = job.id

    finally:
        db.close()

    process_images_job(
        session_factory,
        job_id,
    )

    return True
