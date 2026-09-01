# Build Log

## Session 1 — Repository and architecture

### AI assistance
AI was used to help translate the capstone requirements into an implementation plan and repository structure.

### Human decisions
- Repository name intentionally avoids program-specific branding.
- Python + FastAPI selected for the backend.
- Architecture will support both cloud and local AI providers.
- Reliability and deterministic evaluation will take priority over UI polish.
- All optional stretch capabilities are included in scope.

### Verification
Implementation claims will only be added after they are actually built and tested.

## Session 2 — Python 3.14 dependency correction

### What failed

The initial dependency set pinned NumPy 2.2.6 while the development
environment uses Python 3.14. pip could not use a compatible wheel and
attempted a source build, which failed in NumPy's SIMD C++ compilation.

Because dependency installation stopped early, invoking the globally
available `pytest` also caused test collection to use the wrong runtime
environment and fail to resolve the local `app` package.

### AI mistake

AI assistance originally selected an outdated NumPy pin without first
checking Python 3.14 wheel compatibility.

### Human-visible correction

- Updated NumPy to 2.5.2, which provides CPython 3.14 wheels.
- Added an explicit pytest Python path configuration.
- Standardized test execution on `python -m pytest` so tests use the
  active virtual environment.
- Preserved the failed development commit rather than rewriting history.

This correction is intentionally documented because the build log tracks
where AI assistance was wrong and how the implementation was verified.

## Session 3 — Corpus, evaluation, and duplicate detection

### Added

- Reproducible Wikimedia Commons image downloader.
- Five semantic image groups with eight images each.
- Ten-post labeled evaluation set.
- Deterministic processing CLI.
- Top-1 precision evaluator and API endpoint.
- Perceptual-hash near-duplicate detection as a stretch capability.

### Evidence policy

The final precision value will only be documented after an actual
processing and evaluation run. No metric is pre-written or assumed.

## Session 3 correction — Wikimedia throttling

The first corpus download attempted to fetch original Wikimedia Commons
files too aggressively. Wikimedia returned HTTP 429 responses and
explicitly recommended using thumbnail images instead.

Only five fox images were downloaded, so no corpus manifest was produced.
The subsequent zero-item evaluation was therefore invalid and is not
reported as a model quality result.

Correction:
- switched downloads to Wikimedia-generated 640px thumbnails;
- added HTTP 429/5xx retry with exponential backoff;
- added request throttling and pauses between categories;
- retained source URLs and license metadata in the corpus manifest;
- the phase is considered complete only if exactly 40 images are present.

## Session 4 — Real-model evaluation and threshold calibration

The full corpus was processed with Ollama LLaVA for vision metadata and
BGE-M3 for 1024-dimensional semantic embeddings.

The initial bounded evaluation scored 9/10 because the configured 0.55
similarity threshold rejected the correct dog candidate for the
"Dog training" post.

The threshold was not lowered arbitrarily. A calibration run measured:

- minimum best-positive similarity: 0.494570
- maximum unrelated-negative similarity: 0.399605
- midpoint: 0.447087

The operational threshold was set to 0.45, close to the measured midpoint
and still separated from both observed groups.

The corpus was also audited after vision inference. Seven genuinely
incorrect search-result images were replaced and revalidated with LLaVA;
plural "Foxes" normalization was corrected separately. The final corpus
audit reported zero expected-subject mismatches.

The reported evaluation metric is limited to this repository's bounded
40-image / 10-post evaluation set and is not claimed as general model
accuracy.

## Session 5 — Persistence and tenant architecture

Added Alembic migration infrastructure and tenant-aware persistence.

The schema now contains a tenant entity and tenant foreign keys across
images, posts, suggestions, jobs, and usage records. API operations are
being migrated to explicit tenant scoping so data belonging to one tenant
cannot be returned through another tenant context.

A fresh evaluator clone can create the database through Alembic rather
than relying on ORM create-all as the persistence contract.

## Session 6 — Tenant isolation and resilient workers

Production hardening was verified with executable tests rather than
placeholder assertions.

The test suite now covers:

- invalid API-key rejection;
- independent resources for two tenants using the same filename;
- cross-tenant post access returning 404;
- idempotent background-job creation;
- worker processing restricted to the owning tenant;
- bounded retry behavior;
- persistent warning and terminal error alerts.

This complements the Alembic migration and tenant-aware schema already
verified against a fresh database.

## Session 7 — Alt text and near-duplicate detection

Implemented two capstone stretch capabilities:

- automatic alt-text generation from structured vision metadata;
- near-duplicate image detection using perceptual hashes.

Both capabilities are exposed through tenant-scoped API endpoints and
covered by executable tests, including cross-tenant duplicate isolation.

## Session 8 — Human-in-the-loop QA agent

Implemented the uncertain-match QA stretch capability.

The QA agent:

- inspects deterministic guard results;
- checks the calibrated semantic-margin boundary;
- checks vision confidence and review flags;
- persists its recommendation and supporting signals;
- is idempotent per tenant and suggestion;
- never automatically converts its recommendation into a human decision.

This preserves a real human-in-the-loop boundary rather than presenting an
AI recommendation as final approval.

## Session 9 — Docker and continuous integration

Added reproducible production packaging and automated verification.

The Docker setup runs the API and persistent background worker separately
while sharing database storage. Local Ollama remains outside the containers
and is reached through the host gateway.

GitHub Actions now installs the project on Python 3.14, compiles the source,
runs the complete test suite, and applies all Alembic migrations against a
fresh database.

## Session 10 — Fallback image generation

Implemented provider-based fallback image generation.

The workflow is intentionally library-first: generation is allowed only
when the existing image matcher fails to produce a confident candidate.

Fallback images are persisted as tenant-owned assets, generation usage is
recorded, and every generated result is marked for human review.

The production provider integration is Pollinations. Tests use an offline
deterministic provider so CI does not require credentials or external
network access.

A live provider execution is not claimed until an authenticated smoke test
is run successfully.
