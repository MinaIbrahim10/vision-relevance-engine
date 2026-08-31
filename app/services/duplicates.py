from pathlib import Path

from PIL import Image


def average_hash(
    image_path: str,
    hash_size: int = 8,
) -> str:
    with Image.open(image_path) as image:
        image = (
            image.convert("L")
            .resize((hash_size, hash_size))
        )

        pixels = list(
            image.get_flattened_data()
            if hasattr(image, "get_flattened_data")
            else image.getdata()
        )

    mean = sum(pixels) / len(pixels)

    bits = "".join(
        "1" if pixel >= mean else "0"
        for pixel in pixels
    )

    return f"{int(bits, 2):0{hash_size * hash_size // 4}x}"


def hamming_distance(
    left: str,
    right: str,
) -> int:
    return (
        int(left, 16)
        ^ int(right, 16)
    ).bit_count()


def near_duplicate(
    left_path: str,
    right_path: str,
    max_distance: int = 5,
) -> bool:
    return (
        hamming_distance(
            average_hash(left_path),
            average_hash(right_path),
        )
        <= max_distance
    )
