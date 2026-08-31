from dataclasses import dataclass

from app.config import get_settings


@dataclass
class GuardDecision:
    accepted: bool
    reason: str


def normalize_subject(value: str | None) -> str:
    if not value:
        return ""

    value = value.lower().strip()

    aliases = {
        "fox": "red fox",
        "red foxes": "red fox",
        "vulpes vulpes": "red fox",
        "wolves": "wolf",
        "canis lupus": "wolf",
        "dogs": "dog",
    }

    return aliases.get(value, value)


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

    if (
        expected_category
        and image_category
        and expected_category.lower() != image_category.lower()
    ):
        return GuardDecision(
            False,
            (
                "Category mismatch: expected "
                f"{expected_category}, detected {image_category}."
            ),
        )

    expected = normalize_subject(expected_subject)
    detected = normalize_subject(image_subject)

    if expected and detected and expected != detected:
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
