"""Write resolution decisions to Neo4j per design decision D1 (PLAN.md T6.4).

D1-a (link):  write (:Entity)-[:ALSO_KNOWN_AS {score, method}]->(:Entity)
D1-b (collapse): MERGE nodes via apoc.refactor.mergeNodes, stash aliases as a property array

Either way, store `score` and `method` so the result is auditable.
"""

from __future__ import annotations


def write_decisions(decisions) -> None:
    raise NotImplementedError("T6.4 — depends on D1")
