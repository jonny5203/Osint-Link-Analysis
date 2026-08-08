# Security and limitations

Nexus is designed as a local, single-machine, single-analyst demonstration. Its current
security controls reduce accidental exposure during local use; they do not make it a
production identity, sanctions-compliance, or case-management system.

## Security model

- The Spring API creates one in-memory `ANALYST` account from `ANALYST_USERNAME` and
  `ANALYST_PASSWORD` when it starts.
- Every `/graphql` and GraphiQL request requires HTTP Basic authentication.
- Server sessions and form login are disabled; each request is authenticated
  independently.
- The browser constructs the Basic header from UTF-8 credentials and keeps it only in
  the active Apollo client.
- Signing out clears the Apollo cache and stops that client.
- The web client uses relative `/graphql` requests through the Vite proxy; credentials
  and API hostnames are not compiled into production assets.
- Neo4j ports are bound to `127.0.0.1` by Docker Compose.
- GraphQL inputs are length/range checked, and Lucene search syntax is escaped.
- Cypher relationship patterns come from a server-side allowlist, not browser input.

The disposable browser verification checks that generated credentials do not appear in
local storage, session storage, or the built frontend assets.

## Deployment limitations

HTTP Basic over plain local HTTP provides no transport encryption. Anyone able to
observe that traffic can recover the credentials. Do not expose ports 5173, 8080, 7475,
or 7687 to an untrusted network. A production deployment would require TLS, an external
identity provider, per-user authorization, secret management, audit logging, hardened
images, patch management, and an explicit network policy.

The current browser and supported GraphQL surface are read-only. Saved investigations,
annotations, multi-user ownership, and authorization between users are not supported in
the shipped workflow.

GraphiQL is disabled in the default Spring configuration. The development profile may
enable it, but Spring Security still requires analyst credentials.

## Data and analytical limitations

- The bundled demo is entirely fictional and supports no factual claim about a real
  person, organization, address, or vessel.
- A graph edge records a claim with provenance; it does not prove the claim is current,
  complete, or legally significant.
- `POSSIBLE_MATCH` is an uncertain lead. It must never be described as a verified identity
  or used to collapse source entities.
- An active source record causes the UI's sanctioned styling, but the marker is not a
  legal determination and does not replace checking the original publisher.
- Absence from Nexus is not evidence that an entity or relationship does not exist.
- Shortest path reports graph connectivity, not causation, control, wrongdoing, or
  beneficial ownership beyond the stored edge meanings.

Nexus does not provide legal advice, sanctions screening certification, know-your-
customer approval, or a due-diligence conclusion.

## Live-data limitations

The Python package contains planned source-adapter and resolution structure, but its
top-level source and resolve commands currently return a not-implemented error. The
supported run path loads only the committed fictional fixture. Do not infer that live
OFAC, EU, or UN retrieval is available because source-specific modules exist in the tree.

Before live data becomes supported, each source needs documented licensing and
redistribution rules, download integrity checks, schema-drift handling, repeatable import
manifests, retention rules, and end-to-end verification. Users remain responsible for
lawful collection, minimization, retention, and use of any data they later add.

## Secrets and local data

- Never commit `.env`; it is intentionally ignored.
- Replace every example password before starting services.
- Avoid putting passwords directly in shell history on shared systems. Prefer a local
  secret-loading mechanism appropriate to your environment.
- `docker compose down` preserves the named Neo4j volumes.
- `docker compose down --volumes` deletes local Nexus graph data and is intentionally
  destructive.
- Changing `NEO4J_PASSWORD` does not change the password stored in an existing volume.
  Reuse the original value or explicitly reset the local volume.

## Reporting a security issue

Do not include credentials, real personal data, or unpublished source records in a bug
report. Provide the smallest fictional reproduction possible and describe the affected
boundary: browser, proxy, API authentication, GraphQL validation, or Neo4j data access.
