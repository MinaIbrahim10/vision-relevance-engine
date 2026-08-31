from sqlalchemy.orm import Session

from app.models import (
    ImageAsset,
    Post,
)
from app.services.matcher import (
    match_post,
)


def evaluate_top1(
    db: Session,
) -> dict:
    posts = (
        db.query(Post)
        .filter(
            Post.expected_subject.isnot(None)
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
            image = db.get(
                ImageAsset,
                suggestion.image_id,
            )

            if image:
                predicted_subject = (
                    image.subject
                )

        expected = (
            post.expected_subject
            or ""
        ).lower()

        predicted = (
            predicted_subject
            or ""
        ).lower()

        is_correct = (
            suggestion.accepted_by_guard
            and expected == predicted
        )

        correct += int(
            is_correct
        )

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
