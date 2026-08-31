from app.services.providers import (
    MockEmbeddingProvider,
    MockVisionProvider,
)


def test_mock_vision_detects_fox():
    metadata = MockVisionProvider().analyze(
        "/tmp/red_fox_01.jpg"
    )

    assert metadata.subject == "red fox"
    assert metadata.category == "animal"
    assert metadata.confidence > 0.9


def test_unknown_image_is_flaggable():
    metadata = MockVisionProvider().analyze(
        "/tmp/mystery.jpg"
    )

    assert metadata.confidence < 0.6


def test_semantic_aliases_are_close():
    provider = MockEmbeddingProvider()

    a = provider.embed("red fox")
    b = provider.embed("Vulpes vulpes")

    assert a == b
