# Nexus deterministic demo fixture

All people, organizations, addresses, identifiers, datasets, and relationships in
this directory are fictional. They exist only for automated testing and local
demonstrations. Do not use them for factual claims.

## Scenario

- Avery Stone owns Northstar Trading Ltd.
- Northstar Trading Ltd controls Blue Harbor Holdings.
- Blue Harbor Holdings owns the vessel Aurora Tide, IMO `9990001`.
- Avery Stone and both organizations have separate fictional addresses.
- A second fictional dataset describes `Avery J. Stone`, providing a later
  entity-resolution candidate without asserting that the two people are identical.

## Contract coverage

`fixture.cypher` creates:

- two `Dataset` nodes;
- two successful `ImportRun` nodes;
- five `SourceRecord` nodes;
- eight `Entity` nodes: two people, two organizations, one vessel, and three
  addresses;
- provenance relationships from every source record;
- the `OWNS`, `CONTROLS`, `OWNS` person-to-vessel path;
- evidence-backed `LOCATED_AT` relationships.

The expected isolated-database totals are 17 nodes and 21 relationships.

## Loading behavior

The fixture uses stable IDs and `MERGE`. Loading it twice must leave the node and
relationship counts unchanged. Apply the Phase 2 schema before loading the fixture.

This file contains no live public-record data and requires no network access.
