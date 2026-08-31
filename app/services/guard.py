from dataclasses import dataclass

from app.config import get_settings


@dataclass
class GuardDecision:
    accepted: bool
    reason: str


ANIMAL_SUBJECTS = {
    "red fox",
    "wolf",
    "dog",
    "bear",
    "deer",
}


def normalize_subject(value: str | None) -> str:
    if not value:
        return ""

    text = value.lower().strip()

    if (
        "vulpes vulpes" in text
        or "red fox" in text
        or text in {"fox", "foxes"}
    ):
        return "red fox"

    if "canis lupus" in text or "wolf" in text:
        return "wolf"

    if "dog" in text or "domestic canine" in text:
        return "dog"

    if "bear" in text:
        return "bear"

    if "deer" in text or "cervid" in text:
        return "deer"

    return text


def normalize_category(
    value: str | None,
    subject: str | None = None,
) -> str:
    normalized_subject = normalize_subject(subject)

    if normalized_subject in ANIMAL_SUBJECTS:
        return "animal"

    if not value:
        return ""

    text = value.lower().strip()

    if text in {
        "wildlife",
        "animal",
        "animals",
        "mammal",
        "mammals",
        "fauna",
        "wild animal",
    }:
        return "animal"

    return text


def evaluate_candidate(
    *,
    expected_subject: str | None,
    expected_category: str | None,
    image_subject: str | None,
    image_category: str | None,
    confidence: float | None,
    similarity: float,
) -> GuardDecision:
    settings = get_settings()

    if confidence is None or confidence < settings.min_vision_confidence:
        return GuardDecision(
            False,
            "Vision confidence below threshold.",
        )

    expected_subject_norm = normalize_subject(expected_subject)
    image_subject_norm = normalize_subject(image_subject)

    expected_category_norm = normalize_category(
        expected_category,
        expected_subject,
    )
    image_category_norm = normalize_category(
        image_category,
        image_subject,
    )

    if (
        expected_category_norm
        and image_category_norm
        and expected_category_norm != image_category_norm
    ):
        return GuardDecision(
            False,
            (
                "Category mismatch: expected "
                f"{expected_category}, detected {image_category}."
            ),
        )

    if (
        expected_subject_norm
        and image_subject_norm
        and expected_subject_norm != image_subject_norm
    ):
        return GuardDecision(
            False,
            (
                "Subject mismatch: expected "
                f"{expected_subject}, detected {image_subject}."
            ),
        )

    if similarity < settings.min_similarity_score:
        return GuardDecision(
            False,
            (
                "Semantic similarity below threshold "
                f"({similarity:.3f} < "
                f"{settings.min_similarity_score:.3f})."
            ),
        )

    return GuardDecision(
        True,
        "Candidate passed confidence, category, subject, and similarity guards.",
    )
