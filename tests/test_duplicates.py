from pathlib import Path

from PIL import Image

from app.services.duplicates import (
    average_hash,
    hamming_distance,
    near_duplicate,
)


def test_identical_images_are_duplicates(
    tmp_path: Path,
):
    left = tmp_path / "left.png"
    right = tmp_path / "right.png"

    image = Image.new(
        "RGB",
        (64, 64),
        "red",
    )

    image.save(left)
    image.save(right)

    assert (
        average_hash(str(left))
        == average_hash(str(right))
    )

    assert near_duplicate(
        str(left),
        str(right),
    )


def test_hash_distance_zero_for_same_hash():
    value = "ffffffffffffffff"

    assert (
        hamming_distance(
            value,
            value,
        )
        == 0
    )
