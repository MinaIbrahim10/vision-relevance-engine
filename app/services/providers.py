import base64
import hashlib
import json
import re
from abc import ABC, abstractmethod
from pathlib import Path

import httpx
import numpy as np

from app.config import get_settings
from app.schemas import VisionMetadata


CANONICAL_TERMS = {
    "vulpes vulpes": "red fox",
    "fox": "red fox",
    "red foxes": "red fox",
    "wolves": "wolf",
    "canis lupus": "wolf",
    "dogs": "dog",
    "canine pet": "dog",
    "bears": "bear",
    "deer": "deer",
}


def canonicalize(text: str) -> str:
    value = text.lower()

    for source, target in CANONICAL_TERMS.items():
        value = value.replace(source, target)

    return re.sub(r"[^a-z0-9 ]+", " ", value)


class VisionProvider(ABC):
    name: str
    model: str

    @abstractmethod
    def analyze(self, image_path: str) -> VisionMetadata:
        raise NotImplementedError


class MockVisionProvider(VisionProvider):
    name = "mock"
    model = "deterministic-test-provider"

    def analyze(self, image_path: str) -> VisionMetadata:
        filename = Path(image_path).name.lower()

        mappings = {
            "fox": (
                "red fox",
                "animal",
                ["orange fur", "wild", "forest"],
            ),
            "wolf": (
                "wolf",
                "animal",
                ["gray fur", "wild", "forest"],
            ),
            "dog": (
                "dog",
                "animal",
                ["domestic", "pet"],
            ),
            "bear": (
                "bear",
                "animal",
                ["large", "wild"],
            ),
            "deer": (
                "deer",
                "animal",
                ["antlers", "wild"],
            ),
        }

        for key, (subject, category, attributes) in mappings.items():
            if key in filename:
                return VisionMetadata(
                    subject=subject,
                    category=category,
                    attributes=attributes,
                    caption=f"A {subject} in a natural environment",
                    confidence=0.95,
                )

        return VisionMetadata(
            subject="unknown",
            category="unknown",
            attributes=[],
            caption="Uncertain image content",
            confidence=0.35,
        )


class OllamaVisionProvider(VisionProvider):
    name = "ollama"

    def __init__(self):
        settings = get_settings()
        self.model = settings.ollama_vision_model
        self.base_url = settings.ollama_base_url.rstrip("/")

    def analyze(self, image_path: str) -> VisionMetadata:
        image_bytes = Path(image_path).read_bytes()
        encoded = base64.b64encode(image_bytes).decode()

        prompt = """
Analyze this image and return ONLY JSON with:
{
  "subject": string,
  "category": string,
  "attributes": [string],
  "caption": string,
  "confidence": number from 0 to 1
}
Be specific about animal species when possible.
"""

        payload = {
            "model": self.model,
            "stream": False,
            "format": "json",
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [encoded],
                }
            ],
        }

        response = httpx.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=120,
        )
        response.raise_for_status()

        content = response.json()["message"]["content"].strip()

        if content.startswith("```"):
            content = re.sub(
                r"^```(?:json)?|```$",
                "",
                content,
                flags=re.MULTILINE,
            ).strip()

        return VisionMetadata.model_validate_json(content)


class EmbeddingProvider(ABC):
    name: str
    model: str

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        raise NotImplementedError


class MockEmbeddingProvider(EmbeddingProvider):
    name = "mock"
    model = "semantic-hash-128"

    def embed(self, text: str) -> list[float]:
        text = canonicalize(text)
        vector = np.zeros(128, dtype=np.float64)

        tokens = text.split()

        for token in tokens:
            digest = hashlib.sha256(token.encode()).digest()
            index = int.from_bytes(digest[:4], "big") % len(vector)
            vector[index] += 1.0

        norm = np.linalg.norm(vector)

        if norm:
            vector /= norm

        return vector.tolist()


class OllamaEmbeddingProvider(EmbeddingProvider):
    name = "ollama"

    def __init__(self):
        settings = get_settings()
        self.model = settings.embedding_model
        self.base_url = settings.ollama_base_url.rstrip("/")

    def embed(self, text: str) -> list[float]:
        response = httpx.post(
            f"{self.base_url}/api/embed",
            json={
                "model": self.model,
                "input": canonicalize(text),
            },
            timeout=120,
        )
        response.raise_for_status()

        return response.json()["embeddings"][0]


def get_vision_provider() -> VisionProvider:
    provider = get_settings().vision_provider.lower()

    if provider == "ollama":
        return OllamaVisionProvider()

    return MockVisionProvider()


def get_embedding_provider() -> EmbeddingProvider:
    provider = get_settings().embedding_provider.lower()

    if provider == "ollama":
        return OllamaEmbeddingProvider()

    return MockEmbeddingProvider()
