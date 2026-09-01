from pathlib import Path

from PIL import Image


def average_hash(
    image_path: str,
    hash_size: int = 8,
) -> str:
    path = Path(image_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Image does not exist: {image_path}"
        )

    with Image.open(path) as image:
        image = (
            image.convert("L")
            .resize((hash_size, hash_size))
        )

        if hasattr(
            image,
            "get_flattened_data",
        ):
            pixels = list(
                image.get_flattened_data()
            )
        else:
            pixels = list(
                image.getdata()
            )

    mean = sum(pixels) / len(pixels)

    bits = "".join(
        "1" if pixel >= mean else "0"
        for pixel in pixels
    )

    width = hash_size * hash_size // 4
    return f"{int(bits, 2):0{width}x}"


def hamming_distance(
    left: str,
    right: str,
) -> int:
    return (
        int(left, 16)
        ^ int(right, 16)
    ).bit_count()


def duplicate_similarity(
    left_hash: str,
    right_hash: str,
) -> float:
    bits = max(
        len(left_hash),
        len(right_hash),
    ) * 4

    distance = hamming_distance(
        left_hash,
        right_hash,
    )

    return max(
        0.0,
        1.0 - distance / bits,
    )


def near_duplicate(
    left_path: str,
    right_path: str,
    threshold: float = 0.94,
) -> bool:
    left_hash = average_hash(
        left_path
    )
    right_hash = average_hash(
        right_path
    )

    return (
        duplicate_similarity(
            left_hash,
            right_hash,
        )
        >= threshold
    )
