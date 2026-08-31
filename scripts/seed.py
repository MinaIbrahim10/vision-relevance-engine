import json
from pathlib import Path

from app.db import (
    Base,
    SessionLocal,
    engine,
)
from app.tenancy import ensure_demo_tenant
from app.models import (
    ImageAsset,
    Post,
    Tenant,
)


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "corpus_manifest.json"

POSTS = [
    {
        "title": "Red fox behavior",
        "body": (
            "How red foxes hunt and live "
            "in forest environments."
        ),
        "expected_subject": "red fox",
        "expected_category": "animal",
    },
    {
        "title": "Vulpes vulpes habitat",
        "body": (
            "A field guide to Vulpes vulpes "
            "and its natural habitat."
        ),
        "expected_subject": "red fox",
        "expected_category": "animal",
    },
    {
        "title": "Gray wolf packs",
        "body": (
            "How wolves coordinate and "
            "communicate within a pack."
        ),
        "expected_subject": "wolf",
        "expected_category": "animal",
    },
    {
        "title": "Canis lupus ecology",
        "body": (
            "The ecology and behavior "
            "of Canis lupus."
        ),
        "expected_subject": "wolf",
        "expected_category": "animal",
    },
    {
        "title": "Domestic dogs",
        "body": (
            "Understanding dogs as "
            "domestic companion animals."
        ),
        "expected_subject": "dog",
        "expected_category": "animal",
    },
    {
        "title": "Dog training",
        "body": (
            "Practical behavior and "
            "training principles for dogs."
        ),
        "expected_subject": "dog",
        "expected_category": "animal",
    },
    {
        "title": "Brown bear habitat",
        "body": (
            "Brown bears in forests "
            "and mountain ecosystems."
        ),
        "expected_subject": "bear",
        "expected_category": "animal",
    },
    {
        "title": "Bear behavior",
        "body": (
            "Feeding and seasonal "
            "behavior of wild bears."
        ),
        "expected_subject": "bear",
        "expected_category": "animal",
    },
    {
        "title": "Wild deer",
        "body": (
            "Deer behavior in woodland "
            "and grassland environments."
        ),
        "expected_subject": "deer",
        "expected_category": "animal",
    },
    {
        "title": "Deer ecology",
        "body": (
            "Ecology, feeding, and "
            "movement patterns of deer."
        ),
        "expected_subject": "deer",
        "expected_category": "animal",
    },
]


def main():
    Base.metadata.create_all(
        bind=engine
    )

    if not MANIFEST.exists():
        raise RuntimeError(
            "Corpus manifest missing. "
            "Run python -m "
            "scripts.download_corpus first."
        )

    records = json.loads(
        MANIFEST.read_text()
    )

    db = SessionLocal()

    try:
        tenant = ensure_demo_tenant(db)

        for record in records:
            existing = (
                db.query(ImageAsset)
                .filter(
                    ImageAsset.tenant_id == tenant.id,
                    ImageAsset.filename
                    == record["filename"]
                )
                .first()
            )

            if existing:
                continue

            db.add(
                ImageAsset(
                    tenant_id=tenant.id,
                    filename=record["filename"],
                    path=record["path"],
                )
            )

        for payload in POSTS:
            existing = (
                db.query(Post)
                .filter(
                    Post.tenant_id == tenant.id,
                    Post.title
                    == payload["title"]
                )
                .first()
            )

            if not existing:
                db.add(
                    Post(
                        tenant_id=tenant.id,
                        **payload,
                    )
                )

        db.commit()

        print(
            "Images:",
            db.query(ImageAsset).count(),
        )
        print(
            "Posts:",
            db.query(Post).count(),
        )

    finally:
        db.close()


if __name__ == "__main__":
    main()
