from app.services.guard import evaluate_candidate


def test_fox_candidate_is_accepted(monkeypatch):
    decision = evaluate_candidate(
        expected_subject="red fox",
        expected_category="animal",
        image_subject="red fox",
        image_category="animal",
        confidence=0.95,
        similarity=0.90,
    )

    assert decision.accepted is True


def test_wolf_is_rejected_for_fox_post():
    decision = evaluate_candidate(
        expected_subject="red fox",
        expected_category="animal",
        image_subject="wolf",
        image_category="animal",
        confidence=0.99,
        similarity=0.92,
    )

    assert decision.accepted is False
    assert "Subject mismatch" in decision.reason


def test_low_confidence_is_rejected():
    decision = evaluate_candidate(
        expected_subject="red fox",
        expected_category="animal",
        image_subject="red fox",
        image_category="animal",
        confidence=0.30,
        similarity=0.99,
    )

    assert decision.accepted is False
    assert "confidence" in decision.reason.lower()


def test_low_similarity_is_rejected():
    decision = evaluate_candidate(
        expected_subject="red fox",
        expected_category="animal",
        image_subject="red fox",
        image_category="animal",
        confidence=0.95,
        similarity=0.10,
    )

    assert decision.accepted is False
    assert "similarity" in decision.reason.lower()


def test_wildlife_normalizes_to_animal():
    from app.services.guard import normalize_category

    assert (
        normalize_category(
            "Wildlife",
            "Fox",
        )
        == "animal"
    )


def test_fox_normalizes_to_red_fox():
    from app.services.guard import normalize_subject

    assert normalize_subject("Fox") == "red fox"
    assert normalize_subject("Vulpes vulpes") == "red fox"


def test_plural_fox_normalizes_to_red_fox():
    from app.services.guard import normalize_subject

    assert normalize_subject("Foxes") == "red fox"
