# Infor Connector — Connector Discovery

**Discovery date:** 2026-08-24
**Release scope:** Tier 1 + Tier 2, bounded by public documentation availability
(Infor's deeper per-product API docs sit behind a partner portal — see §4).
**Related task:** BBW Imperal Apps #2410.

## 1. What "Infor" actually is

Infor is NOT one product but a portfolio of vertical (industry-specific) ERP product
lines under one company (Koch Industries-owned): Infor CloudSuite Industrial/LN
(manufacturing), Infor CloudSuite Healthcare, Infor M3, Infor SunSystems (finance), and
others. These are unified — loosely, at the infrastructure level — by **Infor OS**, a
shared platform providing identity, workflow, and API gateway services across whatever
CloudSuite products a customer has licensed.

## 2. Chosen integration surface

**Infor OS / ION API** (Infor Operating Service, ION API Gateway) is the common,
product-agnostic REST entry point Infor documents for external integration across its
CloudSuite portfolio, rather than reverse-engineering each vertical product's own
internal API. This connector targets the **ION API Gateway's generic REST surface**:
callers reach product-specific endpoints (e.g. `LN`, `M3`, `SunSystems`) via ION's
routing, using ION API credentials — this keeps the connector honest about only
exposing what is uniformly documented, instead of guessing at closed per-product schemas.

## 3. Auth model

OAuth2 via **ION API Gateway credentials** — a client/service account generated in
**ION Desk** (or Infor Ming.le admin), yielding a `.ionapi` credential file containing:
`ti` (tenant id), `cn` (client id), `cs` (client secret), `pu` (portal url / OAuth token
endpoint), `saak`/`sask` (service account access key / secret key) for the
service-account flow. This is architecturally different from every other connector in
the portfolio (no other app uses a downloadable multi-field credential bundle) — the
connect form must accept either the raw `.ionapi` JSON pasted in, or its individual
fields, and must not assume the shape matches OAuth2 client_credentials used elsewhere.

## 4. Known limitation — documentation gate (stated honestly, not guessed around)

Infor's authoritative ION API reference (Infor Xtreme / Infor Concierge portal, and
much of docs.infor.com's deeper technical reference) requires an active Infor customer
or partner login. Public, unauthenticated sources (infor.com marketing pages, the
publicly-crawlable subset of docs.infor.com, and third-party ION API integration
write-ups) confirm ION API Gateway's existence, its OAuth2/.ionapi credential model, and
generic REST calling convention, but do NOT provide exhaustive per-product endpoint
catalogs. **Decision:** ship a **generic ION API Gateway REST bridge** (arbitrary
path/method calls against the gateway, following the same "generic call" pattern used
elsewhere in the portfolio for closed/variable APIs) plus an access-audit that reports
which product routes actually respond for a given tenant, rather than inventing
resource-specific tools (e.g. fake "list_manufacturing_orders") that cannot be verified
against real documentation.

## 5. Official sources consulted (publicly accessible)
- infor.com/products/infor-os — Infor OS platform overview
- docs.infor.com (public subset) — ION API Gateway conceptual overview
- Third-party technical write-ups confirming `.ionapi` credential shape and OAuth2 flow

## 6. Tier plan
- **Tier 1:** connect (paste `.ionapi` fields or JSON), disconnect, list_connections,
  generic `call_ion_api_operation` (method + path + body), `audit_ion_api_access`
  (probe a caller-supplied list of candidate product routes, report which respond).
- **Tier 2:** none beyond Tier 1 — deeper per-product tools are explicitly deferred
  until partner-level documentation can be obtained and verified, per the task's
  explicit instruction not to guess behind the closed portal.
