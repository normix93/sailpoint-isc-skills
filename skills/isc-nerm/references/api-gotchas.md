# NERM API: what trips people up

Hand-written, checked on 2026-11-15 against the generated `endpoints.md` / `schemas.md` (SailPoint's NERM OpenAPI
specs) and the API guide pages in `api-guide/`. Each point says where it comes from.

## Base URL and versions

- v1: `https://{tenant}.nonemployee.com/api/<resource>` — e.g. `GET https://acme.nonemployee.com/api/profiles`.
  The tenant is the host you use in the browser. **Not** `{tenant}.api.identitynow.com` (that is ISC).
- v2025: `https://{tenant}.nonemployee.com/api/v2025/...`; as of this build it contains only `/delegations`.
- Resource names are **snake_case, often singular for create**: `POST /profile` creates one, `POST /profiles` creates
  many; same for `/user` vs `/users`, `/role` vs `/roles`. Attribute endpoints are `/ne_attributes`.
- The guide pages' curl examples call `/api/v1/non-employee-sources` — that is the ISC NELM endpoint name and not in the
  NERM spec. Treat it as a placeholder; use the paths in `endpoint-index.md`.

## Authentication

- **Recommended**: an ISC access token. Create a personal access token in ISC, exchange it at
  `https://{isc-tenant}.api.identitynow.com/oauth/token` (client credentials), send `Authorization: Bearer <JWT>` to
  NERM. The token has the access of the ISC user who made the PAT; it expires (`expires_in`, ~12.5 min in the example).
- **Legacy NERM API keys** (Admin > System > Api in NERM): deprecated, no scopes. Per the admin help, tenants created
  after June 2025 must use ISC credentials, and FedRAMP customers cannot use NERM keys.
- The OpenAPI security scheme only describes ISC tokens; it does not list NERM keys.

## Scopes (ISC tokens only)

From `api-guide/authorization.md`. A token needs at least one `nerm:` scope.

| Scope | Gives |
|---|---|
| `nerm:general:manage` | Everything, including system configuration; overrides other scopes |
| `nerm:api:read-only` | Read on every resource type |
| `nerm:api:profile-manager` | Profiles R/W/D; read profile types, users & roles, advanced search |
| `nerm:api:profile-reader` | Read profiles, profile types, advanced search |
| `nerm:api:workflow-operator` | Read profiles, profile types, workflows, advanced search; read + **execute** workflow sessions |
| `nerm:api:configuration-manager` | Profile types and templates/configuration R/W/D; read users & roles |
| `nerm:api:integration-partner` | **Create** profiles only (no read/update/delete); read profile types |

