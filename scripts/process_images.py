import json

from tenacity import retry, stop_after_attempt, wait_fixed

from app.config import get_settings
from app.db import SessionLocal
from app.models import ImageAsset
from app.services.pipeline import (
    assert_budget,
    log_usage,
)
from app.services.providers import (
    get_embedding_provider,
    get_vision_provider,
)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(1),
    reraise=True,
)
def analyze_image(provider, path):
    return provider.analyze(path)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(1),
    reraise=True,
)
def embed_text(provider, text):
    return provider.embed(text)


def main():
    db = SessionLocal()

    try:
        images = db.query(ImageAsset).all()

        vision = get_vision_provider()

        print(
            f"Vision provider: "
            f"{vision.name}/{vision.model}"
        )

        print("\n=== Stage 1: Vision ===")

        for index, image in enumerate(
            images,
            start=1,
        ):
            assert_budget(db)

            metadata = analyze_image(
                vision,
                image.path,
            )

            image.subject = metadata.subject
            image.category = metadata.category
            image.attributes_json = json.dumps(
                metadata.attributes
            )
            image.caption = metadata.caption
            image.confidence = metadata.confidence
            image.alt_text = metadata.caption
            image.needs_review = (
                metadata.confidence
                < get_settings().min_vision_confidence
            )
            image.processed = False

            db.add(image)
            db.commit()

            log_usage(
                db,
                tenant_id=image.tenant_id,
                operation="vision",
                provider=vision.name,
                model=vision.model,
            )

            print(
                f"[VISION {index:02d}/{len(images)}] "
                f"{image.filename}: "
                f"{metadata.subject} | "
                f"{metadata.category} | "
                f"{metadata.confidence:.2f}"
            )

        embedder = get_embedding_provider()

        print(
            "\nEmbedding provider: "
            f"{embedder.name}/{embedder.model}"
        )

        print("\n=== Stage 2: Embeddings ===")

        for index, image in enumerate(
            images,
            start=1,
        ):
            assert_budget(db)

            text = (
                f"{image.subject}. "
                f"{image.category}. "
                f"{image.caption or ''}. "
                f"{image.attributes_json or ''}"
            )

            embedding = embed_text(
                embedder,
                text,
            )

            image.embedding_json = json.dumps(
                embedding
            )
            image.processed = True

            db.add(image)
            db.commit()

            log_usage(
                db,
                tenant_id=image.tenant_id,
                operation="embedding",
                provider=embedder.name,
                model=embedder.model,
            )

            print(
                f"[EMBED {index:02d}/{len(images)}] "
                f"{image.filename} "
                f"dim={len(embedding)}"
            )

        print(
            f"\nCompleted real processing "
            f"for {len(images)} images."
        )

    finally:
        db.close()


if __name__ == "__main__":
    main()
