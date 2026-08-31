import json
import time
from pathlib import Path

import httpx
from PIL import Image


API = "https://commons.wikimedia.org/w/api.php"

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "data" / "corpus"
MANIFEST = ROOT / "data" / "corpus_manifest.json"

CORPUS.mkdir(parents=True, exist_ok=True)

TARGETS = {
    "fox": {
        "queries": [
            "red fox Vulpes vulpes photograph",
            "red fox wildlife",
        ],
        "subject": "red fox",
        "category": "animal",
    },
    "wolf": {
        "queries": [
            "gray wolf Canis lupus photograph",
            "grey wolf wildlife",
        ],
        "subject": "wolf",
        "category": "animal",
    },
    "dog": {
        "queries": [
            "domestic dog photograph",
            "dog animal portrait",
        ],
        "subject": "dog",
        "category": "animal",
    },
    "bear": {
        "queries": [
            "brown bear wildlife photograph",
            "brown bear animal",
        ],
        "subject": "bear",
        "category": "animal",
    },
    "deer": {
        "queries": [
            "deer wildlife photograph",
            "deer animal portrait",
        ],
        "subject": "deer",
        "category": "animal",
    },
}

PER_CATEGORY = 8

HEADERS = {
    "User-Agent": (
        "VisionRelevanceEngine/0.1 "
        "(https://github.com/MinaIbrahim10/vision-relevance-engine)"
    )
}


def request_with_backoff(
    client: httpx.Client,
    url: str,
    **kwargs,
) -> httpx.Response:
    for attempt in range(6):
        response = client.get(url, **kwargs)

        if response.status_code not in {429, 502, 503, 504}:
            response.raise_for_status()
            return response

        retry_after = response.headers.get("Retry-After")

        try:
            delay = float(retry_after) if retry_after else 2 ** attempt
        except ValueError:
            delay = 2 ** attempt

        delay = min(max(delay, 2.0), 30.0)

        print(
            f"HTTP {response.status_code}; "
            f"waiting {delay:.1f}s "
            f"(attempt {attempt + 1}/6)"
        )
        time.sleep(delay)

    response.raise_for_status()
    return response


def search_commons(
    client: httpx.Client,
    query: str,
) -> list[dict]:
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

    response = request_with_backoff(
        client,
        API,
        params=params,
    )

    return list(
        response.json()
        .get("query", {})
        .get("pages", {})
        .values()
    )


def metadata_value(metadata: dict, key: str) -> str:
    value = metadata.get(key, {}).get("value", "")
    return value if isinstance(value, str) else ""


def collect_candidates(
    client: httpx.Client,
    queries: list[str],
) -> list[dict]:
    candidates = []
    seen_titles = set()

    for query in queries:
        pages = search_commons(client, query)

        for page in pages:
            title = page.get("title", "")

            if not title or title in seen_titles:
                continue

            seen_titles.add(title)
            candidates.append(page)

        time.sleep(2.0)

    return candidates


def download_category(
    client: httpx.Client,
    prefix: str,
    config: dict,
) -> list[dict]:
    records = []
    seen_urls = set()

    pages = collect_candidates(
        client,
        config["queries"],
    )

    for page in pages:
        if len(records) >= PER_CATEGORY:
            break

        infos = page.get("imageinfo") or []

        if not infos:
            continue

        info = infos[0]

        mime = info.get("mime", "")

        if mime not in {
            "image/jpeg",
            "image/png",
            "image/webp",
        }:
            continue

        # Important: use Wikimedia's generated thumbnail,
        # not the multi-megabyte original image.
        url = info.get("thumburl") or info.get("url")

        if not url or url in seen_urls:
            continue

        seen_urls.add(url)

        try:
            # Respect Wikimedia bandwidth/rate limits.
            time.sleep(1.25)

            response = request_with_backoff(
                client,
                url,
                timeout=60,
            )

            temp = CORPUS / "_download.tmp"
            temp.write_bytes(response.content)

            with Image.open(temp) as image:
                image.verify()

            with Image.open(temp) as image:
                image = image.convert("RGB")
                image.thumbnail((640, 640))

                filename = (
                    f"{prefix}_{len(records) + 1:02d}.jpg"
                )
                destination = CORPUS / filename

                image.save(
                    destination,
                    format="JPEG",
                    quality=88,
                    optimize=True,
                )

            temp.unlink(missing_ok=True)

            metadata = info.get("extmetadata") or {}

            records.append(
                {
                    "filename": filename,
                    "path": str(destination),
                    "subject": config["subject"],
                    "category": config["category"],
                    "source_title": page.get("title", ""),
                    "source_url": (
                        info.get("descriptionurl")
                        or info.get("url")
                        or url
                    ),
                    "license": (
                        metadata_value(
                            metadata,
                            "LicenseShortName",
                        )
                        or metadata_value(
                            metadata,
                            "UsageTerms",
                        )
                    ),
                    "artist": metadata_value(
                        metadata,
                        "Artist",
                    ),
                }
            )

            print(
                f"[{prefix}] "
                f"{len(records)}/{PER_CATEGORY} "
                f"{filename}"
            )

        except Exception as exc:
            print(
                f"[{prefix}] skipped "
                f"{page.get('title', 'unknown')}: {exc}"
            )

    if len(records) != PER_CATEGORY:
        raise RuntimeError(
            f"{prefix}: downloaded {len(records)} "
            f"of required {PER_CATEGORY} images."
        )

    return records


def main():
    for path in CORPUS.glob("*.jpg"):
        path.unlink()

    (CORPUS / "_download.tmp").unlink(
        missing_ok=True
    )
    MANIFEST.unlink(missing_ok=True)

    manifest = []

    with httpx.Client(
        headers=HEADERS,
        follow_redirects=True,
        timeout=60,
    ) as client:
        for prefix, config in TARGETS.items():
            print(f"\n=== {prefix.upper()} ===")

            records = download_category(
                client,
                prefix,
                config,
            )

            manifest.extend(records)

            # Small pause between categories.
            time.sleep(3.0)

    if len(manifest) != 40:
        raise RuntimeError(
            f"Expected 40 images, got {len(manifest)}."
        )

    MANIFEST.write_text(
        json.dumps(
            manifest,
            indent=2,
            ensure_ascii=False,
        )
    )

    print("\nCorpus complete.")
    print(f"Images: {len(manifest)}")
    print(f"Manifest: {MANIFEST}")


if __name__ == "__main__":
    main()
