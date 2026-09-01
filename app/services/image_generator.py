from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

import httpx
from PIL import Image, ImageDraw

from app.config import get_settings


@dataclass
class GeneratedImage:
    provider: str
    model: str
    path: str
    prompt: str
    cost_usd: float


class ImageGenerator(ABC):
    name: str
    model: str

    @abstractmethod
    def generate(
        self,
        *,
        prompt: str,
        output_path: str,
    ) -> GeneratedImage:
        raise NotImplementedError


class MockImageGenerator(ImageGenerator):
    """
    Deterministic test provider.

    It validates the fallback workflow without claiming
    to be an AI-generated production image.
    """

    name = "mock"
    model = "deterministic-fixture"

    def generate(
        self,
        *,
        prompt: str,
        output_path: str,
    ) -> GeneratedImage:
        path = Path(output_path)
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        image = Image.new(
            "RGB",
            (768, 512),
            "white",
        )

        draw = ImageDraw.Draw(image)

        draw.text(
            (30, 30),
            "Fallback image fixture",
            fill="black",
        )

        draw.text(
            (30, 80),
            prompt[:180],
            fill="black",
        )

        image.save(
            path,
            format="JPEG",
            quality=90,
        )

        return GeneratedImage(
            provider=self.name,
            model=self.model,
            path=str(path),
            prompt=prompt,
            cost_usd=0.0,
        )


class PollinationsImageGenerator(
    ImageGenerator
):
    name = "pollinations"

    def __init__(self):
        settings = get_settings()

        if not settings.pollinations_api_key:
            raise RuntimeError(
                "POLLINATIONS_API_KEY is required "
                "for live fallback image generation."
            )

        self.api_key = (
            settings.pollinations_api_key
        )

        self.base_url = (
            settings.pollinations_base_url
            .rstrip("/")
        )

        self.model = (
            settings.pollinations_image_model
        )

    def generate(
        self,
        *,
        prompt: str,
        output_path: str,
    ) -> GeneratedImage:
        encoded_prompt = quote(
            prompt,
            safe="",
        )

        url = (
            f"{self.base_url}/image/"
            f"{encoded_prompt}"
        )

        response = httpx.get(
            url,
            params={
                "model": self.model,
            },
            headers={
                "Authorization":
                f"Bearer {self.api_key}",
            },
            timeout=180,
            follow_redirects=True,
        )

        response.raise_for_status()

        content_type = (
            response.headers.get(
                "content-type",
                "",
            )
        )

        if not content_type.startswith(
            "image/"
        ):
            raise RuntimeError(
                "Image provider returned "
                f"unexpected content type: "
                f"{content_type}"
            )

        path = Path(output_path)

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        path.write_bytes(
            response.content
        )

        # Validate that returned bytes are a real image.
        with Image.open(path) as image:
            image.verify()

        return GeneratedImage(
            provider=self.name,
            model=self.model,
            path=str(path),
            prompt=prompt,
            cost_usd=0.0,
        )


def get_image_generator() -> ImageGenerator:
    provider = (
        get_settings()
        .image_generation_provider
        .lower()
    )

    if provider == "mock":
        return MockImageGenerator()

    if provider == "pollinations":
        return PollinationsImageGenerator()

    raise RuntimeError(
        "Fallback image generation is disabled. "
        "Set IMAGE_GENERATION_PROVIDER to "
        "'pollinations' or 'mock'."
    )
