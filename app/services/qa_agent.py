import json

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import (
    ImageAsset,
    Post,
    QAReview,
    Suggestion,
)


def analyze_suggestion(
    db: Session,
    suggestion: Suggestion,
) -> dict:
    settings = get_settings()

    post = (
        db.query(Post)
        .filter(
            Post.id == suggestion.post_id,
            Post.tenant_id == suggestion.tenant_id,
        )
        .first()
    )

    image = None

    if suggestion.image_id is not None:
        image = (
            db.query(ImageAsset)
            .filter(
                ImageAsset.id == suggestion.image_id,
                ImageAsset.tenant_id == suggestion.tenant_id,
            )
            .first()
        )

    signals = {
        "guard_accepted": suggestion.accepted_by_guard,
        "similarity": round(
            suggestion.similarity,
            6,
        ),
        "similarity_threshold": (
            settings.min_similarity_score
        ),
        "post_expected_subject": (
            post.expected_subject
            if post
            else None
        ),
        "image_subject": (
            image.subject
            if image
            else None
        ),
        "vision_confidence": (
            image.confidence
            if image
            else None
        ),
        "needs_review": (
            image.needs_review
            if image
            else None
        ),
        "guard_reason": suggestion.reason,
    }

    if not suggestion.accepted_by_guard:
        return {
            "recommendation": "reject",
            "rationale": (
                "The deterministic safety guard rejected "
                "this candidate. Human review may override "
                "the recommendation, but the agent will not "
                "auto-approve a guard failure."
            ),
            "signals": signals,
            "requires_human": True,
        }

    if image is None:
        return {
            "recommendation": "reject",
            "rationale": (
                "The suggestion references no tenant-owned "
                "image candidate."
            ),
            "signals": signals,
            "requires_human": True,
        }

    if (
        image.needs_review
        or image.confidence is None
        or image.confidence
        < settings.min_vision_confidence
    ):
        return {
            "recommendation": "review",
            "rationale": (
                "The candidate passed the matching guard, "
                "but its vision metadata is low-confidence "
                "or explicitly flagged for review."
            ),
            "signals": signals,
            "requires_human": True,
        }

    margin = (
        suggestion.similarity
        - settings.min_similarity_score
    )

    if margin < 0.05:
        return {
            "recommendation": "review",
            "rationale": (
                "The candidate passed the semantic threshold "
                "with a narrow margin, so the agent requests "
                "human confirmation instead of auto-trusting it."
            ),
            "signals": signals,
            "requires_human": True,
        }

    return {
        "recommendation": "approve",
        "rationale": (
            "The candidate passed the deterministic guard, "
            "has sufficient vision confidence, and has a "
            "semantic score comfortably above the calibrated "
            "threshold. Final approval remains human-controlled."
        ),
        "signals": signals,
        "requires_human": True,
    }


def run_suggestion_qa(
    db: Session,
    suggestion: Suggestion,
) -> QAReview:
    result = analyze_suggestion(
        db,
        suggestion,
    )

    existing = (
        db.query(QAReview)
        .filter(
            QAReview.tenant_id
            == suggestion.tenant_id,
            QAReview.suggestion_id
            == suggestion.id,
        )
        .first()
    )

    if existing:
        review = existing
    else:
        review = QAReview(
            tenant_id=suggestion.tenant_id,
            suggestion_id=suggestion.id,
        )

    review.recommendation = (
        result["recommendation"]
    )

    review.rationale = (
        result["rationale"]
    )

    review.signals_json = json.dumps(
        result["signals"]
    )

    review.requires_human = True

    db.add(review)
    db.commit()
    db.refresh(review)

    return review


def serialize_qa_review(
    review: QAReview,
) -> dict:
    return {
        "id": review.id,
        "suggestion_id": review.suggestion_id,
        "recommendation": review.recommendation,
        "rationale": review.rationale,
        "signals": json.loads(
            review.signals_json
        ),
        "requires_human": review.requires_human,
    }
