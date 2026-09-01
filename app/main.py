from uuid import uuid4

from fastapi import (
    Depends,
    FastAPI,
    Header,
    HTTPException,
)
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import (
    AIUsage,
    BackgroundJob,
    ImageAsset,
    JobAlert,
    Post,
    Suggestion,
    Tenant,
)
from app.schemas import (
    ImageCreate,
    MatchResult,
    PostCreate,
    ReviewCreate,
)
from app.services.evaluator import evaluate_top1
from app.services.matcher import match_post
from app.tenancy import get_tenant


app = FastAPI(
    title="Vision Relevance Engine",
    version="0.2.0",
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "vision-relevance-engine",
    }


@app.get("/api/v1/tenant")
def current_tenant(
    tenant: Tenant = Depends(get_tenant),
):
    return {
        "id": tenant.id,
        "slug": tenant.slug,
        "name": tenant.name,
    }


@app.post(
    "/api/v1/images",
    status_code=201,
)
def create_image(
    payload: ImageCreate,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
):
    existing = (
        db.query(ImageAsset)
        .filter(
            ImageAsset.tenant_id
            == tenant.id,
            ImageAsset.filename
            == payload.filename,
        )
        .first()
    )

    if existing:
        return {
            "id": existing.id,
            "filename": existing.filename,
            "idempotent": True,
        }

    image = ImageAsset(
        tenant_id=tenant.id,
        filename=payload.filename,
        path=payload.path,
    )

    db.add(image)
    db.commit()
    db.refresh(image)

    return {
        "id": image.id,
        "filename": image.filename,
        "idempotent": False,
    }


@app.get("/api/v1/images")
def list_images(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
):
    images = (
        db.query(ImageAsset)
        .filter(
            ImageAsset.tenant_id
            == tenant.id
        )
        .all()
    )

    return [
        {
            "id": image.id,
            "filename": image.filename,
            "subject": image.subject,
            "category": image.category,
            "confidence": image.confidence,
            "processed": image.processed,
            "needs_review": (
                image.needs_review
            ),
            "alt_text": image.alt_text,
        }
        for image in images
    ]


@app.post(
    "/api/v1/posts",
    status_code=201,
)
def create_post(
    payload: PostCreate,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
):
    post = Post(
        tenant_id=tenant.id,
        **payload.model_dump(),
    )

    db.add(post)
    db.commit()
    db.refresh(post)

    return {
        "id": post.id,
        "title": post.title,
    }


@app.get("/api/v1/posts")
def list_posts(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
):
    posts = (
        db.query(Post)
        .filter(
            Post.tenant_id
            == tenant.id
        )
        .all()
    )

    return [
        {
            "id": post.id,
            "title": post.title,
            "expected_subject": (
                post.expected_subject
            ),
            "expected_category": (
                post.expected_category
            ),
        }
        for post in posts
    ]


@app.post(
    "/api/v1/jobs/process-images",
    status_code=202,
)
def start_processing(
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
    ),
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
):
    key = (
        idempotency_key
        or str(uuid4())
    )

    existing = (
        db.query(BackgroundJob)
        .filter(
            BackgroundJob.tenant_id
            == tenant.id,
            BackgroundJob.idempotency_key
            == key,
        )
        .first()
    )

    if existing:
        return {
            "job_id": existing.id,
            "status": existing.status,
            "idempotent": True,
        }

    job = BackgroundJob(
        tenant_id=tenant.id,
        kind="image_processing",
        idempotency_key=key,
        status="queued",
        max_attempts=(
            get_settings()
            .max_job_attempts
        ),
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    return {
        "job_id": job.id,
        "status": job.status,
        "idempotent": False,
    }


@app.get("/api/v1/jobs/{job_id}")
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
):
    job = (
        db.query(BackgroundJob)
        .filter(
            BackgroundJob.id == job_id,
            BackgroundJob.tenant_id
            == tenant.id,
        )
        .first()
    )

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found",
        )

    return {
        "id": job.id,
        "status": job.status,
        "attempts": job.attempts,
        "max_attempts": job.max_attempts,
        "total_items": job.total_items,
        "completed_items": (
            job.completed_items
        ),
        "error": job.error,
    }


@app.get(
    "/api/v1/posts/{post_id}/images",
    response_model=MatchResult,
)
def recommend_image(
    post_id: int,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
):
    post = (
        db.query(Post)
        .filter(
            Post.id == post_id,
            Post.tenant_id
            == tenant.id,
        )
        .first()
    )

    if not post:
        raise HTTPException(
            status_code=404,
            detail="Post not found",
        )

    suggestion = match_post(
        db,
        post,
    )

    return MatchResult(
        post_id=post.id,
        image_id=suggestion.image_id,
        similarity=suggestion.similarity,
        accepted=(
            suggestion
            .accepted_by_guard
        ),
        reason=suggestion.reason,
    )


