# nexus-ingest

Python ingestion + entity-resolution service. See [`../PLAN.md`](../PLAN.md).

## How news-NER output flows into entity resolution (PLAN.md T5.3)

News NER (`enrichment/news_ner.py`) extracts `PERSON`/`ORG` mentions and writes them as
candidate nodes flagged `confidence: 0.3, _pending_review: true`. These low-confidence
nodes are the *messy variants* the entity-resolution pipeline (T6) blocks, scores, and
clusters against the high-confidence sanctions set. They must not pollute the
high-confidence graph — always gate on `_pending_review` until a decision promotes them.
