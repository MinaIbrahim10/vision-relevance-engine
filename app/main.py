from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    HTTPException,
)
from sqlalchemy.orm import Session

from app.db import (
    Base,
    SessionLocal,
    engine,
    get_db,
)
from app.models import (
    AIUsage,
    BackgroundJob,
    ImageAsset,
    Post,
    Suggestion,
)
from app.schemas import (
    ImageCreate,
    MatchResult,
    PostCreate,
    ReviewCreate,
)
from app.services.matcher import match_post
from app.services.pipeline import process_images_job


Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Vision Relevance Engine",
    version="0.1.0",
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "vision-relevance-engine",
    }


@app.post("/api/v1/images", status_code=201)
def create_image(
    payload: ImageCreate,
    db: Session = Depends(get_db),
):
    existing = (
        db.query(ImageAsset)
        .filter(ImageAsset.filename == payload.filename)
        .first()
    )

    if existing:
        return {
            "id": existing.id,
            "filename": existing.filename,
            "idempotent": True,
        }

    image = ImageAsset(
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
):
    images = db.query(ImageAsset).all()

    return [
        {
            "id": image.id,
            "filename": image.filename,
            "subject": image.subject,
            "category": image.category,
            "confidence": image.confidence,
            "processed": image.processed,
            "needs_review": image.needs_review,
            "alt_text": image.alt_text,
        }
        for image in images
    ]


@app.post("/api/v1/posts", status_code=201)
def create_post(
    payload: PostCreate,
    db: Session = Depends(get_db),
):
    post = Post(**payload.model_dump())

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
):
    posts = db.query(Post).all()

    return [
        {
            "id": post.id,
            "title": post.title,
            "expected_subject": post.expected_subject,
            "expected_category": post.expected_category,
        }
        for post in posts
    ]


@app.post("/api/v1/jobs/process-images", status_code=202)
def start_processing(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    job = BackgroundJob(
        kind="image_processing",
        status="queued",
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(
        process_images_job,
        SessionLocal,
        job.id,
    )

    return {
        "job_id": job.id,
        "status": job.status,
    }


@app.get("/api/v1/jobs/{job_id}")
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
):
    job = db.get(BackgroundJob, job_id)

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found",
        )

    return {
        "id": job.id,
        "status": job.status,
        "attempts": job.attempts,
        "total_items": job.total_items,
        "completed_items": job.completed_items,
        "error": job.error,
    }


@app.get(
    "/api/v1/posts/{post_id}/images",
    response_model=MatchResult,
)
def recommend_image(
    post_id: int,
    db: Session = Depends(get_db),
):
    post = db.get(Post, post_id)

    if not post:
        raise HTTPException(
            status_code=404,
            detail="Post not found",
        )

    suggestion = match_post(db, post)

    return MatchResult(
        post_id=post.id,
        image_id=suggestion.image_id,
        similarity=suggestion.similarity,
        accepted=suggestion.accepted_by_guard,
        reason=suggestion.reason,
    )


@app.post("/api/v1/reviews")
def review_suggestion(
    payload: ReviewCreate,
    db: Session = Depends(get_db),
):
    suggestion = db.get(
        Suggestion,
        payload.suggestion_id,
    )

    if not suggestion:
        raise HTTPException(
            status_code=404,
            detail="Suggestion not found",
        )

    suggestion.human_decision = payload.decision
    suggestion.human_notes = payload.notes

    db.add(suggestion)
    db.commit()

    return {
        "suggestion_id": suggestion.id,
        "decision": suggestion.human_decision,
    }


@app.get("/api/v1/usage")
def usage(
    db: Session = Depends(get_db),
):
    records = db.query(AIUsage).all()

    return {
        "total_calls": len(records),
        "total_cost_usd": round(
            sum(record.cost_usd for record in records),
            6,
        ),
        "calls": [
            {
                "operation": record.operation,
                "provider": record.provider,
                "model": record.model,
                "cost_usd": record.cost_usd,
            }
            for record in records
        ],
    }


@app.get("/api/v1/evaluation")
def run_evaluation(
    db: Session = Depends(get_db),
):
    from app.services.evaluator import (
        evaluate_top1,
    )

    return evaluate_top1(db)