@app.post("/api/v1/reviews")
def review_suggestion(
    payload: ReviewCreate,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
):
    suggestion = (
        db.query(Suggestion)
        .filter(
            Suggestion.id
            == payload.suggestion_id,
            Suggestion.tenant_id
            == tenant.id,
        )
        .first()
    )

    if not suggestion:
        raise HTTPException(
            status_code=404,
            detail="Suggestion not found",
        )

    suggestion.human_decision = (
        payload.decision
    )
    suggestion.human_notes = (
        payload.notes
    )

    db.add(suggestion)
    db.commit()

    return {
        "suggestion_id": (
            suggestion.id
        ),
        "decision": (
            suggestion.human_decision
        ),
    }


@app.get("/api/v1/usage")
def usage(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
):
    records = (
        db.query(AIUsage)
        .filter(
            AIUsage.tenant_id
            == tenant.id
        )
        .all()
    )

    return {
        "total_calls": len(records),
        "total_cost_usd": round(
            sum(
                record.cost_usd
                for record in records
            ),
            6,
        ),
        "calls": [
            {
                "operation": (
                    record.operation
                ),
                "provider": (
                    record.provider
                ),
                "model": record.model,
                "cost_usd": (
                    record.cost_usd
                ),
            }
            for record in records
        ],
    }


@app.get("/api/v1/alerts")
def alerts(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
):
    records = (
        db.query(JobAlert)
        .filter(
            JobAlert.tenant_id
            == tenant.id
        )
        .order_by(
            JobAlert.created_at.desc()
        )
        .all()
    )

    return [
        {
            "id": alert.id,
            "job_id": alert.job_id,
            "level": alert.level,
            "message": alert.message,
        }
        for alert in records
    ]


@app.get("/api/v1/evaluation")
def run_evaluation(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
):
    return evaluate_top1(
        db,
        tenant.id,
    )


@app.get(
    "/api/v1/images/{image_id}/alt-text"
)
def image_alt_text(
    image_id: int,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
):
    from app.services.alt_text import (
        generate_alt_text,
    )

    image = (
        db.query(ImageAsset)
        .filter(
            ImageAsset.id == image_id,
            ImageAsset.tenant_id
            == tenant.id,
        )
        .first()
    )

    if not image:
        raise HTTPException(
            status_code=404,
            detail="Image not found",
        )

    alt_text = generate_alt_text(
        image
    )

    image.alt_text = alt_text

    db.add(image)
    db.commit()

    return {
        "image_id": image.id,
        "alt_text": alt_text,
        "source": (
            "vision_metadata"
        ),
    }


@app.get(
    "/api/v1/images/{image_id}/duplicates"
)
def image_duplicates(
    image_id: int,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
):
    from app.config import get_settings
    from app.services.duplicates import (
        average_hash,
        duplicate_similarity,
    )

    image = (
        db.query(ImageAsset)
        .filter(
            ImageAsset.id == image_id,
            ImageAsset.tenant_id
            == tenant.id,
        )
        .first()
    )

    if not image:
        raise HTTPException(
            status_code=404,
            detail="Image not found",
        )

    try:
        source_hash = (
            image.perceptual_hash
            or average_hash(
                image.path
            )
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=422,
            detail=(
                "Image file is unavailable "
                "for duplicate analysis"
            ),
        )

    image.perceptual_hash = source_hash
    db.add(image)

    threshold = (
        get_settings()
        .duplicate_threshold
    )

    matches = []

    candidates = (
        db.query(ImageAsset)
        .filter(
            ImageAsset.tenant_id
            == tenant.id,
            ImageAsset.id
            != image.id,
        )
        .all()
    )

    for candidate in candidates:
        try:
            candidate_hash = (
                candidate.perceptual_hash
                or average_hash(
                    candidate.path
                )
            )
        except FileNotFoundError:
            continue

        candidate.perceptual_hash = (
            candidate_hash
        )

        similarity = (
            duplicate_similarity(
                source_hash,
                candidate_hash,
            )
        )

        db.add(candidate)

        if similarity >= threshold:
            matches.append(
                {
                    "image_id":
                    candidate.id,
                    "filename":
                    candidate.filename,
                    "similarity":
                    round(
                        similarity,
                        6,
                    ),
                }
            )

    db.commit()

    matches.sort(
        key=lambda item:
        item["similarity"],
        reverse=True,
    )

    return {
        "image_id": image.id,
        "threshold": threshold,
        "duplicates": matches,
    }
