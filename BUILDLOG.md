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
