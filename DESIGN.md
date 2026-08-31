# Design

## Problem

Image recommendation systems can return visually or semantically plausible but incorrect images. This project prioritizes safe rejection over confident-looking mistakes.

## Main flow

Images
  -> background vision job
  -> validated metadata
  -> embeddings
  -> vector ranking

Posts
  -> embeddings
  -> vector ranking
  -> mismatch guard
  -> recommendation OR safe rejection
  -> human review

## Main entities

- Image
- ImageMetadata
- ImageEmbedding
- Post
- PostEmbedding
- Suggestion
- Review
- AIUsage
- BackgroundJob

## API surface

- Images
- Posts
- Matching
- Reviews
- Evaluation
- Jobs
- Health

## Non-goal

This is not a general-purpose image search engine or full CMS.
