from app.models import ImageAsset


def generate_alt_text(
    image: ImageAsset,
) -> str:
    """
    Produce concise accessible alt text from the
    structured vision metadata already generated
    for the image.
    """

    if image.alt_text:
        return image.alt_text.strip()

    if image.caption:
        return image.caption.strip()

    subject = (
        image.subject.strip()
        if image.subject
        else "image"
    )

    attributes = []

    if image.attributes_json:
        import json

        try:
            values = json.loads(
                image.attributes_json
            )

            attributes = [
                str(value).strip()
                for value in values[:3]
                if str(value).strip()
            ]
        except (
            json.JSONDecodeError,
            TypeError,
        ):
            pass

    if attributes:
        return (
            f"{subject}: "
            + ", ".join(attributes)
        )

    return subject
