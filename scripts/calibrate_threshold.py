import json
from pathlib import Path

from app.db import SessionLocal
from app.models import ImageAsset, Post
from app.services.guard import normalize_subject
from app.services.matcher import cosine_similarity
from app.services.providers import get_embedding_provider


NEGATIVE_POSTS = [
    "Python database migration strategy using Alembic and PostgreSQL.",
    "Quarterly stock market earnings and interest rate analysis.",
    "A pasta recipe with tomato sauce, garlic, and parmesan cheese.",
    "City subway schedules and public transportation infrastructure.",
    "Cloud API billing, authentication, and usage metering architecture.",
]


def main():
    db = SessionLocal()
    embedder = get_embedding_provider()

    try:
        images = db.query(ImageAsset).all()
        posts = db.query(Post).all()

        positive_best = []

        print("=== Positive calibration ===")

        for post in posts:
            post_vec = embedder.embed(
                f"{post.title}\n{post.body}"
            )

            expected = normalize_subject(
                post.expected_subject
            )

            candidates = []

            for image in images:
                if not image.embedding_json:
                    continue

                detected = normalize_subject(
                    image.subject
                )

                if detected != expected:
                    continue

                score = cosine_similarity(
                    post_vec,
                    json.loads(
                        image.embedding_json
                    ),
                )

                candidates.append(
                    (
                        score,
                        image.filename,
                        image.subject,
                    )
                )

            candidates.sort(
                reverse=True,
                key=lambda x: x[0],
            )

            if not candidates:
                print(
                    f"{post.title}: "
                    "NO CORRECT-SUBJECT CANDIDATE"
                )
                continue

            best = candidates[0]

            positive_best.append(
                best[0]
            )

            print(
                f"{post.title:28} "
                f"best_positive={best[0]:.6f} "
                f"image={best[1]} "
                f"subject={best[2]}"
            )

        print("\n=== Unrelated no-match calibration ===")

        negative_best = []

        for text in NEGATIVE_POSTS:
            vector = embedder.embed(text)

            scored = []

            for image in images:
                if not image.embedding_json:
                    continue

                score = cosine_similarity(
                    vector,
                    json.loads(
                        image.embedding_json
                    ),
                )

                scored.append(
                    (
                        score,
                        image.filename,
                    )
                )

            scored.sort(reverse=True)

            best = scored[0]

            negative_best.append(
                best[0]
            )

            print(
                f"{text[:42]:42} "
                f"best_negative={best[0]:.6f} "
                f"image={best[1]}"
            )

        min_positive = min(positive_best)
        max_negative = max(negative_best)

        print("\n=== Calibration summary ===")
        print(
            f"minimum best-positive: "
            f"{min_positive:.6f}"
        )
        print(
            f"maximum unrelated-negative: "
            f"{max_negative:.6f}"
        )

        if max_negative < min_positive:
            recommended = (
                max_negative
                + min_positive
            ) / 2

            print(
                "SEPARATION: YES"
            )
            print(
                f"recommended threshold: "
                f"{recommended:.6f}"
            )
        else:
            print(
                "SEPARATION: NO"
            )
            print(
                "Do not lower the threshold "
                "without improving embeddings "
                "or calibration data."
            )

    finally:
        db.close()


if __name__ == "__main__":
    main()
