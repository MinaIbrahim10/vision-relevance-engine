import json
import time
from pathlib import Path

import httpx
from PIL import Image

from app.db import SessionLocal
from app.models import AIUsage, ImageAsset
from app.services.guard import normalize_subject
from app.services.providers import (
    get_embedding_provider,
    get_vision_provider,
)


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "data" / "corpus"
MANIFEST_PATH = ROOT / "data" / "corpus_manifest.json"

API = "https://commons.wikimedia.org/w/api.php"

HEADERS = {
    "User-Agent": (
        "VisionRelevanceEngine/0.1 "
        "(https://github.com/MinaIbrahim10/vision-relevance-engine)"
    )
}

REPAIRS = {
    "wolf_08.jpg": {
        "subject": "wolf",
        "queries": [
            "Canis lupus gray wolf photograph",
            "grey wolf wildlife Canis lupus",
        ],
    },
    "dog_01.jpg": {
        "subject": "dog",
        "queries": [
            "domestic dog Canis familiaris photograph",
            "pet dog portrait photograph",
        ],
    },
    "bear_06.jpg": {
        "subject": "bear",
        "queries": [
            "Ursus arctos brown bear photograph",
            "brown bear wildlife photograph",
        ],
    },
    "deer_01.jpg": {
        "subject": "deer",
        "queries": [
            "deer Cervidae animal photograph",
            "wild deer wildlife photograph",
        ],
    },
    "deer_02.jpg": {
        "subject": "deer",
        "queries": [
            "red deer Cervus elaphus photograph",
            "deer Cervidae wildlife",
        ],
    },
    "deer_03.jpg": {
        "subject": "deer",
        "queries": [
            "roe deer Capreolus photograph",
            "deer animal close up photograph",
        ],
    },
    "deer_04.jpg": {
        "subject": "deer",
        "queries": [
            "white tailed deer photograph",
            "deer wildlife animal photograph",
        ],
    },
}


def search(client, query):
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": 6,
        "gsrlimit": 30,
        "prop": "imageinfo",
        "iiprop": "url|mime|extmetadata",
        "iiurlwidth": 640,
    }

    for attempt in range(5):
        response = client.get(
            API,
            params=params,
            timeout=60,
        )

        if response.status_code == 429:
            delay = min(2 ** attempt, 20)
            print(f"429 from Wikimedia; waiting {delay}s")
            time.sleep(delay)
            continue

        response.raise_for_status()

        return list(
            response.json()
            .get("query", {})
            .get("pages", {})
            .values()
        )

    raise RuntimeError("Wikimedia search repeatedly rate-limited.")


def meta_value(metadata, key):
    return metadata.get(key, {}).get("value", "")


def download_candidate(client, page, destination):
    infos = page.get("imageinfo") or []

    if not infos:
        return None

    info = infos[0]

    if info.get("mime") not in {
        "image/jpeg",
        "image/png",
        "image/webp",
    }:
        return None

    url = info.get("thumburl") or info.get("url")

    if not url:
        return None

    time.sleep(1.0)

    response = client.get(
        url,
        timeout=60,
    )

    if response.status_code == 429:
        return None

    response.raise_for_status()

    temp = CORPUS / "_candidate.tmp"
    temp.write_bytes(response.content)

    try:
        with Image.open(temp) as img:
            img.verify()

        with Image.open(temp) as img:
            img = img.convert("RGB")
            img.thumbnail((640, 640))
            img.save(
                destination,
                format="JPEG",
                quality=88,
                optimize=True,
            )
    finally:
        temp.unlink(missing_ok=True)

    return info


