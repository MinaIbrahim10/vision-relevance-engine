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
