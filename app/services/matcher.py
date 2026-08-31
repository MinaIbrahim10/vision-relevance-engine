import json

import numpy as np
from sqlalchemy.orm import Session

from app.models import AIUsage, ImageAsset, Post, Suggestion
from app.services.guard import evaluate_candidate
from app.services.providers import get_embedding_provider


def cosine_similarity(
    left: list[float],
    right: list[float],
) -> float:
    a = np.array(left, dtype=np.float64)
    b = np.array(right, dtype=np.float64)

    denominator = np.linalg.norm(a) * np.linalg.norm(b)

    if denominator == 0:
        return 0.0

    return float(np.dot(a, b) / denominator)


def get_post_embedding(
    db: Session,
    post: Post,
) -> list[float]:
    if post.embedding_json:
        return json.loads(post.embedding_json)

    provider = get_embedding_provider()

    text = f"{post.title}\n{post.body}"
    embedding = provider.embed(text)

    post.embedding_json = json.dumps(embedding)
    db.add(post)

    db.add(
        AIUsage(
            operation="embedding",
            provider=provider.name,
            model=provider.model,
            units=1,
            cost_usd=0.0,
        )
    )

    db.commit()

    return embedding


def match_post(
    db: Session,
    post: Post,
) -> Suggestion:
    post_embedding = get_post_embedding(db, post)

    candidates = (
        db.query(ImageAsset)
        .filter(ImageAsset.processed.is_(True))
        .all()
    )

    ranked: list[tuple[float, ImageAsset]] = []

    for image in candidates:
        if not image.embedding_json:
            continue

        score = cosine_similarity(
            post_embedding,
            json.loads(image.embedding_json),
        )

        ranked.append((score, image))

    ranked.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    rejection_reasons = []

    for score, image in ranked:
        decision = evaluate_candidate(
            expected_subject=post.expected_subject,
            expected_category=post.expected_category,
            image_subject=image.subject,
            image_category=image.category,
            confidence=image.confidence,
            similarity=score,
        )

        if decision.accepted:
            suggestion = Suggestion(
                post_id=post.id,
                image_id=image.id,
                similarity=score,
                accepted_by_guard=True,
                reason=decision.reason,
            )

            db.add(suggestion)
            db.commit()
            db.refresh(suggestion)

            return suggestion

        rejection_reasons.append(
            f"{image.filename}: {decision.reason}"
        )

    reason = (
        "No confident match. "
        + "; ".join(rejection_reasons[:3])
        if rejection_reasons
        else "No confident match. No processed image candidates."
    )

    suggestion = Suggestion(
        post_id=post.id,
        image_id=None,
        similarity=0.0,
        accepted_by_guard=False,
        reason=reason,
    )

    db.add(suggestion)
    db.commit()
    db.refresh(suggestion)

    return suggestion
