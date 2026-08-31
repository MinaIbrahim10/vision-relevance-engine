# Evaluation Data

The image corpus is downloaded reproducibly from Wikimedia Commons using:

python -m scripts.download_corpus

The downloader collects 40 real images across five semantic groups:

- red fox
- wolf
- dog
- bear
- deer

Source URLs and available license metadata are preserved in
corpus_manifest.json.

The labeled evaluation set contains ten posts, two per subject.
