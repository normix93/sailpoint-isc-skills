---
name: isc-nerm
description: SailPoint Non-Employee Risk Management (NERM, ex SecZetta, {tenant}.nonemployee.com) reference — how it differs from ISC Non-Employee Lifecycle Management, profiles and profile types, attributes, forms and pages, lifecycle and collaboration workflows and their actions, workflow sessions, risk scoring, users and roles, the NERM connectors to Identity Security Cloud, and the NERM REST API (ISC token or legacy key, nerm scopes, wrapped bodies, limit/offset/after_id paging, advanced search rules, audit query). Use when someone calls or debugs the NERM API, builds a NERM integration or workflow, syncs NERM to ISC, or mixes up NERM with ISC non-employee sources.
---

# SailPoint Non-Employee Risk Management (NERM)

NERM is a **separate SaaS product** (an ISC add-on, formerly SecZetta) at `https://{tenant}.nonemployee.com`. It
governs **profiles**: contractors, vendors, organizations, assignments, even assets, grouped by **profile type**, each
with its own attributes, forms, pages and **workflows**, plus per-attribute **risk scoring**. It is not ISC's
**Non-Employee Lifecycle Management** (`/non-employee-sources`, `/non-employee-records` on `api.identitynow.com`):
if the question uses those names, switch to the isc-api skill. Comparison and product facts: `references/overview.md`.

## Before answering an API question, check these

1. **Host and path**: `https://{tenant}.nonemployee.com/api/<resource>` (v1) or `/api/v2025/...` (only
   `/delegations` so far). Resources are snake_case: `/profiles`, `/profile_types`, `/ne_attributes`,
   `/workflow_sessions`, `/advanced_search/run`, `/audit_events/query`. `POST /profile` = one, `POST /profiles` = many.
2. **Auth**: bearer token. Recommended: ISC PAT → `POST https://{isc}.api.identitynow.com/oauth/token`
   (client_credentials) → JWT sent to NERM. Legacy NERM API keys are deprecated, have no scopes, and tenants created
   after June 2025 cannot use them.
3. **Scopes** (ISC tokens): `nerm:general:manage` (all), `nerm:api:read-only`, `profile-manager`, `profile-reader`,
   `workflow-operator` (only one besides manage that can **execute** workflow sessions), `configuration-manager`,
   `integration-partner` (create profiles only). Missing scope = 403 that does not name it.
4. **Bodies and responses are wrapped**: `{"profile": {...}}`, `{"profiles": [...]}`, `{"workflow_session": {...}}`,
   `{"advanced_search": {...}}`. Profile `attributes` are keyed by **attribute uid**.
5. **Paging**: `limit` (default 100, max 500 on `/profiles`), `offset`, `order`, `metadata=true` for `_metadata`.
   For full profile exports use `after_id` (not with `offset`, and only with `profile_type_id`/`updated_after`).
   There is no `filters=` expression language: plain query params, or advanced search for attribute conditions.
6. **Workflow sessions do not run unless `?run=true`** on `POST /workflow_sessions` (or a later PATCH).
7. Profile statuses are `Active`, `Inactive`, `On Leave`, `Terminated`; profile type categories `employee`,
   `non-employee`, `organization`, `assignment`, `other`.

Details, doc/spec inconsistencies and examples: `references/api-gotchas.md`. Every operation:
`references/endpoint-index.md` → `references/endpoints.md`; field names and enums: `references/schemas.md`.

## Product rules that change answers

- Four core profile types (Non-Employees, Organizations, Jobs, Assignments) cannot be deleted.
- Lifecycle workflows: Create, Update, Batch, Automated (no button, **once a day** at a region-fixed time, profile
  filters must all match). Collaboration workflows: Registration, Login, Password reset (external portal).
- **Status Change** applies immediately (put approvals first); **REST API** steps time out at 60 s; **Close Session**
  stops the workflow.
- Risk: off by default per profile type; only option-based attributes (drop-down, check boxes, radio, profile
  search/select) carry risk; overall = average of average impact and average probability; inherited risk from linked
  profiles can raise it.
- ISC sync: only person profile types become identities; Non-Employee Profile ID → Employee Number is the default
  correlation; archived profiles are never aggregated; extended attributes do not sync; the separate *NERM Users*
  connector manages NERM users and roles (as entitlements) from ISC.

## Checker

`scripts/check_nerm.py` (stdlib, never calls a tenant):

```bash
python3 scripts/check_nerm.py body.json                       # profile(s), advanced_search, workflow_session, audit_events, user(s)
python3 scripts/check_nerm.py --patch bulk.json               # bulk PATCH /profiles (items need id)
python3 scripts/check_nerm.py --url "GET https://acme.nonemployee.com/api/profiles?after_id=...&limit=500"
python3 scripts/check_nerm.py --scopes nerm:api:profile-reader --request "POST /workflow_sessions"
```

It reports missing wrappers, ISC NELM payloads or URLs used against NERM, ISC hosts, unknown paths and methods (with
the closest NERM endpoint), invalid statuses, categories, requester types and audit enums, names used where ids are
required, label-style attribute keys, advanced-search rules with the wrong operator for their attribute type,
`after_id` mixed with `offset` or filters, `limit` over 500, ISC-only parameters (`filters`, `count`, `sorters`),
workflow sessions that will not start, and whether a token's scopes allow a call. Enums come from
`scripts/nerm_api.json`, generated from SailPoint's NERM OpenAPI spec.

## References

| File | Use for |
|---|---|
| `references/overview.md` | NERM vs ISC NELM, data model, workflows and actions, risk scoring, ISC connectors, audit retention |
| `references/api-gotchas.md` | auth, scopes, wrappers, paging, advanced search, workflow sessions, users, known doc/spec issues |
| `references/endpoint-index.md` | GENERATED: every NERM operation (v1 and v2025) by tag |
| `references/endpoints.md` | GENERATED: parameters, body wrapper and response of each operation |
| `references/schemas.md` | GENERATED: profile, profile type, attribute, rules, risk, workflow, user, audit schemas |
| `references/api-guide/` | SailPoint's NERM API guide pages (authentication, authorization/scopes, getting started, pagination) |
