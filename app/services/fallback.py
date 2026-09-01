from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models import AIUsage, ImageAsset, Post
from app.services.image_generator import (
    get_image_generator,
)


def build_generation_prompt(
    post: Post,
) -> str:
    subject = (
        post.expected_subject
        or post.title
    )

    category = (
        post.expected_category
        or "editorial"
    )

    return (
        f"Create a realistic editorial photograph "
        f"for an article titled '{post.title}'. "
        f"Primary subject: {subject}. "
        f"Category: {category}. "
        f"The image must clearly depict the requested "
        f"subject, contain no text or watermark, "
        f"and avoid unrelated animals or objects."
    )


def generate_fallback_for_post(
    db: Session,
    *,
    post: Post,
    output_dir: str = "artifacts/generated",
) -> ImageAsset:
    generator = (
        get_image_generator()
    )

    prompt = build_generation_prompt(
        post
    )

    filename = (
        f"generated-post-{post.id}-"
        f"{uuid4().hex[:10]}.jpg"
    )

    path = str(
        Path(output_dir)
        / filename
    )

    generated = generator.generate(
        prompt=prompt,
        output_path=path,
    )

    image = ImageAsset(
        tenant_id=post.tenant_id,
        filename=filename,
        path=generated.path,
        subject=post.expected_subject,
        category=post.expected_category,
        caption=(
            "Generated fallback image for "
            f"post {post.id}: {post.title}"
        ),
        confidence=1.0,
        alt_text=(
            post.expected_subject
            or post.title
        ),
        needs_review=True,
        processed=False,
    )

    db.add(image)

    db.add(
        AIUsage(
            tenant_id=post.tenant_id,
            operation="image_generation",
            provider=generated.provider,
            model=generated.model,
            units=1,
            cost_usd=generated.cost_usd,
        )
    )

    db.commit()
    db.refresh(image)

    return image
