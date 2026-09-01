# Vision Relevance Engine

A production-oriented AI image understanding and semantic content-matching engine.

The system analyzes image libraries, generates structured metadata, embeds image and article semantics, ranks relevant images, and applies a mismatch guard that refuses unsafe or low-confidence recommendations.

## Planned capabilities

### Core
- Structured vision classification with schema validation
- Low-confidence review flags
- Background batch processing with retries
- Semantic image/post embeddings
- Similarity ranking
- Explainable mismatch guard
- "No confident match" behavior
- Persistent image/post/suggestion/review models
- Human review API
- Per-call AI cost tracking
- Evaluation dataset and top-1 precision

### Extended
- Automatic alt-text generation
- Near-duplicate image detection
- Fallback image generation
- Human-in-the-loop agent QA
- Deterministic automated test suite
- Dockerized local environment
- CI

## Status

Initial design and repository setup.

**Measured evaluation:** 10/10 correct, top-1 precision **1.00** on the repository's 10-post bounded evaluation set.

## Production Architecture

### Multi-Tenant Isolation

The API is designed around explicit tenant isolation.

Each tenant has its own:

- images
- posts
- suggestions
- processing jobs
- AI usage records
- review data
- operational alerts

Requests are scoped using the `X-API-Key` header. API keys are stored as SHA-256 hashes rather than plaintext values.

The same filename may exist independently for different tenants through the composite `(tenant_id, filename)` uniqueness constraint.

Cross-tenant resources are never intentionally included in matching or listing queries.

### Database & Migrations

Persistence uses SQLAlchemy with Alembic migrations.

Create or upgrade the database with:

    python -m alembic upgrade head

The current schema includes:

- `tenants`
- `images`
- `posts`
- `suggestions`
- `background_jobs`
- `job_alerts`
- `ai_usage`

Indexes are included for tenant-scoped access, background-job status, image metadata, suggestions, and usage records.

SQLite is supported for the reproducible local demonstration. The architecture keeps database configuration behind `DATABASE_URL`.

### Background Processing

Image analysis is designed as a persisted background-job workflow instead of requiring long-running AI inference inside the HTTP request lifecycle.

Start the worker with:

    python -m app.worker

Process at most one queued job with:

    python -m app.worker --once

Processing jobs support:

- persisted job state
- tenant ownership
- idempotency keys
- bounded retries
- progress tracking
- persistent failure information
- warning and error alerts
- AI budget checking

Typical states are:

    queued -> running -> completed

or, after a provider failure:

    queued -> running -> retry -> running -> failed

### Idempotency

Background jobs accept an `Idempotency-Key`.

Submitting the same key again for the same tenant returns the existing job instead of creating duplicate work.

### AI Cost Tracking

Every vision and embedding operation can be recorded in `ai_usage`.

Recorded fields include:

- tenant
- operation
- provider
- model
- units
- estimated cost

The local Ollama pipeline currently records `$0` provider cost while still preserving per-call attribution.

A configurable budget guard prevents new AI processing after the configured tenant budget is reached.

### Real AI Pipeline

The measured local pipeline uses:

- Vision: `llava:latest` through Ollama
- Embeddings: `bge-m3:latest` through Ollama
- Embedding size: 1024 dimensions
- Semantic ranking: cosine similarity
- Deterministic mismatch guard
- Human-review workflow

The repository contains a reproducible 40-image Wikimedia Commons corpus covering:

- red fox
- wolf
- dog
- bear
- deer

The bounded evaluation contains 10 labeled article/post examples.

Measured result:

    10 / 10 correct top-1 matches
    Top-1 precision: 1.00

This is explicitly a result on the repository's bounded evaluation set and is not presented as general model accuracy.

### Threshold Calibration

The semantic acceptance threshold was measured rather than selected solely to maximize the evaluation score.

Observed calibration values:

    Minimum best-positive similarity: 0.494570
    Maximum unrelated-negative similarity: 0.399605
    Midpoint: 0.447087
    Operational threshold: 0.45

This provides separation between the weakest tested correct match and the strongest tested unrelated match.

### Mismatch Safety Guard

Semantic similarity alone is not trusted.

A candidate must also satisfy deterministic checks for:

- vision confidence
- expected subject
- semantic category
- minimum similarity

For example, even a high-similarity wolf image is rejected for an article explicitly requiring a red fox.

When no candidate passes the guard, the system returns a safe `no confident match` result rather than forcing an image.

### Review Workflow

Suggestions can be inspected and explicitly:

- approved
- rejected
- annotated with reviewer notes

Low-confidence vision results are flagged for review.

### Reproducible Evaluation

Download the image corpus with:

    python -m scripts.download_corpus

Seed the database with:

    python -m scripts.seed

Process the corpus with Ollama:

    VISION_PROVIDER=ollama \
    OLLAMA_VISION_MODEL=llava:latest \
    EMBEDDING_PROVIDER=ollama \
    EMBEDDING_MODEL=bge-m3:latest \
    python -m scripts.process_images

Run the evaluation with:

    EMBEDDING_PROVIDER=ollama \
    EMBEDDING_MODEL=bge-m3:latest \
    python -m scripts.evaluate

Run threshold calibration with:

    EMBEDDING_PROVIDER=ollama \
    EMBEDDING_MODEL=bge-m3:latest \
    python -m scripts.calibrate_threshold

Run the automated test suite with:

    python -m pytest -q

### Evidence

Measured outputs, acceptance probes, threshold calibration, limitations, and implementation evidence are documented in:

- `EVIDENCE.md`
- `BUILDLOG.md`
- `DESIGN.md`
- `data/corpus_manifest.json`

The project intentionally separates measured results from assumptions and does not report unexecuted evaluations as evidence.

## Human-in-the-Loop QA Agent

Uncertain or high-impact suggestions can be sent through a QA agent before
a human reviewer makes the final decision.

Run QA for a suggestion:

    POST /api/v1/suggestions/{suggestion_id}/qa

Retrieve the persisted QA recommendation:

    GET /api/v1/suggestions/{suggestion_id}/qa

The agent examines:

- deterministic mismatch-guard status
- semantic similarity
- calibrated similarity threshold
- vision confidence
- low-confidence review flags
- expected and detected subjects

Possible recommendations are:

- `approve`
- `reject`
- `review`

The QA agent never writes the final human decision. A reviewer still uses
the review workflow to approve or reject the suggestion.

## Docker

Build and start the API and persistent background worker:

    docker compose up --build

The API is exposed at:

    http://localhost:8000

Health check:

    GET /health

The local Docker configuration connects to Ollama running on the host at
`host.docker.internal:11434`.

Both API and worker use the same persisted database volume.

## Continuous Integration

GitHub Actions runs on every push to `main` and on pull requests.

CI verifies:

- Python 3.14 dependency installation
- Python compilation
- complete pytest suite
- Alembic migrations on a fresh database
- presence of all required persistence tables

No AI API secret or Ollama model is required by CI because model-dependent
tests use deterministic providers.
