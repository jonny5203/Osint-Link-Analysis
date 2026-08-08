# Nexus v1 — Self-Contained Implementation Plan

> **Plan status:** reviewed against the current workspace on 2026-07-22.
>
> **Verdict:** the product idea is coherent, but the old execution plan was not safe to
> implement from top to bottom. It mixed incompatible data models, delayed the first
> end-to-end test until too late, relied on an unlikely three-list overlap, omitted edge
> data required by the graph UI, and never added the containerization needed by its own
> one-command-demo acceptance criterion. This version corrects those problems.
>
> **What “self-contained” means here:** a developer should be able to understand the
> architecture, terminology, task order, expected files, commands, success conditions,
> and common failure modes from this document. Internet access is still inherently
> required to download live sanctions data and initial software dependencies, but the
> developer should not need to search the web to discover what a task is asking them to
> do.

---

## Table of contents

- [0. How to use this plan](#0-how-to-use-this-plan)
- [1. Review findings and corrections](#1-review-findings-and-corrections)
- [2. Product outcome, user journey, and scope](#2-product-outcome-user-journey-and-scope)
- [3. Current workspace state](#3-current-workspace-state)
- [4. Glossary](#4-glossary)
- [5. Questions for Humans](#5-questions-for-humans--phase-0-gate)
- [6. Target architecture and boundaries](#6-target-architecture-and-boundaries)
- [7. Technology and reproducibility contract](#7-technology-and-reproducibility-contract)
- [8. Graph data contract](#8-graph-data-contract)
- [9. API contract required by the UI](#9-api-contract-required-by-the-ui)
- [10. Phase map and dependency gates](#10-phase-map-and-dependency-gates)
- [Phase 0 — Decisions](#phase-0--confirm-product-and-architecture-decisions)
- [Phase 1 — Reproducible baseline](#phase-1--make-the-skeleton-reproducible-and-green)
- [Phase 2 — Graph contract and fixture](#phase-2--define-and-prove-the-graph-contract-with-offline-data)
- [Phase 3 — Read GraphQL API](#phase-3--build-the-authenticated-read-only-graphql-vertical-slice)
- [Phase 4 — Graph explorer](#phase-4--build-the-minimal-graph-explorer)
- [Phase 5 — OFAC ingestion](#phase-5--build-the-ingestion-framework-and-ofac-vertical-slice)
- [Phase 6 — EU and UN ingestion](#phase-6--add-eu-and-un-adapters-without-assuming-overlap)
- [Phase 7 — Entity resolution](#phase-7--build-and-evaluate-non-destructive-entity-resolution)
- [Phase 8 — Investigation API](#phase-8--add-investigation-persistence-and-authorization)
- [Phase 9 — Investigation UI](#phase-9--build-the-investigation-workspace-ui)
- [Phase 10 — Packaging](#phase-10--package-and-verify-the-complete-local-system)
- [Phase 11 — Documentation and release audit](#phase-11--documentation-release-audit-and-handoff)
- [Optional work](#optional-a--opencorporates-and-news-enrichment)
- [12. Risk register](#12-risk-register-and-trigger-actions)
- [13. Definition of Done](#13-definition-of-done-and-traceability)

---

## 0. How to use this plan

Work in phase order. Do not begin a phase until every prerequisite and exit criterion of
the previous phase is satisfied.

### Status markers

- `[ ]` — not verified
- `[~]` — work is in progress, but the exit criteria are not all satisfied
- `[x]` — verified complete with evidence
- `[!]` — blocked by a named Question for a Human or external dependency
- `[S]` — explicitly skipped because the task is optional

Creating a file is not completion. A task is complete only when its acceptance criteria
pass. Placeholder tests that only assert `True` are not evidence.

### Evidence rule

For each completed phase, create `docs/verification/phase-<number>.md` containing:

1. the date and operating system;
2. the exact commands run;
3. whether each command passed;
4. any expected counts or screenshots;
5. any limitation that prevents a broad claim.

Do not paste secrets, raw personal data, or full sanctions files into verification notes.

### Task anatomy

Every phase below states:

- **Purpose** — the outcome and why it belongs at this point in the sequence;
- **Prerequisites** — facts that must already be true;
- **Deliverables** — files or behavior produced by the phase;
- **Tasks** — implementation steps in dependency order;
- **Acceptance criteria** — observable proof that the phase is complete;
- **Failure guidance** — what to inspect before guessing.

### Legacy task-number mapping

Existing source comments refer to the previous plan’s `T1`–`T12` numbers. Use this map
until those comments are replaced as their files are implemented:

| Old task | New phase | Meaning |
|---|---:|---|
| T1 | Phase 1 | Reproducible repository foundation |
| T2 | Phase 2 | Graph contract and deterministic fixture |
| T7 | Phase 3 | Read-only GraphQL API |
| T9 | Phase 4 | Search-and-expand graph explorer |
| T3 | Phase 5 | Shared ingestion framework and OFAC adapter |
| T4 | Phase 6 | EU and UN adapters |
| T6 | Phase 7 | Entity-resolution evaluation and links |
| T8 | Phase 8 | Investigation API and authorization |
| T10 | Phase 9 | Investigation workspace UI |
| T11 | Phases 10–11 | Packaging, documentation, and release proof |
| T5 | Optional A | OpenCorporates and news enrichment |
| T12 | Optional B | Entity-resolution article |

When a legacy stub is implemented, replace its old `TODO(Tx)` comment with either a
normal explanatory comment or the new phase/task identifier. Do not leave comments that
claim a working implementation is still a placeholder.

---

## 1. Review findings and corrections

The old plan had a reasonable high-level flow—ingest data, resolve identities, expose a
graph API, and build an analyst UI—but the detailed contracts did not line up.

| Finding in the old plan | Why it was a problem | Correction in this plan |
|---|---|---|
| The architecture diagram said Spring Boot 3, React 18, and Python 3.11 while the stack table and manifests said Spring Boot 4, React 19, and Python 3.13. | A developer could not know which versions were authoritative. | Phase 1 establishes one version matrix and commits lockfiles/toolchain files. |
| Queries matched `:Entity`, but `Person`, `Organization`, and `Vessel` nodes were never given the `Entity` label. | Entity-resolution and generic graph queries would return nothing. | Every browsable domain node receives both `:Entity` and one concrete label. |
| `Source` represented both a publisher and a retrieval, and its `retrieved_at` value was overwritten. | The graph could not prove which downloaded file produced a fact. | `Dataset`, `ImportRun`, and `SourceRecord` are separate concepts with stable IDs and hashes. |
| `SANCTIONED_BY` pointed from an entity to a source file. | A file does not sanction a person; it records a listing. The name also hid record-level provenance. | `SourceRecord-[:DESCRIBES]->Entity`, `SourceRecord-[:FROM_DATASET]->Dataset`, and `SourceRecord-[:OBSERVED_IN]->ImportRun` model the evidence explicitly. |
| The seed query required an organization-to-vessel `CONTROLS` path even though the relationship contract only allowed organization-to-organization control. | The acceptance query could not be satisfied by the declared schema. | `OWNS` and `CONTROLS` now state their allowed endpoint types, and the fixture query follows those rules. |
| The plan assumed a Russian oligarch appeared on OFAC, EU, and UN lists. | The UN list covers Security Council regimes and cannot be assumed to overlap a chosen EU/OFAC example. | Each adapter is verified independently. Cross-list overlap is measured from actual data, never hard-coded as an acceptance gate. |
| OFAC parsing described numeric SDN types and XML elements that do not match the legacy `SDN.XML` contract. | A parser written from that description would target the wrong schema. | Phase 5 selects one named OFAC format, stores a representative fixture, discovers XML namespaces from the document, and accounts for every record type. |
| `unicodedata` was suggested for Cyrillic-to-Latin transliteration. | Unicode normalization does not transliterate Cyrillic. | Phase 7 preserves the original name and uses an explicit transliteration library only for an additional comparison form. |
| Entity resolution offered destructive node collapse via APOC. | It could erase source distinctions and required a plugin absent from Compose. | v1 is non-destructive: accepted matches use `SAME_AS`; uncertain matches use `POSSIBLE_MATCH`; source records remain intact. |
| A “human review” middle band existed, but no review workflow existed. | `LINK` was not actually reviewable or actionable. | The resolver emits a review file, a human records decisions, and a separate apply command writes accepted links. |
| `neighbors` returned nodes but no relationships. | Cytoscape cannot render a graph without edge IDs, endpoints, and types. | Read queries return a `GraphSlice` containing both nodes and edges. |
| The UI needed to list and reload investigations, but the API defined neither query. | The restore flow was impossible. | Phase 8 adds `investigations` and `investigation(id)` queries before Phase 9 uses them. |
| Browser credentials were to be hard-coded in frontend source. | Any built JavaScript bundle would disclose them. | The analyst enters credentials at runtime; they stay in memory for the local session. |
| Compose only ran Neo4j, while the final acceptance criterion required `docker compose up` to run the demo. | No task created Dockerfiles, service health checks, schema initialization, or a web-to-API proxy. | Phase 10 explicitly packages and wires every runtime component. |
| Tests were allowed to use placeholders or vague manual checks. | Green commands could prove nothing. | Every phase names assertions, expected behavior, and negative cases. Browser flows receive automated end-to-end coverage. |
| Eighteen calendar days were assigned before unknown data formats and design decisions were resolved. | The estimate looked precise but was not evidence-based. | This plan uses dependency gates and risk levels. Estimate only after Phase 0 decisions and Phase 1 toolchain proof. |
| Java domain interface `Node` collided with Spring Data Neo4j’s `@Node` annotation. | The current API does not compile; Java resolves the wrong `Node` type. | Phase 1 renames the domain abstraction and Phase 3 favors explicit query DTOs for heterogeneous graph reads. |

### Overall logic verdict

The project is logical as a **local, single-analyst portfolio/demo application**. It is
not a sanctions-screening product and must not claim production compliance, exhaustive
coverage, or legally reliable identity matching. The critical path is:

```text
human decisions
  -> reproducible builds
  -> stable graph contract + offline fixture
  -> read API
  -> minimal graph UI
  -> live source ingestion
  -> evaluated identity links
  -> investigation persistence
  -> saved-work UI
  -> one-command packaging
  -> cold-start release proof
```

The seed-backed API/UI vertical slice deliberately comes before live ingestion. This
proves that the graph, API, and browser agree on node and edge contracts while the data
is still deterministic and small.

---

## 2. Product outcome, user journey, and scope

### v1 outcome

A reviewer can start Nexus locally, load deterministic demo data, and complete this
workflow:

1. sign in as the local analyst;
2. search for a person, organization, vessel, or address;
3. add a search result to a graph canvas;
4. expand one-hop relationships and see labeled edges;
5. inspect the source dataset, source record, retrieval time, and record hash behind a
   listing;
6. see accepted and possible identity links with their score and explanation;
7. create an investigation, add selected entities, annotate them, and save node
   positions;
8. reload the page and restore the investigation exactly;
9. optionally run live OFAC, EU, and UN imports without changing the application code.

### v1 quality promises

- Source records are traceable to a downloaded snapshot.
- Running the same import twice does not create duplicate identities or records.
- A possible identity match never destroys or silently combines source data.
- The default demo and automated tests work without live public-data downloads.
- Public-data writes originate only from the Python batch pipeline.
- API writes are restricted to analyst work product: investigations and their items.
- Search and traversal queries have explicit size limits.
- No secret is committed or compiled into the frontend bundle.

### Non-goals for v1

- legal or regulatory sanctions-screening compliance;
- production deployment, high availability, backups, or disaster recovery;
- multi-tenant identity and access management, SSO, or organization roles;
- automatic destructive merging of entity nodes;
- real-time streaming, Kafka, or change-data capture;
- PDF/OCR ingestion;
- web scraping of news sites;
- graph neural networks or ML training pipelines;
- proving that all three sanctions datasets contain the same named person;
- automatically treating a name similarity as evidence of wrongdoing or identity.

### Safety and interpretation notice

Nexus visualizes public records and similarity signals. A link marked
`POSSIBLE_MATCH` is a lead for review, not a factual identity assertion. A source listing
describes what a publisher recorded at a point in time; it does not imply that every
relationship inferred elsewhere is stated by that publisher. The UI and README must
display this limitation.

---

## 3. Current workspace state

This snapshot separates the verified baseline from later feature scaffolding.

| Area | Current evidence | Honest status |
|---|---|---|
| Repository metadata | The workspace is a Git repository with a private GitHub remote. | Commit and CI evidence are available. |
| Environment | `.env.example` exists and the ignored `.env` configures the local database. | Local Neo4j connectivity is verified without committing secrets. |
| Compose | Neo4j is active with a pinned image, loopback ports, credentials, and a health check. API, ingest, and web remain commented stubs. | Database-only baseline; P1.8's named-volume requirement remains open. |
| Java API | GraphQL SDL and Java filenames exist, but controllers and models are stubs. | Not implemented. |
| Java build | The wrapper compiles for Java 25; the context smoke test and disposable-Neo4j graph-contract test pass. | Green Phase 1 baseline and Phase 2 contract; API features remain unimplemented. |
| Python ingest | Package layout exists; downloaders, parsers, mappers, writers, resolver, and enrichment functions raise `NotImplementedError`. | Not implemented. |
| Python tests | The CLI baseline has two passing tests under Python 3.13. | Green baseline; ingestion behavior remains unimplemented. |
| Web | The testable startup page passes lint, test, typecheck, and build. | Green baseline; graph behavior remains unimplemented. |
| Dependency reproducibility | Python and web lockfiles, the API Maven wrapper, runtime version files, and the Neo4j digest are committed. | Reproducible baseline verified. |
| Graph contract | Schema, fictional fixture, scripts, eight invariants, and the disposable-database integration test pass. | Phase 2 verified complete. |

The project contract is Corretto/OpenJDK 25.0.1, CPython 3.13.12, Node 24.18.0, and the
exact Neo4j image recorded in Section 7. The current local shell still resolves Node
20.20.2 unless the selected `.node-version` is activated; CI uses Node 24.18.0.

---

## 4. Glossary

| Term | Meaning in Nexus |
|---|---|
| OSINT | Open-source intelligence: information collected from publicly available sources. “Open” does not automatically mean unrestricted redistribution. |
| Dataset | A stable publisher/product identity, such as the OFAC SDN list. It does not represent one particular download. |
| Import run | One attempted retrieval and ingestion of a dataset. It records URL, timestamp, SHA-256 hash, status, and counts. |
| Source record | One publisher-controlled record identified by dataset ID plus the publisher’s external ID. It preserves provenance even when Nexus links identities. |
| Entity | A browsable domain object described by a source record: person, organization, vessel, or address. Every such node has the base `Entity` label. |
| Provenance | Evidence showing where data came from: dataset, external record ID, download URL, retrieval time, and content hash. |
| Idempotent import | Re-running an import with identical input produces the same graph identities and no duplicate nodes or relationships. |
| Entity resolution | Comparing records to decide whether they may describe the same real-world entity. |
| Normalization | Creating a comparison-friendly form, such as case-folded names, without discarding the original value. |
| Blocking | Generating a small set of plausible pairs before expensive scoring. It avoids comparing every entity with every other entity. |
| Feature | One comparison signal, such as name similarity, date-of-birth agreement, or identifier conflict. |
| Precision | Of the pairs automatically accepted as matches, the fraction that the labeled evaluation data says are correct. |
| Recall | Of the labeled true matches, the fraction found by the relevant stage. Blocking recall measures candidate generation; decision recall measures final acceptance. |
| Hard negative | A pair that looks similar but is known to be different, such as two people with the same name and conflicting dates of birth. |
| GraphQL | The HTTP API query language used between the React app and Spring service. The server schema defines exactly what clients may request. |
| Cypher | Neo4j’s graph query language. |
| Bolt | Neo4j’s binary database protocol used by the Java and Python drivers. |
| Fixture | Small, deterministic test data committed to the repository. Fixtures do not change when public sources change. |
| Unit test | Tests one function or class without a real external system. |
| Integration test | Tests multiple components together, such as Spring plus a real Neo4j test container. |
| End-to-end test | Drives the built application through the browser and API as a user would. |
| Acceptance criterion | Observable evidence required before a task or phase may be marked complete. |

---

## 5. Questions for Humans — Phase 0 gate

These are product or policy choices, not facts the code can discover. The proposed
defaults make the plan concrete, but a human owner must confirm or replace them before
implementation proceeds.

### QH-1 — Intended deployment

- [x] Confirm **local, single-machine portfolio/demo application** as the v1 target.
- Proposed default: yes.
- If no: specify users, hosting environment, data retention, availability, and security
  requirements. That answer changes Phases 1, 8, and 10 substantially.
- Human answer: **Accepted 2026-07-12.** Nexus v1 is strictly a local, single-machine
  portfolio/demo application for one analyst. Hosted operation, production availability,
  multi-user behavior, compliance use, backup/disaster recovery, and operational data
  retention are excluded. See [ADR 0001](docs/adr/0001-v1-scope.md).

### QH-2 — Identity-resolution policy

- [x] Confirm **never collapse/delete source entities in v1**.
- Proposed default: accepted pairs receive `SAME_AS`; uncertain pairs receive
  `POSSIBLE_MATCH`; source records and original properties remain intact.
- If destructive merge is required: define undo, conflict handling, audit history, and
  who has authority to approve a merge before changing this plan.
- Human answer: **Accepted 2026-07-12.** Resolution never collapses or deletes source
  entities. Accepted pairs receive audited `SAME_AS` links; uncertain pairs receive
  audited `POSSIBLE_MATCH` links. See
  [ADR 0002](docs/adr/0002-non-destructive-identity-resolution.md).

### QH-3 — Investigation storage

- [x] Confirm investigations are stored in Neo4j as `Investigation` nodes with
  `INCLUDES` relationship properties.
- Proposed default: yes; it keeps v1 to one database and makes saved graph work simple.
- If a side store is required: name the store, backup expectations, and transaction
  behavior across stores.
- Human answer: **Accepted 2026-07-12.** Investigations are stored in Neo4j as
  `Investigation` nodes with `INCLUDES` relationship properties, and the authenticated
  principal becomes the investigation `owner`. See
  [ADR 0003](docs/adr/0003-investigation-persistence.md).

### QH-4 — Authentication scope

- [x] Confirm one local analyst account configured from environment variables.
- Proposed default: HTTP Basic for the local demo, credentials entered at runtime and
  retained only in browser memory. The README must state that this is not production
  authentication.
- If multiple users are required: define signup/provisioning, password reset, ownership,
  sharing, and administrator behavior first.
- Human answer: **Accepted 2026-07-12.** One local analyst account is configured through
  environment variables. The browser accepts HTTP Basic credentials at runtime and keeps
  them only in memory. This is demo-only authentication. See
  [ADR 0004](docs/adr/0004-local-authentication.md).

### QH-5 — Demo-data policy

- [x] Confirm the default automated fixture is clearly fictional and the optional
  real-world demo is loaded separately with fact-level citations.
- Proposed default: yes. This keeps tests stable and avoids turning changing public
  allegations into test assertions.
- Human answer: **Accepted 2026-07-12.** Committed automated fixtures are explicitly
  fictional. Optional real-world demo data is loaded separately and requires fact-level
  citations. See [ADR 0001](docs/adr/0001-v1-scope.md#data-policy).

### QH-6 — Raw-data redistribution

- [x] Confirm raw live downloads are ignored by version control; only minimal synthetic
  XML fixtures and download manifests are committed.
- Proposed default: yes. Before committing any real source excerpt, a human must confirm
  that the source terms permit redistribution.
- Human answer: **Accepted 2026-07-12.** Raw live downloads remain ignored. The repository
  may contain minimized synthetic fixtures and metadata-only manifests/reports; committing
  a real source excerpt requires a separate human redistribution review. See
  [ADR 0001](docs/adr/0001-v1-scope.md#data-policy).

### Phase 0 exit gate

- [x] Every question above has a recorded answer.
- [x] Any answer that rejects a proposed default has been reflected in this plan before
  implementation begins.
- [x] Short architecture decision records exist in `docs/adr/` for scope, identity
  resolution, persistence, and authentication.

---

## 6. Target architecture and boundaries

```text
                           Browser
                 React 19 + TypeScript + Cytoscape.js
                 search | expand | inspect | investigate
                               |
                      same-origin /graphql
                               |
                 Spring Boot 4 + Spring GraphQL
          bounded reads | analyst authentication | investigation writes
                               |
                           Neo4j Bolt
                               |
        +----------------------+-----------------------+
        |                                              |
 public-data graph                              analyst work product
 Entity | Dataset | ImportRun |                 Investigation
 SourceRecord | provenance                     -[INCLUDES]-> Entity
        ^
        |
 Python 3.13 batch CLI
 fetch -> validate -> snapshot -> parse -> normalize -> upsert
                    -> resolve -> review file -> apply links
```

### Boundary rules

1. **Python is the only writer of public-source data.** It owns datasets, import runs,
   source records, entities created from those records, public relationships, and
   identity-resolution links.
2. **Spring reads public-source data.** It must use parameterized, bounded queries.
3. **Spring writes only analyst work product.** It owns investigations and `INCLUDES`
   relationship properties. It must never edit a source record or identity link.
4. **The browser never connects directly to Neo4j.** All browser access goes through
   GraphQL.
5. **The ingest component is a batch command, not a long-running FastAPI service.** A
   `/healthz` endpoint adds no value when no other service calls it. Optional operational
   APIs can be reconsidered after v1.
6. **The default demo uses committed synthetic fixtures.** Live imports are explicit
   commands because upstream files can change or be unavailable.

### Why the order matters

- The graph schema must be stable before either writer exists.
- The API and UI first use a deterministic fixture, which isolates contract bugs from
  parser bugs.
- One source adapter proves the shared ingestion framework before two more are added.
- Entity resolution needs records from at least two sources and therefore follows
  ingestion.
- Investigation storage is added after read behavior is stable, preventing public and
  analyst write concerns from being debugged simultaneously.
- Container packaging happens after local commands work independently, so Compose is an
  integration layer rather than a debugging black box.

---

## 7. Technology and reproducibility contract

The initial version families come from the current manifests and the reviewed design.
Phase 1 records exact tested versions; do not perform opportunistic upgrades during a
feature phase.

| Layer | v1 choice | Reproducibility rule |
|---|---|---|
| Graph database | Neo4j Community 5.26 LTS family | Pin an exact image tag and digest in Compose; never use `neo4j:5` or `latest`. |
| Java | Java 25 | Commit `.java-version` with the tested 25.0.1 patch and use the Maven wrapper. |
| API | Spring Boot 4.0.x, Spring GraphQL, Neo4j Java driver/Spring Data Neo4j | Pin the Spring Boot parent patch; let its BOM manage compatible Spring versions. |
| Python | CPython 3.13 | Commit `.python-version` and `uv.lock`; use `uv sync --frozen`. |
| Ingest | `httpx`, `lxml`, Neo4j driver, `rapidfuzz`, explicit transliteration library | Exact transitive versions come from `uv.lock`; optional enrichment dependencies use an optional group. |
| Frontend | React 19, TypeScript, Vite, Apollo Client, Cytoscape.js | Commit `.nvmrc` or `.node-version` and `package-lock.json`; use `npm ci`. |
| Cytoscape integration | Direct Cytoscape instance owned by a React ref/effect | Avoid depending on a thin React wrapper unless a Phase 1 compatibility test proves it works with React 19. |
| Local orchestration | Docker Compose | Pin every base image; define health checks and named volumes. |

### Locking rules

- Maven: use `./mvnw`; the parent and any explicitly declared plugin versions are exact.
- Python: `uv lock` creates `uv.lock`; CI and documented commands use `--frozen`.
- Web: `npm install` creates `package-lock.json`; CI uses `npm ci`, never a fresh
  unconstrained install.
- Docker: an exact tag is human-readable; a digest proves the exact image. Record both.
- Public data: SHA-256 of each downloaded file is the data equivalent of a lockfile.

---

## 8. Graph data contract

This is the shared contract for Python, Java, Cypher fixtures, GraphQL DTOs, and the UI.
Changing it requires updating all consumers and their contract tests in the same phase.

### 8.1 Node labels

| Labels | Required properties | Purpose |
|---|---|---|
| `Entity:Person` | `id`, `kind="PERSON"`, `display_name`, `normalized_name` | A person described by one or more source records or connected by identity links. |
| `Entity:Organization` | `id`, `kind="ORGANIZATION"`, `display_name`, `normalized_name` | A legal entity, group, or organization. |
| `Entity:Vessel` | `id`, `kind="VESSEL"`, `display_name`, `normalized_name` | A maritime vessel; optional `imo` and `flag`. |
| `Entity:Address` | `id`, `kind="ADDRESS"`, `display_name`, `normalized_address` | A browsable address. It has `display_name`, so generic graph rendering does not need a special case. |
| `Dataset` | `id`, `name`, `publisher`, `landing_url` | Stable source product, for example `ofac-sdn`. |
| `ImportRun` | `id`, `dataset_id`, `started_at`, `status`, `download_url` | One fetch/parse/write attempt. On success also stores `finished_at`, `sha256`, and counts. |
| `SourceRecord` | `id`, `dataset_id`, `external_id`, `record_hash`, `first_seen_at`, `last_seen_at`, `active` | Stable identity for a publisher record. IDs are source-qualified. |
| `Investigation` | `id`, `title`, `owner`, `created_at`, `updated_at`, `version` | Analyst-created work product. |

Optional entity properties include `aliases` (list of strings), `dates_of_birth` (list of
source-preserving strings), `nationalities`, `jurisdiction`, `registration_number`,
`imo`, `flag`, and `_source_payload` only if a human approves storing normalized payloads
in Neo4j. Full raw files remain on disk, not in graph properties.

### 8.2 Relationship types

| Relationship | Allowed direction | Meaning and required evidence |
|---|---|---|
| `DESCRIBES` | `SourceRecord -> Entity` | This source record describes this source-specific entity. Exactly one target in v1. |
| `FROM_DATASET` | `SourceRecord -> Dataset` | Exactly one dataset per source record. |
| `OBSERVED_IN` | `SourceRecord -> ImportRun` | The record appeared in this successfully downloaded snapshot. |
| `LOCATED_AT` | `Entity -> Address` | Address stated by a source. Store `evidence_record_ids`. |
| `OFFICER_OF` | `Person -> Organization` | Public-record role. Store `role` and evidence. Not normally inferred from a sanctions name alone. |
| `OWNS` | `Person|Organization -> Organization|Vessel` | Ownership claim. Optional `percentage`; evidence is mandatory. |
| `CONTROLS` | `Person|Organization -> Organization|Vessel` | Control claim distinct from legal ownership; evidence is mandatory. |
| `SAME_AS` | `Entity -> Entity` | Accepted non-destructive identity link. Store `score`, `reasons`, `algorithm_version`, `decided_at`, and `decision_source`. |
| `POSSIBLE_MATCH` | `Entity -> Entity` | Review candidate, not an identity assertion. Store the same audit fields plus `review_status`. |
| `INCLUDES` | `Investigation -> Entity` | Analyst selection. Relationship properties: `annotation`, `x`, `y`, `added_at`, `updated_at`. |

`SAME_AS` and `POSSIBLE_MATCH` endpoints use canonical ordering: the lexicographically
smaller entity ID is always the start node. This prevents mirrored duplicates.

### 8.3 ID rules

- Dataset: stable slug, such as `ofac-sdn`, `eu-fsf`, or `unsc-consolidated`.
- Import run: `<dataset-id>:<UTC timestamp>:<first 12 sha256 characters>` after a
  successful download; a generated attempt ID may be used until the hash exists.
- Source record: `<dataset-id>:<external-id>`.
- Source-specific entity: `entity:<source-record-id>` unless the adapter has a stable,
  documented sub-entity identifier.
- Address: `address:<source-record-id>:<index>` in v1. Do not globally merge addresses
  solely because their strings look alike.
- Investigation: application-generated UUID.

IDs never depend on display names. Names change; publisher IDs and generated UUIDs are
stable.

### 8.4 Property naming and dates

- Neo4j properties use `snake_case`.
- GraphQL exposes idiomatic `camelCase` fields through DTO mapping.
- Timestamps are UTC ISO-8601 strings, for example `2026-07-11T18:30:00Z`.
- Partial dates such as a birth year must not be invented into full dates. Preserve the
  source string and, if useful, separate `year`, `month`, `day`, and `precision` fields in
  the normalized Python model.
- Original spelling is always preserved. Normalized/transliterated values are additional
  comparison fields, never replacements.

### 8.5 Schema operations

Phase 2 creates named constraints and indexes. The required logical set is:

```cypher
CREATE CONSTRAINT entity_id IF NOT EXISTS
FOR (n:Entity) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT dataset_id IF NOT EXISTS
FOR (n:Dataset) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT import_run_id IF NOT EXISTS
FOR (n:ImportRun) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT source_record_id IF NOT EXISTS
FOR (n:SourceRecord) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT investigation_id IF NOT EXISTS
FOR (n:Investigation) REQUIRE n.id IS UNIQUE;

CREATE FULLTEXT INDEX entity_name_search IF NOT EXISTS
FOR (n:Entity) ON EACH [n.display_name, n.aliases];

CREATE INDEX source_record_external_id IF NOT EXISTS
FOR (n:SourceRecord) ON (n.dataset_id, n.external_id);

CREATE INDEX vessel_imo IF NOT EXISTS
FOR (n:Vessel) ON (n.imo);
```

Do not verify this with `SHOW INDEXES RETURN count(*)`: Neo4j creates backing and token
lookup indexes that make a global count misleading. Verify the required **names**, types,
and `ONLINE` state.

### 8.6 Graph invariants

The following must remain true after every import:

1. every `Person`, `Organization`, `Vessel`, and `Address` also has `Entity`;
2. every `SourceRecord` has exactly one `FROM_DATASET` relationship;
3. every active `SourceRecord` has exactly one `DESCRIBES` relationship;
4. every successful import run has a SHA-256 and non-negative record counts;
5. no entity is deleted by resolution;
6. no pair has both mirrored `SAME_AS` links;
7. an investigation item points only to an existing `Entity`;
8. public relationships with factual meaning have evidence record IDs or a cited manual
   seed source.

---

## 9. API contract required by the UI

The exact SDL is implemented in Phase 3, but it must support this behavior. A concrete
`GraphNode` DTO is preferred over a GraphQL interface for v1; it avoids Java polymorphic
type-resolution complexity while still exposing `kind`.

```graphql
enum EntityKind { PERSON ORGANIZATION VESSEL ADDRESS }

type Query {
  searchEntities(term: String!, limit: Int = 20): [SearchHit!]!
  entity(id: ID!): EntityDetail
  neighborhood(id: ID!, depth: Int = 1, nodeLimit: Int = 100, edgeLimit: Int = 200): GraphSlice!
  shortestPath(fromId: ID!, toId: ID!, maxHops: Int = 6): GraphSlice
  investigations: [InvestigationSummary!]!
  investigation(id: ID!): Investigation
}

type Mutation {
  createInvestigation(title: String!): Investigation!
  renameInvestigation(id: ID!, title: String!): Investigation!
  upsertInvestigationItem(input: InvestigationItemInput!): Investigation!
  removeInvestigationItem(investigationId: ID!, entityId: ID!): Investigation!
  saveInvestigationLayout(investigationId: ID!, items: [LayoutItemInput!]!): Investigation!
}

type GraphNode {
  id: ID!
  kind: EntityKind!
  displayName: String!
  aliases: [String!]!
  sanctioned: Boolean!
  datasetIds: [ID!]!
}

type GraphEdge {
  id: ID!
  sourceId: ID!
  targetId: ID!
  type: String!
  label: String!
  confidence: Float
  reviewStatus: String
}

type GraphSlice {
  nodes: [GraphNode!]!
  edges: [GraphEdge!]!
  truncated: Boolean!
}
```

`EntityDetail` additionally exposes source-record summaries, import provenance,
sanctions programs, original/normalized identifiers, and identity-match explanations.
It must not dump arbitrary raw properties to the browser.

### API limit rules

- `term`: trim whitespace; 2–100 characters after trimming.
- search `limit`: clamp to 1–50.
- v1 neighborhood `depth`: only 1 is supported. Reject other values clearly rather than
  pretending to honor them.
- `nodeLimit`: 1–200; `edgeLimit`: 1–500.
- `maxHops`: 1–6. Cypher variable-length bounds are selected from this allowlisted range;
  user text is never concatenated into a query.
- traversal relationship types are allowlisted. Provenance internals are returned in
  detail views, not mixed into the default analyst graph.
- all IDs and search terms are Cypher parameters.

---

## 10. Phase map and dependency gates

### Phase progress tracker

- [x] **Phase 0** — human decisions and ADRs
- [~] **Phase 1** — reproducible green skeleton
- [~] **Phase 2** — graph contract and deterministic fixture
- [ ] **Phase 3** — bounded authenticated read API
- [x] **Phase 4** — search-and-expand graph explorer
- [ ] **Phase 5** — shared import pipeline and OFAC
- [ ] **Phase 6** — EU and UN imports
- [ ] **Phase 7** — evaluated non-destructive resolution
- [ ] **Phase 8** — authorized investigation API
- [ ] **Phase 9** — restorable investigation UI
- [ ] **Phase 10** — one-command packaged demo
- [ ] **Phase 11** — self-contained documentation and release proof
- [ ] / [S] **Optional A** — OpenCorporates and news enrichment
- [ ] / [S] **Optional B** — entity-resolution article

| Phase | Outcome | Depends on | Main risk | Exit proof |
|---:|---|---|---|---|
| 0 | Human decisions and ADRs | none | hidden product assumptions | all QH answers recorded |
| 1 | Reproducible green skeleton | 0 | tool/version mismatch | Java, Python, web, and Compose baseline commands pass |
| 2 | Stable graph schema and offline fixture | 1 | model cannot express demo | schema/invariant/seed tests pass twice |
| 3 | Bounded, authenticated read API | 2 | DTO/Cypher mismatch | GraphQL integration tests pass against Neo4j |
| 4 | Search-and-expand UI vertical slice | 3 | node/edge state errors | component tests plus seed-backed browser smoke pass |
| 5 | Shared import pipeline plus OFAC | 2, 1 | upstream XML drift | fixture tests, live import, and idempotency proof |
| 6 | EU and UN imports | 5 | distinct schemas and endpoint drift | independent data-quality reports and repeat-run proof |
| 7 | Auditable entity resolution | 5–6 | false positive identity links | held-out evaluation and review/apply audit trail |
| 8 | Authorized investigation API | 3 | mixing public and analyst writes | persistence/reload/authorization integration tests |
| 9 | Restorable analyst workspace | 4, 8 | UI/server state divergence | automated create-save-reload browser test |
| 10 | One-command local system | 5–9 | container networking/start order | clean-volume Compose end-to-end test |
| 11 | Self-contained docs and release audit | 10 | instructions differ from reality | independent cold-start walkthrough and traceability audit |

Phases 3–4 and 5–6 may be developed in parallel by separate people after Phase 2, but a
single developer should follow the table order to minimize context switching. Phase 7
requires live/representative records; Phase 8 does not depend on resolution and may start
after Phase 3 if necessary.

---

## Phase 0 — Confirm product and architecture decisions

### Purpose

Remove branches that would otherwise change the schema, auth model, and deployment. This
is short but mandatory.

### Prerequisites

- A human owner is available to answer Section 5.

### Deliverables

- `docs/adr/0001-v1-scope.md`
- `docs/adr/0002-non-destructive-identity-resolution.md`
- `docs/adr/0003-investigation-persistence.md`
- `docs/adr/0004-local-authentication.md`
- updated Section 5 answers

Each ADR contains: context, decision, alternatives rejected, consequences, and date.

### Tasks

- [x] **P0.1 — Record the intended user and deployment.** State whether v1 is strictly a
  local demo. Do not use “for now” without describing what is excluded.
- [x] **P0.2 — Record the identity policy.** Explicitly state that source entities survive
  all resolution decisions and describe `SAME_AS` versus `POSSIBLE_MATCH`.
- [x] **P0.3 — Record persistence and ownership.** State where investigations live and
  how the authenticated principal becomes `owner`.
- [x] **P0.4 — Record auth limitations.** State that HTTP Basic over local HTTP is demo
  only; deployed environments would require TLS and stronger identity management.
- [x] **P0.5 — Record data policy.** Separate fictional committed fixtures, ignored live
  raw files, and optional cited demo material.
- [x] **P0.6 — Re-read Phases 1–11.** If any human answer contradicts them, update the
  affected tasks before marking this phase complete.

The accepted defaults are already the assumptions used by Phases 1–11, so P0.6 required
no downstream task changes.

### Acceptance criteria

- [x] All six Questions for Humans have answers.
- [x] Four ADRs exist and contain no unresolved choice such as “option A or B.”
- [x] The graph labels, API ownership rules, and Compose target still match those ADRs.
- [x] `docs/verification/phase-0.md` links each answer to its ADR.

### Failure guidance

If the owner asks for production, multi-user, or compliance behavior, stop. That is a
scope expansion, not a small v1 variation. Add threat modeling, deployment, retention,
audit, backup, and operational phases before continuing.

---

## Phase 1 — Make the skeleton reproducible and green

### Purpose

Create a trustworthy baseline. Later failures should mean a feature broke, not that an
unlocked dependency or wrong interpreter was used.

### Prerequisites

- Phase 0 is complete.

### Deliverables

- Maven wrapper: `mvnw`, `mvnw.cmd`, `.mvn/wrapper/`
- `.java-version`
- `.python-version`
- `uv.lock`
- `.node-version` or `.nvmrc`
- `package-lock.json`
- exact Neo4j image tag/digest in `docker-compose.yml`
- `scripts/verify.sh`
- CI workflow under `.github/workflows/verify.yml` when this workspace is placed in a
  real Git repository
- green minimal builds for all three codebases

### Tasks

- [x] **P1.1 — Record the version matrix.** Put exact tested versions in
  `docs/development.md`. Match Java 25 and Python 3.13. Select a supported Node release
  and run all web commands through it. Record the exact Spring Boot patch and Neo4j image
  digest.
- [x] **P1.2 — Repair the Java baseline.** Rename the application’s `Node` interface to a
  non-conflicting name such as `GraphEntityView`, or remove it until query DTOs exist.
  Never import Spring’s `@Node` annotation and implement a local type with the same simple
  name. Add missing imports. Keep domain classes minimal; do not pretend stub getters are
  implemented by throwing `UnsupportedOperationException`.
- [x] **P1.3 — Add one meaningful Java smoke test.** It should load the Spring application
  context without requiring a live Neo4j instance by using a test profile or mocked
  configuration. Remove empty placeholder tests or mark them disabled with a precise
  reason until their phase.
- [x] **P1.4 — Convert Python to a batch-package baseline.** Remove FastAPI/uvicorn from
  the core path unless Phase 0 explicitly requires an HTTP service. Add a console entry
  point, for example `nexus-ingest --help`, that exits zero and lists `source` and
  `resolve` command groups even if feature commands are not implemented yet.
- [x] **P1.5 — Separate optional Python dependencies.** Keep spaCy, pandas, and any
  OpenCorporates-only dependency out of the v1 core group unless a core task actually
  imports it. Add development tools such as pytest and a formatter/linter to the dev
  group.
- [x] **P1.6 — Make the web placeholder testable.** Add `test`, `lint`, and `typecheck`
  scripts. Render a small “Nexus is starting” page and test that it mounts. Do not add
  graph behavior yet.
- [x] **P1.7 — Lock dependencies.** Generate `uv.lock` with Python 3.13 and
  `package-lock.json`. Commit the Maven wrapper. Document when network access is needed
  for the initial sync.
- [ ] **P1.8 — Harden the database-only Compose baseline.** Pin Neo4j exactly, bind local
  database ports to `127.0.0.1`, use a named data volume, keep credentials in `.env`, and
  retain a health check. `.env.example` must include `NEO4J_PASSWORD` and
  `ANALYST_PASSWORD` with non-secret examples.
- [x] **P1.9 — Add the local verification script.** It runs Java tests, Python tests,
  Python lint/format checks, web tests/typecheck/build, and `docker compose config` in a
  fail-fast order. It must not download live sanctions data.
- [x] **P1.10 — Add CI parity.** CI invokes the same underlying commands with frozen
  dependency modes. If this checkout cannot hold a real workflow yet, prepare the file
  and document that remote execution is unverified.

### Required commands

```bash
./api/mvnw --file api/pom.xml test

cd ingest
uv sync --frozen --python 3.13
uv run pytest

cd ../web
npm ci
npm run lint
npm run test -- --run
npm run typecheck
npm run build

cd ..
docker compose config
./scripts/verify.sh
```

Run each block from the path shown. A fresh dependency sync requires network access;
subsequent frozen runs should not change lockfiles.

### Acceptance criteria

- [x] Every required command exits 0.
- [x] `git diff --exit-code ingest/uv.lock web/package-lock.json` is clean after frozen
  verification.
- [x] `docker compose config` contains no `latest`, `neo4j:5`, or blank required secret.
- [x] No test in the phase scope is named `test_placeholder` or consists only of
  `assert True`.
- [x] Maven is invoked through `api/mvnw` in docs and CI.
- [x] `uv run python --version` reports Python 3.13.x, not the host’s Python 3.14.
- [x] `docs/verification/phase-1.md` records all exact versions and command results.

### Failure guidance

- If Java says `aggregateBoundary()` or treats a class as an annotation, inspect the
  `Node` name collision first.
- If Python resolves 3.14, inspect `.python-version` and the `uv sync --python 3.13`
  command before changing application code.
- If `npm ci` refuses to run, the lockfile and `package.json` disagree; regenerate once
  intentionally, review the diff, then return to `npm ci`.
- If Maven fails only offline because a plugin is absent, perform one approved online
  wrapper build; do not call that a source-code failure.

---

## Phase 2 — Define and prove the graph contract with offline data

### Purpose

Prove the schema, provenance model, and multi-hop demo without relying on a changing
public website.

### Prerequisites

- Phase 1 commands are green.
- Identity and demo-data decisions are recorded.

### Deliverables

- `api/src/main/resources/schema.cypher` rewritten to Section 8
- `api/src/test/resources/fixture.cypher` or `fixtures/demo/fixture.cypher`
- `fixtures/demo/README.md`
- `scripts/apply-schema.sh`
- `scripts/load-fixture.sh`
- invariant queries under `api/src/test/resources/invariants/`
- schema/fixture integration test

### Deterministic fictional scenario

Use this story unless the owner records a different fictional fixture:

- Person `Avery Stone` owns `Northstar Trading Ltd`.
- `Northstar Trading Ltd` controls `Blue Harbor Holdings`.
- `Blue Harbor Holdings` owns vessel `Aurora Tide`, IMO `9990001`.
- The person and organizations have separate addresses.
- Two fictional datasets provide distinct source records for variant spellings of Avery
  Stone, allowing later resolution tests.

Every fixture ID starts with `fixture:` and every file states clearly that the people,
companies, addresses, identifiers, and relationships are fictional. Do not use this
scenario for factual claims.

### Tasks

- [x] **P2.1 — Replace the schema.** Add the base `Entity` constraint, provenance nodes,
  investigation constraint, full-text name index, and supporting indexes from Section 8.
  Remove per-concrete-label ID constraints that allow the same ID to exist once as a
  person and once as an organization.
- [x] **P2.2 — Create idempotent schema tooling.** `scripts/apply-schema.sh` reads
  connection settings from environment variables, waits for Neo4j readiness with a
  bounded retry, runs the file with `cypher-shell`, and exits non-zero on failure.
- [x] **P2.3 — Build the fictional fixture.** Use `MERGE` on stable IDs. Create datasets,
  one successful import run per dataset, source records, typed entities, provenance
  relationships, addresses, and the person-to-vessel ownership/control path.
- [x] **P2.4 — Make fixture loading idempotent.** The second run must produce identical
  node/relationship counts. Do not use creation timestamps that change every run.
- [x] **P2.5 — Add invariant queries.** Each query returns zero violations, not just a
  count that a human must interpret. Include all eight invariants from Section 8.6.
- [x] **P2.6 — Add a schema integration test.** Start a disposable Neo4j test container,
  apply schema twice, load fixture twice, assert named constraints/indexes and exact
  fixture counts, then run invariants.
- [x] **P2.7 — Prove the intended path.** The following shape must return `Avery Stone`
  and `Aurora Tide`:

  ```cypher
  MATCH path = (p:Person {id: "fixture:entity:avery"})
               -[:OWNS|CONTROLS*1..4]->
               (v:Vessel {id: "fixture:entity:aurora-tide"})
  RETURN p.display_name AS person,
         v.display_name AS vessel,
         [r IN relationships(path) | type(r)] AS relationship_types;
  ```

- [x] **P2.8 — Keep real demo data separate.** Create a placeholder process in
  `fixtures/public-demo/README.md` describing required fact-level URL, retrieval date,
  quoted fact summary, and reviewer approval. Do not block the deterministic fixture on
  choosing a real person.

### Acceptance criteria

- [x] Applying `schema.cypher` twice succeeds.
- [x] Required schema object names exist and the full-text index reaches `ONLINE`.
- [x] Loading the fixture twice leaves exact counts unchanged.
- [x] Every invariant query reports zero violations.
- [x] The path query returns exactly the fictional person and vessel with an `OWNS`,
  `CONTROLS`, `OWNS` relationship sequence.
- [x] Searching the full-text index for `Avery` returns the person.
- [x] The integration test starts from an empty disposable database and exits 0.
- [x] No public person or organization is embedded in automated acceptance assertions.
- [x] `docs/verification/phase-2.md` records schema names, counts, and query results.

### Failure guidance

- If `SHOW INDEXES` returns more rows than expected, inspect names and types; Neo4j’s
  backing and token indexes are normal.
- If `MATCH (n:Entity)` misses people or vessels, inspect fixture labels before changing
  the query.
- If the path is empty, compare relationship direction and allowed endpoints with
  Section 8.2.

---

## Phase 3 — Build the authenticated read-only GraphQL vertical slice

### Purpose

Expose stable, bounded graph reads against the deterministic fixture before live-data
complexity enters the system.

### Prerequisites

- Phase 2 schema and fixture tests pass.
- Authentication decision is recorded.

### Deliverables

- final read portion of `api/src/main/resources/graphql/schema.graphqls`
- query DTOs under `api/src/main/java/io/nexus/api/query/`
- bounded Cypher query service using `Neo4jClient` or the Neo4j driver
- GraphQL controller/resolvers
- security configuration
- validation and error mapping
- unit and Neo4j integration tests

### Tasks

- [ ] **P3.1 — Replace the draft SDL.** Implement `searchEntities`, `entity`,
  `neighborhood`, and `shortestPath` plus `GraphNode`, `GraphEdge`, `GraphSlice`, source
  summaries, and match-explanation types. Remove the old nodes-only `neighbors` field.
- [ ] **P3.2 — Use explicit query DTOs.** Heterogeneous graph reads should map Cypher
  rows into records/classes such as `GraphNodeDto`, `GraphEdgeDto`, and
  `EntityDetailDto`. Do not force Person, Organization, Vessel, and Address through a
  misleading `Neo4jRepository<Person, String>`.
- [ ] **P3.3 — Implement full-text search.** Call the named full-text index, order by its
  score, apply the clamped limit, and return dataset IDs. Escape or reject dangerous
  Lucene syntax so a user receives a clear validation error rather than a parser error.
- [ ] **P3.4 — Implement neighborhood reads.** Return both nodes and edges. Use an
  allowlist of analyst-facing relationships (`OWNS`, `CONTROLS`, `OFFICER_OF`,
  `LOCATED_AT`, `SAME_AS`, `POSSIBLE_MATCH`). Set `truncated=true` if either limit was
  reached.
- [ ] **P3.5 — Implement shortest path.** Validate `maxHops` as 1–6, use only allowlisted
  relationship types, and return nodes and ordered edges. Return `null` for no path,
  not an empty path that looks successful.
- [ ] **P3.6 — Implement detail/provenance.** Fetch source record ID, dataset, external
  ID, import retrieval time, record hash, and identity-match reasons without exposing raw
  payloads or unrelated Neo4j properties.
- [ ] **P3.7 — Add local authentication now.** Enable Spring Security. Read username and
  password from environment; never put a default real password in source. All GraphQL
  operations require the analyst role. GraphiQL is enabled only in a `dev` profile and
  still requires authentication.
- [ ] **P3.8 — Validate all inputs.** Add explicit messages and tests for blank/one-letter
  search, excessive limits, missing IDs, unsupported depth, and invalid hop counts.
- [ ] **P3.9 — Add unit tests.** Test limit clamping, DTO mapping, edge ID stability,
  Lucene input handling, and relationship allowlisting without a database.
- [ ] **P3.10 — Add integration tests.** Against disposable Neo4j with the Phase 2
  fixture, assert search result, exact neighborhood edge endpoints, path ordering,
  provenance fields, truncation behavior, and no-path behavior.
- [ ] **P3.11 — Add security tests.** Unauthenticated GraphQL requests return 401;
  valid credentials succeed; wrong credentials fail; errors do not echo the password.

### Example smoke query

```graphql
query SearchAndExpand {
  searchEntities(term: "Avery", limit: 5) {
    score
    node { id kind displayName datasetIds }
  }
  neighborhood(id: "fixture:entity:avery", depth: 1) {
    nodes { id kind displayName }
    edges { id sourceId targetId type label }
    truncated
  }
}
```

### Acceptance criteria

- [ ] `./mvnw test` passes unit, GraphQL, security, and Neo4j integration tests.
- [ ] The example query returns Avery plus at least the `OWNS` edge and its target.
- [ ] Every edge endpoint appears in the returned node list.
- [ ] `shortestPath` returns the ordered fictional person-to-vessel path within four
  hops.
- [ ] An invalid `maxHops=100` is rejected before Cypher execution.
- [ ] An unauthenticated request returns 401; valid analyst credentials return 200.
- [ ] No query performs unbounded `MATCH p=(a)-[*]-(b)` traversal.
- [ ] GraphQL field names and frontend query documents have a contract test or generated
  type check.
- [ ] `docs/verification/phase-3.md` includes redacted request/response examples.

### Failure guidance

- If GraphQL cannot resolve a Java interface type, simplify to the concrete `GraphNode`
  DTO rather than adding fragile runtime type guessing.
- If search returns no results while Cypher does, confirm the full-text index is online
  and the exact index name is used.
- If the graph renders nodes later but no edges, verify the API response already contains
  stable `sourceId` and `targetId`; do not patch around it in the browser.

---

## Phase 4 — Build the minimal graph explorer

### Purpose

Complete the first user-visible vertical slice: authenticate, search, add a result, and
expand relationships using deterministic data.

### Prerequisites

- Phase 3 read API and fixture are running.

### Deliverables

- authenticated Apollo client
- search UI
- Cytoscape graph adapter and canvas
- selected-node detail panel with provenance
- loading, empty, and error states
- component tests and one seed-backed browser smoke test

### Tasks

- [x] **P4.1 — Implement runtime credential entry.** Present a local-demo sign-in form.
  Keep the Basic authorization value in React memory, not source code, a Vite build-time
  variable, local storage, logs, or error messages. A page refresh may require sign-in
  again in v1.
- [x] **P4.2 — Configure same-origin GraphQL.** Development uses the Vite `/graphql`
  proxy; packaged mode uses the web server proxy from Phase 10. Apollo always calls the
  relative `/graphql` path.
- [x] **P4.3 — Implement typed query documents.** Add search, entity detail,
  neighborhood, and shortest-path documents matching Phase 3. Compile-time types must
  cover node and edge fields.
- [x] **P4.4 — Implement debounced search.** Debounce 300 ms, do not query fewer than two
  trimmed characters, cancel/ignore stale results, support keyboard selection, and show
  loading/no-results/error states.
- [x] **P4.5 — Implement a pure graph merge adapter.** Given a `GraphSlice`, return unique
  Cytoscape elements keyed by stable IDs. Re-adding the same slice changes no counts.
  Reject/log an edge whose endpoint is absent instead of rendering corrupt state.
- [x] **P4.6 — Own Cytoscape safely.** Create one Cytoscape instance in a React effect,
  store it in a ref, register event handlers once, and destroy it on unmount. Add fCoSE
  only if its version is locked and tested with the chosen Cytoscape version.
- [x] **P4.7 — Preserve layout during expansion.** Existing nodes keep their positions.
  Place new nodes around the expanded node, then optionally run a constrained layout.
  Provide an explicit “Re-layout” action for moving the whole graph.
- [x] **P4.8 — Style semantic types.** Person, organization, vessel, and address have
  distinguishable shapes/colors plus text labels. Sanctions status uses an additional
  border/icon, not color alone. `POSSIBLE_MATCH` edges are visibly uncertain.
- [x] **P4.9 — Implement details.** Show display name, kind, aliases, datasets, source
  record IDs, retrieval time, and identity-link explanation. Include the “lead, not
  fact” notice for possible matches.
- [x] **P4.10 — Test state behavior.** Unit-test graph deduplication, stale search
  responses, missing endpoints, authentication-header injection, and layout preservation.
- [x] **P4.11 — Add a browser smoke test.** Against fixture data: sign in, search Avery,
  add the person, expand once, assert an organization node and `OWNS` edge are visible,
  and open provenance detail.

### Acceptance criteria

- [x] `npm run lint`, `npm run test -- --run`, `npm run typecheck`, and
  `npm run build` all pass.
- [x] Search does not send a request for a one-character term.
- [x] Adding or expanding the same node twice creates no duplicate graph elements.
- [x] The browser displays both relationship type and direction.
- [x] Existing node positions remain unchanged during incremental expansion unless the
  user invokes “Re-layout.”
- [x] No password string appears in built JavaScript, browser storage, or test snapshots.
- [x] The automated browser smoke test passes against a fresh fixture database.
- [x] `docs/verification/phase-4.md` contains the test result and one screenshot.

### Failure guidance

- If React renders twice in development, ensure Strict Mode cleanup destroys the first
  Cytoscape instance; do not globally disable Strict Mode to hide lifecycle bugs.
- If Apollo succeeds in tests but fails in the browser, inspect the relative proxy path
  and 401 response before adding CORS exceptions.
- If expansion moves the entire graph, inspect the layout call and locked existing nodes.

---

## Phase 5 — Build the ingestion framework and OFAC vertical slice

### Purpose

Prove one complete, auditable live-data path before copying patterns for other sources.

### Prerequisites

- Phase 1 Python baseline is green.
- Phase 2 schema is stable.
- Raw-data policy is confirmed.

### Deliverables

- source configuration under `ingest/config/sources.toml`
- source-neutral models and pipeline
- OFAC downloader, parser, normalizer/mapper, writer, and CLI command
- small synthetic OFAC-schema fixtures
- import manifest and quality report
- unit and Neo4j integration tests

### Selected OFAC contract

Use the legacy OFAC `SDN.XML` product for v1 because its core fields are sufficient and
OFAC continues to publish it. The official landing page is
`https://ofac.treasury.gov/sanctions-list-service`; the traditional download URL is
`https://www.treasury.gov/ofac/downloads/sdn.xml`, which may redirect to OFAC’s Sanctions
List Service. Record the final URL and allow redirects only to an explicit official-host
allowlist.

The document root is `sdnList`; entries are `sdnEntry`; the stable key is `uid`; common
types are textual values such as Individual, Entity, Vessel, and Aircraft. Do not code
the old plan’s numeric `1/2/3/4` assumption. XML namespaces have changed before, so use
the document namespace/local names and keep a namespace regression fixture.

Aircraft are out of the v1 graph scope. The parser must still count them as
`unsupported_by_policy`; silently dropping them is a failure.

### Source-neutral pipeline

```text
fetch to temporary file
  -> validate status, host, size, XML root, and non-empty content
  -> compute SHA-256
  -> atomically move to data/raw/<dataset>/<date>/<sha256>.<ext>
  -> create ImportRun(status=FETCHED)
  -> streaming parse into NormalizedRecord values
  -> quality checks and dry-run report
  -> batched, allowlisted-label upsert
  -> mark observed records and successful run
  -> only after success mark previously seen-but-absent records inactive
```

### Tasks

- [ ] **P5.1 — Replace source-specific shared models.** Rename `SdnRecord` to a generic
  `NormalizedRecord`. Include dataset ID, external ID, entity kind, original display
  name, aliases, identifiers, programs, addresses, source fields, and stable
  `record_hash`. Model missing/partial dates explicitly.
- [ ] **P5.2 — Define structured outcomes.** `FetchResult`, `ParseStats`, `WriteStats`,
  and `ImportReport` separately count fetched bytes, parsed records, supported records,
  unsupported records by reason, inserted, changed, unchanged, and failed records.
- [ ] **P5.3 — Configure sources.** Store dataset ID, landing URL, download URL, expected
  root local name, maximum bytes, timeout, and allowed redirect hosts in
  `sources.toml`. URLs are data, not scattered constants.
- [ ] **P5.4 — Implement safe download and caching.** Use connect/read timeouts, a
  descriptive User-Agent, bounded redirects, streamed bytes, maximum size, temporary
  file, SHA-256, and atomic rename. Never treat an HTML error page as cached XML.
- [ ] **P5.5 — Write the raw manifest.** Beside each raw file store JSON containing
  dataset ID, requested/final URL, retrieval UTC time, HTTP metadata, byte count,
  SHA-256, and parser format version. Raw files and manifests are ignored locally unless
  policy explicitly says otherwise.
- [ ] **P5.6 — Stream-parse OFAC XML.** Use `lxml.etree.iterparse`, clear processed
  elements, preserve original values, extract aliases/programs/addresses, map supported
  textual types, and count aircraft/unknown values. Namespace handling must not depend
  on one historical URI string.
- [ ] **P5.7 — Create minimized fixtures.** Include one individual, organization, vessel,
  aircraft, alias, address, missing optional field, partial date, changed namespace, and
  malformed record. Fixtures use fictional names and IDs.
- [ ] **P5.8 — Normalize deterministically.** Unicode NFKC, case-folding, punctuation and
  whitespace normalization create comparison values. Keep originals. Serialize the
  normalized record with sorted keys before hashing.
- [ ] **P5.9 — Upsert in batches by allowlisted kind.** All entities use `Entity` plus an
  allowlisted concrete label. Do not use unlabelled `MERGE (e {id: ...})`; do not inject
  labels from source text. Create/update Dataset, ImportRun, SourceRecord, Entity,
  Address, and provenance relationships using parameters.
- [ ] **P5.10 — Make change accounting real.** Compare `record_hash` to distinguish
  inserted, changed, and unchanged. A second identical run reports zero inserted and
  zero changed. Do not infer counts from wishful application-side counters.
- [ ] **P5.11 — Handle removals safely.** Only after the entire import succeeds, mark
  source records not observed in the current run `active=false`. Never delete them.
  A failed run must not deactivate anything.
- [ ] **P5.12 — Build the CLI.** Provide:

  ```text
  nexus-ingest source fetch ofac
  nexus-ingest source run ofac --dry-run
  nexus-ingest source run ofac --write
  nexus-ingest source report <import-run-id>
  ```

  `--dry-run` never connects to or writes Neo4j.
- [ ] **P5.13 — Add tests.** Unit-test downloader validation, cache hits, parser mapping,
  namespace change, normalization, hashing, and malformed records. Integration-test
  first write, unchanged repeat, one changed record, and failure-without-deactivation.
- [ ] **P5.14 — Run one live import.** Save only the manifest/report as evidence. Record
  upstream record counts rather than expecting the old plan’s approximate “8,000.”

### Acceptance criteria

- [ ] All fictional fixture records are accounted for: supported + unsupported + failed
  equals encountered.
- [ ] The parser’s peak-memory behavior is consistent with streaming; it does not build a
  list of the entire XML document.
- [ ] A dry run creates no Neo4j nodes and produces a quality report.
- [ ] A first fixture import creates exact expected nodes/relationships; the identical
  second import creates/changes zero.
- [ ] Changing one fixture field increments `changed` by exactly one without changing the
  SourceRecord ID.
- [ ] A deliberately failed run leaves prior active flags unchanged.
- [ ] The live import is non-zero, its XML root is validated, and its report reconciles
  all encountered entry types.
- [ ] Every live SourceRecord links to one Dataset, one Entity, and the successful
  ImportRun in which it was observed.
- [ ] `uv run pytest` and the full repository verification script pass.
- [ ] `docs/verification/phase-5.md` records SHA-256, counts, and redacted command output.

### Failure guidance

- If the download begins with `<html`, stop at fetch validation; do not modify the XML
  parser.
- If every XPath returns empty, inspect the root namespace/local name before assuming the
  feed has no records.
- If the repeat run reports updates, compare deterministic serialization, timestamp
  exclusion, list ordering, and record hashes.
- If a dynamic-label query is tempting, group records by an internal enum and run one
  fixed Cypher statement per supported label.

---

## Phase 6 — Add EU and UN adapters without assuming overlap

### Purpose

Reuse the proven pipeline for two genuinely different schemas and demonstrate that
Nexus preserves source distinctions.

### Prerequisites

- Phase 5 shared pipeline and OFAC import are green.

### Authoritative source entry points

- EU consolidated financial sanctions dataset landing page:
  `https://data.europa.eu/data/datasets/consolidated-list-of-persons-groups-and-entities-subject-to-eu-financial-sanctions?locale=en`
- UN Security Council Consolidated List landing page:
  `https://main.un.org/securitycouncil/en/content/un-sc-consolidated-list`
- UN XML link currently exposed by that page:
  `https://scsanctions.un.org/resources/xml/en/consolidated.xml`

The EU direct distribution URL is allowed to move. Phase 6 records the current XML 1.1
download URL from the official dataset metadata in `sources.toml` and verifies its host,
format, and root before accepting it. This is a configuration update, not a code rewrite.

### Deliverables

- EU and UN source configurations and adapters
- minimized fictional fixtures for each schema
- source-specific mapping documentation
- per-import data-quality reports
- cross-source normalization tests

### Tasks

- [ ] **P6.1 — Freeze source contracts.** For each source, record landing URL, direct
  URL, allowed redirect hosts, XML root, namespace behavior, stable external ID field,
  supported record kinds, and known “not available” sentinel values.
- [ ] **P6.2 — Implement the EU adapter.** Parse the official XML 1.1 structure into
  `NormalizedRecord`; preserve publication/reference IDs, name parts, aliases,
  citizenship/jurisdiction, dates, addresses, and regulation/program references that are
  actually present. Never invent a vessel or ownership relationship from free text.
- [ ] **P6.3 — Implement the UN adapter.** Handle individual and entity sections,
  permanent reference numbers, four-part names, original-script names, good/low-quality
  aliases, partial/alternative dates, addresses, listing date, and committee/regime
  identifiers. Treat the literal sentinel `na` as missing only in fields where the source
  defines it that way.
- [ ] **P6.4 — Add schema fixtures.** Each source fixture covers aliases, missing fields,
  multiple dates/addresses, original script, unsupported/unknown type, and malformed
  input. All people and entities are fictional.
- [ ] **P6.5 — Prove source-neutral hashing.** Field ordering and parser iteration order
  must not alter record hashes. A real content change must alter the hash.
- [ ] **P6.6 — Produce quality reports.** Report total entries, supported kinds,
  unsupported/failed counts, required-field coverage, aliases/addresses extracted,
  and active/inactive changes. Set explicit failure thresholds: zero records, missing
  external IDs, or more than 1% parse failures fail the import; any non-zero parse failure
  is listed with a reason.
- [ ] **P6.7 — Run each source twice.** The second identical snapshot produces zero
  inserted/changed source records. If a publisher changes the file between runs, prove
  idempotency against the cached same-hash file instead of comparing two different
  snapshots.
- [ ] **P6.8 — Measure overlap; do not require it.** Run a report of normalized-name and
  strong-identifier candidate overlaps between dataset pairs. Use the result to build
  Phase 7 labels, but do not assert a named person exists in all three sources.
- [ ] **P6.9 — Add regression tests.** Shared pipeline tests run against all adapters.
  One broken adapter must identify its dataset and record ID in the error.

### Acceptance criteria

- [ ] EU fixture and live imports reconcile all encountered records.
- [ ] UN fixture and live imports reconcile all encountered records.
- [ ] Each live import is non-zero and records its official landing URL, final download
  URL, retrieval time, and SHA-256.
- [ ] Re-importing the same cached file produces zero inserted and zero changed records.
- [ ] A source record ID from one dataset cannot collide with the same external ID from
  another dataset.
- [ ] Unknown types and parse failures are counted and visible, never silently skipped.
- [ ] The overlap report states actual pair counts, including zero where applicable.
- [ ] No acceptance criterion names a person who is assumed to appear on all three lists.
- [ ] All Python tests and graph invariants pass.
- [ ] `docs/verification/phase-6.md` contains per-source quality summaries.

### Failure guidance

- If a source requires credentials, presents terms that prevent intended use, or no
  longer exposes a machine-readable distribution, raise a Question for a Human. Do not
  bypass access controls or scrape an interactive page.
- If a live count changes, compare SHA-256 and publisher metadata before changing test
  expectations.
- If `na` becomes a real alias/name, inspect field-specific sentinel handling rather than
  globally deleting that string.

---

## Phase 7 — Build and evaluate non-destructive entity resolution

### Purpose

Generate auditable identity candidates, evaluate them on labeled data, obtain human
decisions for uncertain pairs, and write links without erasing source provenance.

### Prerequisites

- At least two adapters have representative records.
- QH-2 confirms non-destructive resolution.
- The owner understands that small evaluation data cannot support production accuracy
  claims.

### Deliverables

- normalization, candidate generation, feature scoring, decision, evaluation, export,
  and apply modules
- versioned labeled pair datasets
- review CSV/JSONL format and instructions
- resolution report with blocking and decision metrics
- `SAME_AS`/`POSSIBLE_MATCH` writer
- API-visible explanations

### Decision vocabulary

- `AUTO_ACCEPT`: strong evidence and no conflicting strong identifier; eligible for a
  `SAME_AS` link.
- `REVIEW`: plausible but insufficient; exported for a human and optionally represented
  as `POSSIBLE_MATCH`.
- `REJECT`: evidence says distinct or similarity is too weak; retained in the run report,
  not written as a graph edge.

Do not call the decision `MERGE`; v1 never merges nodes.

### Tasks

- [ ] **P7.1 — Define an entity-comparison model.** Inputs include entity kind, all
  original/normalized aliases, identifiers, date values with precision, country/
  nationality sets, and addresses. Missing values are distinct from conflicts.
- [ ] **P7.2 — Normalize without data loss.** Produce NFKC/case-folded/punctuation-
  normalized forms. Add transliterated forms through an explicit library such as
  Unidecode; keep original script. Unit-test Cyrillic and diacritics so transliteration
  is not confused with Unicode normalization.
- [ ] **P7.3 — Generate candidates with multiple blocking keys.** Use the union of safe
  keys, for example: exact strong identifier; normalized surname prefix + birth year;
  normalized token prefix + country; and exact normalized alias. Missing country must
  not place all records into one giant block. Deduplicate candidate pairs.
- [ ] **P7.4 — Measure blocking recall.** Every labeled true match should become a
  candidate. Report missed pairs and which blocking key should have caught them.
- [ ] **P7.5 — Compute isolated features.** At minimum: best alias token-sort score,
  Jaro-Winkler score, exact/compatible/conflicting date signal, country overlap,
  normalized address score, entity-kind agreement, and exact/conflicting strong
  identifiers. Each feature function has unit tests.
- [ ] **P7.6 — Build labeled data.** Create at least 100 reviewed pairs, including at
  least 40 matches, 40 nonmatches, transliterations, missing fields, common names, and
  hard negatives. Every real-data label includes source record IDs and a short reason.
  Split into a threshold-tuning set and a held-out evaluation set before tuning.
- [ ] **P7.7 — Define conservative rules.** Strong identifier conflict always rejects.
  Name similarity alone never auto-accepts a common person name. Exact strong identifier
  agreement may auto-accept only when entity kinds agree and no strong conflict exists.
  Store a machine-readable reason list for every decision.
- [ ] **P7.8 — Keep thresholds in versioned configuration.** For example
  `resolution-v1.toml` contains thresholds and `algorithm_version`. Code reads this file;
  reports record its hash.
- [ ] **P7.9 — Export a review queue.** Include pair IDs, display names, source datasets,
  feature values, proposed decision, reasons, and blank `human_decision`/
  `human_reason` columns. Sort deterministically. Never include secrets or unnecessary
  personal fields.
- [ ] **P7.10 — Implement the apply command.** It validates that each endpoint still
  exists, rejects self-links/mirrored duplicates, requires a human reason for overridden
  decisions, and writes audited `SAME_AS` or `POSSIBLE_MATCH` relationships. Reapplying
  the same review file is idempotent.
- [ ] **P7.11 — Evaluate on held-out labels.** Report candidate-pair reduction, blocking
  recall, auto-accept precision/recall, review-band size, false positives, false
  negatives, and confusion matrix. Report raw numerator/denominator with percentages.
- [ ] **P7.12 — Guard against transitive overclaiming.** The UI may display connected
  identity links, but an A–B and B–C chain must not silently create an A–C edge or one
  collapsed entity. Each edge retains its own evidence.
- [ ] **P7.13 — Test performance and repeatability.** Running the same configuration and
  records produces byte-for-byte equivalent sorted decisions except run timestamps.
  Record pair counts and elapsed time; do not assert a flaky wall-clock threshold in CI.

### Acceptance criteria

- [ ] Candidate generation finds at least 95% of labeled true matches; missed cases are
  documented.
- [ ] The held-out hard-negative set has zero automatic false positives. If not, adjust
  rules using the tuning set and re-evaluate once; do not tune directly on held-out rows.
- [ ] Precision, recall, and raw counts are reported; the README explicitly says the
  sample is too small for production claims.
- [ ] Every accepted/review link has score components, reasons, algorithm version,
  decision source, and timestamp.
- [ ] SourceRecord and Entity node counts are unchanged by applying resolution links.
- [ ] Applying the same reviewed file twice creates no duplicate relationships.
- [ ] Strong identifier conflicts cannot result in `SAME_AS`.
- [ ] Unit, evaluation, writer-integration, and graph-invariant tests pass.
- [ ] `docs/verification/phase-7.md` links the versioned evaluation report and records
  its dataset/config hashes.

### Failure guidance

- If candidate volume approaches all-pairs volume, inspect giant missing-value blocks.
- If transliterated names never match, inspect the explicit transliteration output; NFKC
  alone will not convert scripts.
- If five variants form one connected component, that proves connectivity, not accuracy.
  Inspect every link’s labeled evidence.
- If one bad link joins two clusters, do not collapse or infer transitive links; lower the
  automatic threshold or move that case to review.

---

## Phase 8 — Add investigation persistence and authorization

### Purpose

Let the authenticated analyst save work without granting the API permission to mutate
public-source data.

### Prerequisites

- Phase 3 authenticated reads are stable.
- Investigation storage/ownership decisions are recorded.

### Deliverables

- investigation GraphQL queries and mutations from Section 9
- `Investigation` mapping
- `InvestigationItem` relationship-properties mapping with `@TargetNode`
- authorization and validation service
- integration tests proving persistence and public-data immutability

### Tasks

- [ ] **P8.1 — Complete the SDL before Java code.** Add list/get queries and create,
  rename, upsert item, remove item, and save layout mutations. This closes the old plan’s
  missing reload contract.
- [ ] **P8.2 — Map relationship properties explicitly.** `INCLUDES` carries annotation,
  x/y, and timestamps. Use Spring Data Neo4j relationship-properties support or explicit
  Cypher; do not put one investigation’s annotation on the shared Entity node.
- [ ] **P8.3 — Derive owner from authentication.** The client never supplies `owner`.
  Create/list/get/update queries filter by the authenticated principal even in
  single-user mode.
- [ ] **P8.4 — Validate text and coordinates.** Title: 1–200 trimmed characters.
  Annotation: at most 5,000 characters, stored/rendered as plain text. Coordinates must
  be finite numbers within documented bounds. Entity and investigation IDs must exist.
- [ ] **P8.5 — Define upsert semantics.** Adding the same entity twice updates one
  `INCLUDES` relationship. Annotation updates preserve coordinates; layout updates
  preserve annotation. Remove deletes only the `INCLUDES` relationship.
- [ ] **P8.6 — Define layout semantics.** `saveInvestigationLayout` updates the supplied
  items atomically. It does not implicitly remove omitted investigation items. Reject an
  item not already included unless the mutation contract explicitly says it may add.
- [ ] **P8.7 — Add optimistic versioning.** Increment `Investigation.version` on each
  write and return it. If the chosen client contract sends an expected version, reject a
  stale update clearly; otherwise document last-write-wins for the single-user demo.
- [ ] **P8.8 — Enforce the write boundary.** Put public-data query code and investigation
  write code in separate packages/services. Add a test snapshot of Entity, SourceRecord,
  Dataset, and identity-link counts/properties before and after every mutation flow.
- [ ] **P8.9 — Add integration coverage.** Create, list, get, rename, add four entities,
  annotate two, save layout, reload, remove one, and verify exact persisted state after a
  new database session.
- [ ] **P8.10 — Add negative authorization tests.** Missing/wrong credentials fail;
  unknown investigation/entity fails without partial writes; simulated other owner
  cannot read or mutate the investigation.

### Acceptance criteria

- [ ] A four-entity investigation survives API restart/reconnection with title,
  annotations, positions, owner, and version intact.
- [ ] Listing returns only the authenticated owner’s investigations.
- [ ] Adding the same entity twice leaves one `INCLUDES` relationship.
- [ ] A failed layout request changes no coordinates.
- [ ] Annotation content is returned as plain text and length limits are enforced.
- [ ] Public-data nodes and relationships are byte-for-byte/property-equivalent before
  and after the mutation suite.
- [ ] Unauthenticated requests return 401; unauthorized ownership returns 403 or a
  documented not-found policy consistently.
- [ ] `./mvnw test` and repository verification pass.
- [ ] `docs/verification/phase-8.md` records the full redacted create-to-reload flow.

### Failure guidance

- If annotations appear on Entity nodes, stop and correct the relationship-property
  model before adding UI work.
- If list/load is difficult, do not make the browser remember server data locally; fix
  the API contract.
- If a mutation partially updates a layout, inspect transaction boundaries and validation
  order.

---

## Phase 9 — Build the investigation workspace UI

### Purpose

Turn the read-only explorer into a restorable analyst workflow while keeping UI state and
server state explicit.

### Prerequisites

- Phase 4 explorer works.
- Phase 8 investigation API works.

### Deliverables

- investigation list/create/select UI
- add/remove graph item actions
- plain-text annotation editor
- save/restore layout behavior
- dirty/saving/saved/error states
- component tests and end-to-end create-save-reload test

### Tasks

- [ ] **P9.1 — Implement a typed investigation hook/store.** It exposes list, load,
  create, rename, add/update/remove item, annotate, and save layout. Separate server data
  from transient Cytoscape selection state.
- [ ] **P9.2 — Add investigation navigation.** Show saved investigations, create with a
  validated title, select one, and display updated time. Empty and API-error states are
  usable.
- [ ] **P9.3 — Add entities intentionally.** Searching/expanding does not automatically
  persist every visible node. The analyst chooses “Add to investigation.” Included nodes
  have a visible marker.
- [ ] **P9.4 — Edit annotations as plain text.** Save explicitly or with a documented
  debounce. Show saving/saved/error state. Never use `dangerouslySetInnerHTML` to render
  annotation content.
- [ ] **P9.5 — Save the current layout.** Serialize only finite x/y positions for included
  nodes, send one atomic mutation, and update local version from the response.
- [ ] **P9.6 — Restore deterministically.** Loading an investigation clears or confirms
  replacement of the current canvas, fetches included entities/edges needed for display,
  applies `preset` positions, and shows annotations. It must not run a force layout that
  immediately overwrites saved coordinates.
- [ ] **P9.7 — Handle unsaved work.** Warn before replacing a dirty investigation or
  navigating away if unsaved annotation/layout changes exist. A failed save remains dirty
  and offers retry.
- [ ] **P9.8 — Test component state.** Cover create validation, duplicate add,
  annotation error/retry, save-layout payload, restore positions, stale-version response,
  and auth expiry.
- [ ] **P9.9 — Add an end-to-end test.** Sign in; create investigation; search and add four
  fixture entities; annotate two; move nodes; save; reload the browser; sign in if
  required; reopen investigation; assert membership, text, and positions within a small
  pixel tolerance.
- [ ] **P9.10 — Add accessibility basics.** All controls have labels, keyboard focus is
  visible, status changes are announced, and graph information has a textual selected-
  node/edge alternative.

### Acceptance criteria

- [ ] The automated create-to-reload flow passes against a fresh database.
- [ ] Visible-but-not-added exploration nodes do not appear after investigation reload.
- [ ] Four included nodes, two annotations, and saved positions restore correctly.
- [ ] Duplicate add does not create a duplicate item in client or database state.
- [ ] Failed saves show an error and preserve unsaved local work.
- [ ] Annotation HTML-like text is displayed literally, not executed.
- [ ] Frontend lint, unit/component tests, typecheck, build, and browser tests pass.
- [ ] `docs/verification/phase-9.md` contains test results and before/after screenshots.

### Failure guidance

- If restored positions move, inspect automatic layout execution after the `preset`
  layout.
- If annotations vanish only after refresh, inspect the API reload query rather than
  adding browser persistence.
- If optimistic responses diverge from server state, prefer refetching the investigation
  after a mutation until cache update logic is proven.

---

## Phase 10 — Package and verify the complete local system

### Purpose

Fulfill the one-command-demo promise that the old plan specified but never scheduled.

### Prerequisites

- Independent local commands for API, ingest, web, and tests pass.
- Required behavior from Phases 2–9 is complete.

### Deliverables

- `api/Dockerfile`
- `ingest/Dockerfile`
- `web/Dockerfile` and web-server proxy configuration
- complete `docker-compose.yml`
- one-shot schema and demo-fixture jobs
- optional one-shot live-ingest profile
- service health checks
- `scripts/demo-up.sh`, `scripts/demo-down.sh`, and `scripts/demo-smoke.sh`
- automated end-to-end Compose test

### Runtime services

| Service | Role | Start behavior |
|---|---|---|
| `neo4j` | Graph database | health-checked; persistent named volume; localhost-only admin/browser ports |
| `schema-init` | Apply idempotent constraints/indexes | one-shot after Neo4j is healthy |
| `demo-seed` | Load deterministic fixture | one-shot in the `demo` profile after schema succeeds |
| `api` | Spring GraphQL | starts after schema; health endpoint; Neo4j hostname uses Compose DNS |
| `web` | Static React app and `/graphql` reverse proxy | starts after API is healthy; only user-facing port |
| `ingest` | Python batch image | does not stay running; invoked with `docker compose run --rm` under `live-data` profile |

### Tasks

- [ ] **P10.1 — Create multi-stage images.** Build dependencies in toolchain images and
  copy only runtime artifacts into final images. Run application processes as non-root
  where practical. Pin every base image.
- [ ] **P10.2 — Add API health.** Use a bounded health endpoint that proves the process is
  ready and, if appropriate, Neo4j is reachable. Do not expose sensitive configuration.
- [ ] **P10.3 — Add same-origin proxying.** The web container serves static assets and
  proxies `/graphql` to `api:8080`. The browser never needs Compose-internal hostnames or
  broad CORS.
- [ ] **P10.4 — Add initialization jobs.** `schema-init` fails the stack if schema cannot
  apply. `demo-seed` is idempotent. API startup does not race an uninitialized schema.
- [ ] **P10.5 — Complete environment configuration.** `.env.example` documents every
  variable, safe example format, whether required, and which service consumes it. Scripts
  fail fast if required passwords remain examples or are too short.
- [ ] **P10.6 — Bind ports conservatively.** Expose only the web port by default. Bind
  Neo4j Browser/Bolt and API debug ports to `127.0.0.1` only when enabled for development.
- [ ] **P10.7 — Implement demo scripts.** `demo-up.sh` checks prerequisites, builds,
  starts the demo profile, waits with a timeout, and runs smoke checks. `demo-down.sh`
  preserves data by default and requires `--volumes` for destructive cleanup.
- [ ] **P10.8 — Implement live-ingest commands.** The README/script names source commands
  explicitly. Live ingestion is never an automatic side effect of starting the demo.
- [ ] **P10.9 — Add smoke checks.** Verify web HTTP, authenticated GraphQL search,
  fixture path, source provenance, investigation create/reload, and unauthenticated 401.
- [ ] **P10.10 — Test clean-volume startup.** Use a unique Compose project name and empty
  volumes. Do not rely on the developer’s existing Neo4j data.
- [ ] **P10.11 — Test restart behavior.** Restart API/web without deleting volumes and
  confirm the saved investigation survives. Re-run schema/seed and confirm no duplicates.
- [ ] **P10.12 — Run browser E2E against packaged services.** The Phase 9 flow must pass
  through the web proxy, not Vite’s development server.

### Intended reviewer commands

```bash
cp .env.example .env
# Edit NEO4J_PASSWORD and ANALYST_PASSWORD in .env.
./scripts/demo-up.sh
```

The script prints the local URL and next actions. Live import is separate:

```bash
docker compose --profile live-data run --rm ingest source run ofac --write
docker compose --profile live-data run --rm ingest source run eu --write
docker compose --profile live-data run --rm ingest source run un --write
```

### Acceptance criteria

- [ ] From empty volumes, `./scripts/demo-up.sh` exits 0 within its documented timeout.
- [ ] The script reports healthy Neo4j, schema, API, and web services.
- [ ] The packaged UI completes search, expansion, provenance, and investigation reload.
- [ ] The same browser test passes against packaged services.
- [ ] Re-running schema and demo seed changes no fixture counts.
- [ ] Restarting runtime services preserves the investigation.
- [ ] No live source download occurs during default demo startup or automated unit tests.
- [ ] No required service uses `localhost` to address another container.
- [ ] No secret appears in an image layer inspection, frontend assets, logs, or committed
  files.
- [ ] `docs/verification/phase-10.md` records the clean project name, image identifiers,
  health status, smoke output, and E2E result.

### Failure guidance

- If API works on the host but not in Compose, inspect `bolt://neo4j:7687`, dependency
  health, and environment names before changing Java code.
- If web returns 502, inspect API health and reverse-proxy upstream name.
- If an old graph makes tests pass, repeat with a unique Compose project and empty named
  volumes.
- If bind-mounted Neo4j folders fail permissions, use the documented named volume for the
  default path rather than requiring host ownership changes.

---

## Phase 11 — Documentation, release audit, and handoff

### Purpose

Prove that a new reviewer can understand and run the project from repository documents,
and that every v1 promise has direct evidence.

### Prerequisites

- Phase 10 cold-start proof passes.

### Deliverables

- complete root `README.md`
- `docs/architecture.md`
- `docs/data-model.md`
- `docs/ingestion.md`
- `docs/entity-resolution.md`
- `docs/security-and-limitations.md`
- `docs/demo-scenario.md`
- screenshots/GIF with no secrets or unintended personal data
- completed verification directory
- final requirement traceability matrix

### README structure

1. what Nexus is and is not;
2. screenshot/GIF of the fictional demo;
3. prerequisites with tested versions;
4. three-command quick start;
5. login and analyst workflow;
6. deterministic demo versus live imports;
7. data-source table with publisher, landing URL, format, and retrieval behavior;
8. architecture summary and service boundaries;
9. test/verification commands;
10. common troubleshooting;
11. security, ethical, accuracy, and licensing limitations;
12. links to the detailed docs and plan.

### Tasks

- [ ] **P11.1 — Replace placeholder docs with observed behavior.** Do not document a
  planned endpoint or command as implemented. Keep planned/optional work clearly labeled.
- [ ] **P11.2 — Explain the architecture in plain language.** Include why Python is a
  batch writer, why Spring cannot edit source data, why source records survive resolution,
  and why the browser receives both nodes and edges.
- [ ] **P11.3 — Explain the data model.** Include all Section 8 labels, relationships,
  IDs, provenance flow, and at least one complete fictional example.
- [ ] **P11.4 — Explain ingestion.** Include cache paths, manifests, hashes, dry run,
  write run, repeat-run meaning, active/inactive behavior, and upstream drift failures.
- [ ] **P11.5 — Explain resolution.** Define normalization, transliteration, blocking,
  features, review, precision/recall, link audit fields, and non-transitive behavior with
  a worked fictional pair.
- [ ] **P11.6 — Explain security and limitations.** State demo auth limits, local-only
  ports, secret handling, query limits, OSINT interpretation, no compliance claim, and
  data licensing responsibility.
- [ ] **P11.7 — Write the demo story.** Use only the fictional Avery Stone scenario by
  default. Describe exactly what to search, which node to expand, what evidence to inspect,
  and how to save/reload an investigation.
- [ ] **P11.8 — Add source references.** Include official landing pages and the exact
  source configurations used by the importer. Record that direct URLs can move and how
  validation detects it; do not tell readers to “search for the current URL.”
- [ ] **P11.9 — Add troubleshooting from real failures.** At minimum cover missing
  `.env`, wrong Python interpreter, Java `Node` collision history, frozen-lock mismatch,
  Neo4j index state, HTML returned instead of XML, namespace drift, Compose DNS, 401, and
  stale volumes.
- [ ] **P11.10 — Perform an independent cold walkthrough.** A person/process that did not
  rely on developer shell history follows only README commands from an empty project/volume
  state. Record every correction, rerun from zero, and keep only the final passing proof.
- [ ] **P11.11 — Audit traceability.** For every Definition of Done row, link a test,
  command output, screenshot, schema query, or document section that directly proves it.
- [ ] **P11.12 — Audit placeholders and secrets.** Search for TODO placeholders,
  `NotImplementedError`, unsupported-operation stubs, example passwords used as real
  defaults, hard-coded Authorization headers, and raw source files. Classify every hit.

### Acceptance criteria

- [ ] A reviewer using only the README reaches the fictional demo and completes the saved
  investigation flow.
- [ ] All commands in docs were copied and run exactly as written during the cold test.
- [ ] Every source has a direct official landing-page link and its configured download
  behavior; understanding the importer requires no external search.
- [ ] The architecture, data model, ingestion, resolution, security, and limitations docs
  define their specialized terms.
- [ ] Screenshots contain no credentials, local filesystem secrets, or unintended real
  personal data.
- [ ] All phase verification records exist and match current commands.
- [ ] Required-scope searches find no unclassified placeholder implementation.
- [ ] The traceability matrix has no “assumed,” “manual someday,” or blank evidence row.
- [ ] `./scripts/verify.sh`, Compose smoke, and packaged browser E2E all pass once more.
- [ ] `docs/verification/phase-11.md` records the final audit and independent walkthrough.

### Failure guidance

- If README steps require undocumented knowledge, fix the README or script; do not count
  verbal help as a pass.
- If a feature exists only in source but cannot be reached through the packaged demo, it
  is not complete.
- If a test is green but does not cover the requirement’s scope, add the missing test or
  use stronger evidence.

---

## Optional A — OpenCorporates and news enrichment

This work is outside the v1 critical path. Mark `[S]` if skipped; v1 remains complete.

### Preconditions

- Core phases are complete or the owner explicitly prioritizes enrichment.
- A human confirms API access terms, rate limits, caching, attribution, and redistribution
  for OpenCorporates.
- A human confirms the news corpus may be stored and processed.

### Safer design

- OpenCorporates facts enter as their own Dataset/ImportRun/SourceRecord provenance, not
  direct unexplained edits to sanctions entities.
- News NER produces `Mention`/candidate artifacts or a review queue, not high-confidence
  Entity nodes.
- Extracted mentions do not imply identity, sanctions status, ownership, or wrongdoing.
- The corpus uses public-domain, licensed, or original text; do not copy full copyrighted
  articles.

### Acceptance criteria if implemented

- [ ] Access/licensing decisions are documented.
- [ ] Rate limiting, timeout, retry/backoff, and cache behavior are tested.
- [ ] Every enrichment fact has source provenance.
- [ ] NER precision is evaluated on a labeled sample; “five entities per article” is not
  used as a quality metric.
- [ ] Candidate mentions remain reviewable and cannot pollute accepted entity links.
- [ ] Core verification still passes without API tokens or the optional corpus.

---

## Optional B — Entity-resolution article

Write this only after Phase 7 has real evaluation output. A useful article contains:

1. the source-record versus entity distinction;
2. why all-pairs comparison is too large;
3. blocking keys and measured blocking recall;
4. missing versus conflicting evidence;
5. one accepted, one review, and one rejected fictional example;
6. precision/recall with raw counts and limitations;
7. why Nexus links rather than merges;
8. a diagram from raw records through review to graph edges.

Acceptance is a reviewed draft linked from README. Publishing to an external platform is
not required for v1 and requires separate authorization.

---

## 12. Risk register and trigger actions

| Risk | Early signal | Required response |
|---|---|---|
| Upstream URL or schema drift | redirect to new host, HTML body, unexpected root/namespace, sudden zero count | fail before write; retain prior active state; update source config/fixture only after official verification |
| False identity link | hard negative auto-accepted, identifier conflict ignored | stop apply; tighten rule; rerun held-out evaluation; never hide by collapsing nodes |
| Provenance loss | entity exists without SourceRecord/ImportRun path | fail invariants and import; repair model before UI work |
| Query explosion | unbounded traversal, large response, slow integration test | enforce hop/node/edge limits and relationship allowlists; report truncation |
| Secret disclosure | password in bundle/log/snapshot/commit | rotate secret, remove artifact/history where authorized, add regression scan |
| Toolchain drift | lockfile changes on verification, wrong Python/Node/Java | stop feature work; restore version files/frozen install |
| Data/license uncertainty | unclear redistribution or access terms | Question for a Human; do not commit or bypass controls |
| Personally identifying data in tests | real names/addresses in fixtures or screenshots | replace with fictional values; keep approved public demo separate |
| Compose passes only with old state | clean-volume failure | use unique project/volumes; fix initialization and readiness |
| Small evaluation overclaim | accuracy percentage without raw counts or held-out split | add counts/split/limitations; remove production claim |

---

## 13. Definition of Done and traceability

Nexus v1 is complete only when every required row is checked with direct evidence.

| Requirement | Owning phase | Required evidence |
|---|---:|---|
| Human scope, identity, persistence, auth, and data decisions are explicit | 0 | answered QH section + ADRs |
| Java, Python, web, and Compose baselines are reproducible | 1 | frozen builds and version/lock files |
| Graph schema represents entities, provenance, identity links, and investigations consistently | 2 | named schema objects + invariant tests |
| Offline fixture has a valid person→organization→organization→vessel path | 2 | exact fixture query and counts |
| Search, detail, neighborhood, and shortest path are bounded and authenticated | 3 | GraphQL/security integration tests |
| Graph UI renders nodes and edges and preserves positions during expansion | 4 | component + browser vertical-slice tests |
| OFAC import is safe, reconciled, traceable, and idempotent | 5 | fixture/live reports + repeat-run proof |
| EU and UN imports independently meet the same quality contract | 6 | per-source reports + repeat-run proof |
| Resolution is non-destructive, reviewable, and evaluated on held-out labels | 7 | metrics, review file, apply test, unchanged node counts |
| Investigation API persists authorized relationship properties without public-data mutation | 8 | mutation/reload/auth boundary tests |
| UI creates, annotates, saves, and restores an investigation | 9 | packaged browser create-to-reload test |
| One command starts a healthy fictional demo from empty volumes | 10 | clean Compose smoke and health evidence |
| Documentation is self-contained and independently reproduced | 11 | cold walkthrough + final audit |
| Optional enrichment is either verified or marked skipped | Optional A | `[x]` evidence or `[S]` |
| Optional article is either completed or marked skipped | Optional B | `[x]` link or `[S]` |

### Final release checklist

- [ ] All required Phase 0–11 acceptance criteria are checked.
- [ ] Optional A and B are explicitly `[x]` or `[S]`.
- [ ] No required evidence relies solely on a manual claim when an automated check is
  feasible.
- [ ] Live source manifests identify exactly what data was tested, but raw files are not
  committed.
- [ ] A fresh reviewer can understand every term and execute every documented command
  without searching for missing instructions.
- [ ] Limitations prominently state: local demo, not compliance software, possible
  matches are not facts, and public data may change.
- [ ] The final packaged E2E test and `./scripts/verify.sh` pass against current files.

Only after this checklist is satisfied should the implementation be described as “Nexus
v1 complete.”
