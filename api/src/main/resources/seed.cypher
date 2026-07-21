// Nexus seed scenario (PLAN.md T2).
// Hand-craft a small PUBLIC-RECORD sanctions-evasion subgraph: 1 sanctioned person,
// 2-3 organizations they control, 1 vessel, 2-3 addresses (~15-20 nodes + relationships).
//
// TODO(T2.2/T2.3): choose a real public scenario and replace these placeholders.
// Rules:
//   - Use parameterized MERGE for every node/relationship so re-running is a no-op.
//   - Attach every entity to a Source via SANCTIONED_BY.
//   - Cite every non-trivial fact in seed-sources.md.

// --- Source(s) ---
MERGE (s_ofac:Source {id: "ofac", list: "OFAC SDN", url: "https://www.treasury.gov/ofac", retrieved_at: "TODO"});

// TODO: Person / Organizations / Vessel / Addresses + SANCTIONED_BY / OFFICER_OF / OWNS / CONTROLS / LOCATED_AT.

// Verification query (must return >=1 row):
// MATCH (p:Person)-[:OFFICER_OF|OWNS|CONTROLS*1..3]->(o:Organization)-[:CONTROLS*0..2]->(v:Vessel)
// RETURN p.name AS person, v.name AS vessel, v.imo AS imo LIMIT 5;
