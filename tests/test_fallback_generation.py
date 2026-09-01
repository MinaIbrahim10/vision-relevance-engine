from pathlib import Path
from uuid import uuid4

from app.config import get_settings
from app.models import (
    Post,
    Tenant,
)
from app.services.fallback import (
    build_generation_prompt,
    generate_fallback_for_post,
)
from app.tenancy import hash_api_key


def make_tenant(db):
    token = uuid4().hex

    tenant = Tenant(
        slug=f"fallback-{token}",
        name="Fallback Tenant",
        api_key_hash=hash_api_key(
            token
        ),
    )

    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    return tenant


def test_generation_prompt_contains_subject(
    db,
):
    tenant = make_tenant(db)

    post = Post(
        tenant_id=tenant.id,
        title="Red fox conservation",
        body="Article about fox habitat.",
        expected_subject="red fox",
        expected_category="animal",
    )

    db.add(post)
    db.commit()

    prompt = build_generation_prompt(
        post
    )

    assert "red fox" in prompt.lower()
    assert "no text" in prompt.lower()


def test_mock_fallback_generates_real_file(
    db,
    tmp_path,
    monkeypatch,
):
    tenant = make_tenant(db)

    post = Post(
        tenant_id=tenant.id,
        title="Rare arctic fox",
        body="No suitable library image.",
        expected_subject="arctic fox",
        expected_category="animal",
    )

    db.add(post)
    db.commit()
    db.refresh(post)

    settings = get_settings()

    monkeypatch.setattr(
        settings,
        "image_generation_provider",
        "mock",
    )

    image = (
        generate_fallback_for_post(
            db,
            post=post,
            output_dir=str(tmp_path),
        )
    )

    assert Path(
        image.path
    ).exists()

    assert image.needs_review is True
    assert image.processed is False


def test_disabled_generator_fails_safely(
    monkeypatch,
):
    from app.services.image_generator import (
        get_image_generator,
    )

    settings = get_settings()

    monkeypatch.setattr(
        settings,
        "image_generation_provider",
        "disabled",
    )

    try:
        get_image_generator()
    except RuntimeError as exc:
        assert "disabled" in str(exc)
    else:
        raise AssertionError(
            "disabled generator should fail"
        )
