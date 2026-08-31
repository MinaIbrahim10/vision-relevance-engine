from app.db import SessionLocal
from app.models import ImageAsset
from app.services.pipeline import (
    process_single_image,
)


def main():
    db = SessionLocal()

    try:
        images = (
            db.query(ImageAsset)
            .filter(
                ImageAsset.processed.is_(False)
            )
            .all()
        )

        total = len(images)

        for index, image in enumerate(
            images,
            start=1,
        ):
            process_single_image(
                db,
                image,
            )

            print(
                f"{index}/{total} "
                f"{image.filename}: "
                f"{image.subject} "
                f"({image.confidence:.2f})"
            )

        print(
            f"Processed {total} images."
        )

    finally:
        db.close()


if __name__ == "__main__":
    main()
