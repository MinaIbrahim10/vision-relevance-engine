from uuid import uuid4

from app.models import (
    ImageAsset,
    Post,
    Suggestion,
    Tenant,
)
from app.services.qa_agent import (
    analyze_suggestion,
    run_suggestion_qa,
)
from app.tenancy import hash_api_key


def create_tenant(db):
    token = uuid4().hex

    item = Tenant(
        slug=f"qa-{token}",
        name="QA Tenant",
        api_key_hash=hash_api_key(
            token
        ),
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    return item


def create_case(
    db,
    *,
    similarity=0.80,
    accepted=True,
    confidence=0.95,
    needs_review=False,
):
    tenant = create_tenant(db)

    post = Post(
        tenant_id=tenant.id,
        title="Red fox article",
        body="A red fox in a forest.",
        expected_subject="red fox",
        expected_category="animal",
    )

    image = ImageAsset(
        tenant_id=tenant.id,
        filename=f"fox-{uuid4().hex}.jpg",
        path="/tmp/fox.jpg",
        subject="red fox",
        category="animal",
        confidence=confidence,
        needs_review=needs_review,
        processed=True,
    )

    db.add_all(
        [
            post,
            image,
        ]
    )
    db.commit()

    suggestion = Suggestion(
        tenant_id=tenant.id,
        post_id=post.id,
        image_id=image.id,
        similarity=similarity,
        accepted_by_guard=accepted,
        reason=(
            "Candidate passed guards."
            if accepted
            else "Subject mismatch."
        ),
    )

    db.add(suggestion)
    db.commit()
    db.refresh(suggestion)

    return (
        tenant,
        post,
        image,
        suggestion,
    )


def test_high_quality_match_recommends_approve(
    db,
):
    _, _, _, suggestion = (
        create_case(db)
    )

    result = analyze_suggestion(
        db,
        suggestion,
    )

    assert (
        result["recommendation"]
        == "approve"
    )

    assert (
        result["requires_human"]
        is True
    )


def test_guard_failure_recommends_reject(
    db,
):
    _, _, _, suggestion = (
        create_case(
            db,
            accepted=False,
        )
    )

    result = analyze_suggestion(
        db,
        suggestion,
    )

    assert (
        result["recommendation"]
        == "reject"
    )


def test_borderline_similarity_requests_review(
    db,
):
    _, _, _, suggestion = (
        create_case(
            db,
            similarity=0.47,
        )
    )

    result = analyze_suggestion(
        db,
        suggestion,
    )

    assert (
        result["recommendation"]
        == "review"
    )


def test_low_confidence_requests_review(
    db,
):
    _, _, _, suggestion = (
        create_case(
            db,
            confidence=0.40,
            needs_review=True,
        )
    )

    result = analyze_suggestion(
        db,
        suggestion,
    )

    assert (
        result["recommendation"]
        == "review"
    )


def test_qa_agent_never_sets_human_decision(
    db,
):
    _, _, _, suggestion = (
        create_case(db)
    )

    first = run_suggestion_qa(
        db,
        suggestion,
    )

    second = run_suggestion_qa(
        db,
        suggestion,
    )

    db.refresh(suggestion)

    assert first.id == second.id

    assert (
        suggestion.human_decision
        is None
    )

    assert (
        first.requires_human
        is True
    )
