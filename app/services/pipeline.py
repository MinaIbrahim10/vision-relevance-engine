import json

from sqlalchemy.orm import Session
from tenacity import retry, stop_after_attempt, wait_fixed

from app.config import get_settings
from app.models import AIUsage, BackgroundJob, ImageAsset
from app.services.providers import (
    get_embedding_provider,
    get_vision_provider,
)


def log_usage(
    db: Session,
    *,
    operation: str,
    provider: str,
    model: str,
    cost_usd: float = 0.0,
):
    usage = AIUsage(
        operation=operation,
        provider=provider,
        model=model,
        units=1,
        cost_usd=cost_usd,
    )

    db.add(usage)
    db.commit()


def assert_budget(db: Session):
    settings = get_settings()

    total = sum(
        row.cost_usd
        for row in db.query(AIUsage).all()
    )

    if total >= settings.ai_budget_usd:
        raise RuntimeError(
            f"AI budget guard reached: ${total:.4f}"
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
    assert_budget(db)

    vision = get_vision_provider()
    embedder = get_embedding_provider()

    metadata = vision.analyze(image.path)

    log_usage(
        db,
        operation="vision",
        provider=vision.name,
        model=vision.model,
    )

    image.subject = metadata.subject
    image.category = metadata.category
    image.attributes_json = json.dumps(metadata.attributes)
    image.caption = metadata.caption
    image.confidence = metadata.confidence
    image.alt_text = metadata.caption
    image.needs_review = (
        metadata.confidence
        < get_settings().min_vision_confidence
    )

    embedding = embedder.embed(metadata.caption)

    log_usage(
        db,
        operation="embedding",
        provider=embedder.name,
        model=embedder.model,
    )

    image.embedding_json = json.dumps(embedding)
    image.processed = True

    db.add(image)
    db.commit()


def process_images_job(
    session_factory,
    job_id: int,
):
    db = session_factory()

    try:
        job = db.get(BackgroundJob, job_id)

        if not job:
            return

        job.status = "running"
        job.attempts += 1
        db.commit()

        images = (
            db.query(ImageAsset)
            .filter(ImageAsset.processed.is_(False))
            .all()
        )

        job.total_items = len(images)
        db.commit()

        for image in images:
            process_single_image(db, image)
            job.completed_items += 1
            db.commit()

        job.status = "completed"
        db.commit()

    except Exception as exc:
        job = db.get(BackgroundJob, job_id)

        if job:
            job.status = "failed"
            job.error = str(exc)
            db.commit()

    finally:
        db.close()
