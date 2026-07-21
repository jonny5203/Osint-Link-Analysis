"""News NER extraction (PLAN.md T5.2).

Run spaCy (en_core_web_sm) NER over each article, extract PERSON + ORG, insert as
candidate nodes flagged confidence=0.3, _pending_review=True.
"""

from __future__ import annotations

from pathlib import Path


def extract_from_article(article_path: Path) -> list[dict]:
    raise NotImplementedError("T5.2")
