from sqlalchemy.orm import Session

from app.models import (
    ImageAsset,
    Post,
)
from app.services.guard import normalize_subject
from app.services.matcher import match_post


def evaluate_top1(
    db: Session,
    tenant_id: int,
) -> dict:
    posts = (
        db.query(Post)
        .filter(
            Post.tenant_id == tenant_id,
            Post.expected_subject.isnot(None),
        )
        .all()
    )

    results = []
    correct = 0

    for post in posts:
        suggestion = match_post(
            db,
            post,
        )

        predicted_subject = None

        if suggestion.image_id:
            image = (
                db.query(ImageAsset)
                .filter(
                    ImageAsset.id
                    == suggestion.image_id,
                    ImageAsset.tenant_id
                    == tenant_id,
                )
                .first()
            )

            if image:
                predicted_subject = (
                    image.subject
                )

        expected_norm = normalize_subject(
            post.expected_subject
        )
        predicted_norm = normalize_subject(
            predicted_subject
        )

        is_correct = (
            suggestion.accepted_by_guard
            and expected_norm
            and expected_norm
            == predicted_norm
        )

        correct += int(is_correct)

        results.append(
            {
                "post_id": post.id,
                "title": post.title,
                "expected_subject": (
                    post.expected_subject
                ),
                "predicted_subject": (
                    predicted_subject
                ),
                "normalized_expected": (
                    expected_norm
                ),
                "normalized_prediction": (
                    predicted_norm
                ),
                "image_id": (
                    suggestion.image_id
                ),
                "accepted": (
                    suggestion
                    .accepted_by_guard
                ),
                "similarity": round(
                    suggestion.similarity,
                    6,
                ),
                "correct": is_correct,
                "reason": (
                    suggestion.reason
                ),
            }
        )

    total = len(results)

    precision = (
        correct / total
        if total
        else 0.0
    )

    return {
        "metric": "top_1_precision",
        "total": total,
        "correct": correct,
        "precision": round(
            precision,
            6,
        ),
        "results": results,
    }