def main():
    manifest = json.loads(
        MANIFEST_PATH.read_text()
    )

    by_filename = {
        row["filename"]: row
        for row in manifest
    }

    used_urls = {
        row["source_url"]
        for row in manifest
        if row.get("source_url")
    }

    vision = get_vision_provider()
    embedder = get_embedding_provider()

    print(
        f"Vision: {vision.name}/{vision.model}"
    )
    print(
        f"Embeddings: {embedder.name}/{embedder.model}"
    )

    db = SessionLocal()

    try:
        with httpx.Client(
            headers=HEADERS,
            follow_redirects=True,
        ) as client:

            for filename, config in REPAIRS.items():
                expected = normalize_subject(
                    config["subject"]
                )

                destination = CORPUS / filename
                accepted = False

                print(
                    f"\n=== Repairing {filename} "
                    f"(need {expected}) ==="
                )

                for query in config["queries"]:
                    pages = search(
                        client,
                        query,
                    )

                    for page in pages:
                        infos = page.get(
                            "imageinfo"
                        ) or []

                        if not infos:
                            continue

                        info = infos[0]

                        source_url = (
                            info.get("descriptionurl")
                            or info.get("url")
                        )

                        if source_url in used_urls:
                            continue

                        try:
                            downloaded_info = (
                                download_candidate(
                                    client,
                                    page,
                                    destination,
                                )
                            )

                            if not downloaded_info:
                                continue

                            metadata = vision.analyze(
                                str(destination)
                            )

                            detected = normalize_subject(
                                metadata.subject
                            )

                            print(
                                f"candidate: "
                                f"{metadata.subject} "
                                f"confidence="
                                f"{metadata.confidence:.2f}"
                            )

                            if (
                                detected != expected
                                or metadata.confidence < 0.65
                            ):
                                destination.unlink(
                                    missing_ok=True
                                )
                                continue

                            # Accepted by real vision model.
                            text = (
                                f"{metadata.subject}. "
                                f"{metadata.category}. "
                                f"{metadata.caption}. "
                                f"{' '.join(metadata.attributes)}"
                            )

                            embedding = (
                                embedder.embed(text)
                            )

                            image = (
                                db.query(ImageAsset)
                                .filter(
                                    ImageAsset.filename
                                    == filename
                                )
                                .one()
                            )

                            image.subject = metadata.subject
                            image.category = metadata.category
                            image.attributes_json = json.dumps(
                                metadata.attributes
                            )
                            image.caption = metadata.caption
                            image.confidence = (
                                metadata.confidence
                            )
                            image.alt_text = (
                                metadata.caption
                            )
                            image.embedding_json = json.dumps(
                                embedding
                            )
                            image.needs_review = (
                                metadata.confidence < 0.60
                            )
                            image.processed = True

                            db.add(image)

                            db.add(
                                AIUsage(
                                    tenant_id=image.tenant_id,
                                    operation="vision",
                                    provider=vision.name,
                                    model=vision.model,
                                    units=1,
                                    cost_usd=0.0,
                                )
                            )

                            db.add(
                                AIUsage(
                                    tenant_id=image.tenant_id,
                                    operation="embedding",
                                    provider=embedder.name,
                                    model=embedder.model,
                                    units=1,
                                    cost_usd=0.0,
                                )
                            )

                            db.commit()

                            ext = (
                                downloaded_info
                                .get("extmetadata")
                                or {}
                            )

                            record = by_filename[
                                filename
                            ]

                            record["subject"] = (
                                config["subject"]
                            )
                            record["category"] = "animal"
                            record["source_title"] = (
                                page.get(
                                    "title",
                                    "",
                                )
                            )
                            record["source_url"] = (
                                source_url
                            )
                            record["license"] = (
                                meta_value(
                                    ext,
                                    "LicenseShortName",
                                )
                                or meta_value(
                                    ext,
                                    "UsageTerms",
                                )
                            )
                            record["artist"] = (
                                meta_value(
                                    ext,
                                    "Artist",
                                )
                            )

                            used_urls.add(
                                source_url
                            )

                            print(
                                f"ACCEPTED {filename}: "
                                f"{metadata.subject}"
                            )

                            accepted = True
                            break

                        except Exception as exc:
                            print(
                                "candidate skipped:",
                                exc,
                            )
                            destination.unlink(
                                missing_ok=True
                            )

                    if accepted:
                        break

                if not accepted:
                    raise RuntimeError(
                        f"Could not find valid "
                        f"replacement for {filename}"
                    )

                time.sleep(1.5)

        MANIFEST_PATH.write_text(
            json.dumps(
                manifest,
                indent=2,
                ensure_ascii=False,
            )
        )

    finally:
        db.close()

    print("\nAll contaminated images repaired.")


if __name__ == "__main__":
    main()
