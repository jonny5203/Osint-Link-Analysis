"""OpenCorporates enrichment (PLAN.md T5.1).

GET /v0.0.4/companies/search with OPEN_CORPORATES_API_TOKEN. For an Organization already
in Neo4j, add (:Person)-[:OFFICER_OF]->(:Organization) edges.
"""

from __future__ import annotations


def enrich_organization(org_id: str) -> int:
    """Enrich one org; return number of OFFICER_OF edges added."""
    raise NotImplementedError("T5.1")
