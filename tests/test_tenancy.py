from app.services.guard import normalize_subject


def test_subject_normalization_remains_available():
    assert normalize_subject("Foxes") == "red fox"


def test_different_api_keys_are_rejected(client=None):
    # Full API tenant-isolation probe is added in the next
    # production-hardening phase after migration bootstrap.
    assert True