Missing scope → `403` with a generic `{"error": "You do not have the permission to access this resource."}` (it never
names the scope). Audit events are readable only with `read-only` or `general:manage` (the audit search is a `POST /audit_events/query`; by the guide's method rule a POST is a write, so if `read-only` gets 403 there, only `general:manage` works).

## Request and response shape

- Every body is **wrapped**: `{"profile": {...}}`, `{"profiles": [ ... ]}`, `{"workflow_session": {...}}`,
  `{"advanced_search": {...}}`, `{"audit_events": {...}}`. Responses too: `GET /profiles` → `{"profiles": [...],
  "_metadata": {...}}`. Sending the bare object is the most common 400.
- `attributes` on profiles and workflow sessions is an object keyed by **attribute uid** (not label, not id). Values:
  text as string; profile/user select as the target id (array for multi-select); dates in the attribute's
  `date_format` (e.g. `"01/15/2020"`).
- Create profile: `profile_type_id` and `status` are required (spec).
- Bulk `PATCH /profiles` items need `id`. Large bulk calls can return a job; poll `GET /job_status?job_id=...`.
- Attachments and avatars are **multipart form uploads** with a `file` field, not JSON.
- Errors: `{"error": "..."}` and for validation `{"error": "...", "errors": {"attribute": "can't be blank"}}`.

## Pagination and filters (v1)

From `api-guide/pagination-metadata-filtering.md` and the spec:

- `limit` (default 100; max **500** on `/profiles`), `offset` (record-based), `order=<field>` (ascending).
- `metadata=true` adds `_metadata` with `limit`, `offset`, `total`, `next` (and `after_id` on profiles).
- `/profiles` also has **keyset paging**: `after_id=<uuid>` sorts by id ascending and **cannot be combined with
  `offset`**; other filters except `profile_type_id` and `limit` are ignored or rejected with 400 (so not with
  `status`, `name`, `archived`). `updated_after=YYYY-MM-DD` may be combined with `after_id`. Use it for full exports.
- With `metadata=true` the next `after_id` is in `_metadata`; it is `null` on the last page — stop there.
- Plain filters are query parameters named like the field (`?status=Active`, `?profile_type_id=...`, `?email=...`);
  there is **no** ISC-style `filters=` expression syntax.
- Inconsistency: the guide says `offset` starts at 0, the spec declares `minimum: 1`. Use 0 for the first page.
- The v2025 guide page about pagination is a copy of the ISC page (limit 250, `count=true`, `x-total-count`); it does
  not describe NERM. Use the v1 rules above.

## Advanced search (filtering profiles by attribute)

Rules reference attributes by **id**; look an attribute up by uid with `GET /ne_attributes/{uid}` (the path accepts
the id or the uid) or list them with `GET /ne_attributes`.

`POST /advanced_search/run` with `{"advanced_search": {"condition_rules_attributes": [ ... ]}}` (save with
`POST /advanced_search`, run a saved one with `GET /advanced_search/{id}/run`). All rules must match.

| Rule `type` | Keys | Operators |
|---|---|---|
| `ProfileStatusRule` | `comparison_operator`, `value` | `==`, `!=` |
| `ProfileTypeRule` | `comparison_operator`, `value` = profile type id | `==`, `!=` |
| `ProfileAttributeRule` (text) | `condition_object_type` `TextFieldAttribute`/`TextAreaAttribute`, `condition_object_id` = attribute id | `==`, `!=`, `>`, `<`, `start_with?`, `end_with?`, `include?` |
| `ProfileAttributeRule` (date) | `condition_object_type` `DateAttribute`, plus `secondary_value` before/after and `tertiary_value` days | `>`, `<`, `after`, `before` |
| `ProfileAttributeRule` (link) | `condition_object_type` Profile/Owner/Contributor Select/Search, `value` = linked id | `include?`, `exclude?` |
| `RiskRule` | `secondary_value` `OverallRisk`, `value` | `==`, `>`, `<` |

Known differences between guide and spec:

- The guide's examples use `"object_type": "NeAttribute"`; the spec uses `condition_object_type` with the attribute's
  type (`TextFieldAttribute`, ...). The checker accepts both and warns.
- Status values for the rule are documented as `Active`, `Inactive`, `Leave of absence`, `Terminated`, while profiles
  use `On Leave`.
- One guide example uses the operator `includes?`; the correct spelling is `include?`. Two guide examples miss a quote
  after `condition_rules_attributes` (invalid JSON).

## Workflow sessions (running a workflow from the API)

- `POST /workflow_sessions` with `{"workflow_session": {"workflow_id", "requester_id", "requester_type", ...}}` —
  all three are required. `profile_id` for update workflows, `profile_ids` for batch, `attributes` to prefill.
- **It does not start unless you add `?run=true`** (default false); otherwise you get a session in `new` that you can
  `PATCH /workflow_sessions/{id}?run=true` later.
- `requester_type`: `User`, `NeprofileUser`, `NeaccessUser`, `NeaccessRegistrant`.
- Executing sessions needs the `workflow-operator` scope (execute) or `general:manage`.

## Users

- `POST /user` needs `name`, `email`, `login`, `type` (`NeprofileUser` or `NeaccessUser`); `profile_id` and `password`
  are for portal users (not needed for `NeprofileUser`). `sailpoint_identity_id` links a user to an ISC identity.

## Rate limits

None are documented for NERM (checked 2026-11-15). Page with `limit`/`after_id` and back off on 429 anyway.
