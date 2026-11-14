---
name: isc-api
description: SailPoint Identity Security Cloud (ISC, formerly IdentityNow) REST API reference. Use when someone asks which endpoint to call, which filters/sorters/operators an endpoint accepts, how pagination, auth, scopes, rate limits, PATCH or API versions work, or writes/reviews code that calls api.identitynow.com (access requests, identities, accounts, sources, roles, work items, certifications…).
---

# SailPoint ISC REST API

Generic, tenant-independent reference. The bundled files under `references/` are generated from SailPoint's public OpenAPI specs and developer docs (see the banner at the top of each file for the commit and date).

## How to answer an endpoint question

Typical questions: *"endpoint for getting access requests: what can I filter on, how do I paginate?"*

1. **Find the endpoint.** Grep `references/endpoint-index.md` for the resource (e.g. `access-request`, `work-items`, `identities`). Prefer the current per-service paths (`/{service}/v{N}/…`).
2. **Open the service file** `references/endpoints/<service>.md` (the first path segment, e.g. `endpoints/access-request-status.md`). Each operation lists: operationId, scopes, user levels, every query parameter, the exact **`filters` fields with their allowed operators**, the **`sorters` fields**, `limit` max/default, body content type and response type.
3. **Answer with:** method + path, required scope/user level, the filterable fields table, sortable fields, a pagination loop, one ready-to-run example (curl or the user's language). Quote filter fields exactly as listed; never invent a field that isn't there.
4. If several endpoints could fit, say so and explain the difference (see "Common look-alikes" below).
5. If the `sailpoint-isc-docs` MCP tools (`search_endpoints`, `get_endpoint`, `get_schema`) are available in the session, use them to confirm against the live spec. Otherwise the bundled files are the source; mention their date if the answer depends on something recent.

## Common look-alikes (access requests)

| Need | Endpoint |
|---|---|
| Status of requests (requested-for/by, assigned-to, state) | `GET /access-request-status/v1` — filters `accessRequestId`, `accountActivityItemId`, `created`; query params `requested-for`, `requested-by`, `regarding-identity`, `assigned-to`, `request-state=EXECUTING` |
| Admin view of every request in the org (adds a `status` filter) | `GET /access-request-administration/v1` — experimental |
| Approvals waiting for / done by the caller | `GET /access-request-approvals/v1/pending`, `/completed` (filters `id`, `requestedFor.id`, `accessRequestId`, `created`, `modified`) |
| Submit, cancel, close requests | `POST /access-requests/v1`, `/access-requests/v1/cancel`, `/close`, `/bulk-cancel` |
| Approvals of the generic approval framework (workflows, non-access tasks) | `/generic-approvals/v1` |
| Manual provisioning tasks / work items | `GET /work-items/v1` (and `/completed`): only `limit`/`offset`/`count` and `ownerId` — **no `filters` or `sorters` documented**, so no guaranteed order: sort client-side (e.g. by `created`) and use `/work-items/v1/count` or `/summary` for totals |

Always check the service file: fields and operators differ per endpoint and change between versions.

## Core rules (apply to every call)

**Base URL and auth** — `https://{tenant}.api.identitynow.com`. Token: `POST /oauth/token` with `grant_type=client_credentials`, `client_id`, `client_secret` in a form-urlencoded body. Send `Authorization: Bearer <access_token>`; refresh before `expires_in`. PATs inherit the creating user's rights. Details: `references/guides/authentication.md`, scopes and user levels: `references/guides/authorization.md`.

**Versioning (since June 2026)** — per-service versions: `/accounts/v1`, `/access-requests/v1`, `/search/v1`… Legacy `/v3`, `/beta`, `/v2024`–`/v2026` still work until their announced end of support; map any legacy path with `references/versioning-map.md` (a few routes map to `v2`, e.g. `/access-request-config`). Don't use `/latest` in production. Experimental operations need `X-SailPoint-Experimental: true` (flagged **EXPERIMENTAL** in the endpoint files). Strategy: `references/guides/api-versioning-strategy.md`.

**Pagination** — list endpoints: `limit` (default and max **250**), `offset` (record-based, starts at 0), `count=true` → total in `X-Total-Count` header (costs extra, use only when needed). Loop until a page returns fewer than `limit` items, and always send a stable `sorters` (e.g. `id` or `created`) so pages don't shift. Search (`POST /search/v1`): `limit` up to 10 000 per call; beyond 10 000 results use `searchAfter` with a sort on a unique field — see the `isc-search` skill.

**Filters** — `filters=<expression>`, URL-encoded as a whole.
- Operators (lowercase only): `eq ne gt ge lt le` · `in` · `sw` (starts with) · `co` (contains) · `ca` (collection contains all) · `pr` (present) · `isnull`; combine with `and`, `or`, `not` and parentheses.
- Strings in double quotes: `name eq "Finance"`; lists: `id in ("a","b")`; dates unquoted ISO-8601: `created gt 2026-01-01T00:00:00Z`; booleans unquoted.
- Escape `"` as `\"` and `\` as `\\` inside values.
- **Only the fields/operators listed for that endpoint work**; anything else returns 400.
- Full syntax: `references/guides/standard-collection-parameters.md`.

**Sorters** — `sorters=name,-created` (`-` = descending), only listed fields.

**PATCH** — `Content-Type: application/json-patch+json`, body is a JSON Patch array (`add`, `remove`, `replace`, `move`, `copy`, `test`). `/array/-` appends; `replace` on an array replaces the whole array. Examples per object type: `references/guides/patch-requests.md`.

**Rate limits** — 100 requests per 10 s per client_id **and per API version** (some endpoints stricter) → `429` with `Retry-After`. Retry 429/5xx with backoff, refresh token once on 401, never retry other 4xx. See `references/guides/rate-limit.md`.

**Errors** — body has `detailCode`, `trackingId`, `messages[]`. Log `trackingId` (support asks for it). Branch on HTTP status, not message text.

**Async operations** — aggregations, imports, access requests, many bulk calls return a task/request id, not the result. Poll the status endpoint with a timeout; a 202 is not "done".

## Pagination snippet (adapt to the user's language)

```js
async function listAll(path, params = {}) {
  const out = [];
  for (let offset = 0; ; offset += 250) {
    const qs = new URLSearchParams({ ...params, limit: 250, offset, sorters: params.sorters ?? 'id' });
    const res = await fetch(`${BASE}${path}?${qs}`, { headers: { Authorization: `Bearer ${token}` } });
    if (res.status === 429) { await sleep((+res.headers.get('Retry-After') || 5) * 1000); offset -= 250; continue; }
    if (!res.ok) throw new Error(`${res.status} ${(await res.json()).trackingId}`);
    const page = await res.json();
    out.push(...page);
    if (page.length < 250) return out;
  }
}
// listAll('/access-request-status/v1', { 'requested-for': '<identityId>', filters: 'created ge 2026-01-01T00:00:00Z', sorters: '-created' })
```

`URLSearchParams` encodes the filter expression; don't hand-encode pieces of it (double encoding gives `%2522`).

## Check before you answer

`scripts/check_filter.py` validates a filter/sorter against the endpoint's spec and prints the encoded query string:

```bash
python3 scripts/check_filter.py "GET /access-request-status/v1" --filters 'created ge 2026-01-01T00:00:00Z' --sorters '-created'
python3 scripts/check_filter.py "GET /work-items/v1"          # what the endpoint supports
python3 scripts/check_filter.py --find access-request          # find endpoints
```
Run it whenever you hand someone a `filters` expression. If you can't run scripts, apply the same rules by reading the endpoint file.

## Reference map

| File | Use for |
|---|---|
| `references/endpoint-index.md` | every path grouped by service — start here |
| `references/endpoints/<service>.md` | full detail per operation: scopes, user levels, filters, sorters, body, response |
| `references/versioning-map.md` | legacy (`v3`/`beta`/`v202x`) → new path and version |
| `references/guides/standard-collection-parameters.md` | filters, sorters, pagination, search paging |
| `references/guides/patch-requests.md` | JSON Patch rules and examples |
| `references/guides/authentication.md`, `authorization.md` | tokens, PATs, OAuth flows, scopes, user levels |
| `references/guides/rate-limit.md` | throttling |

Related skills in this plugin: `isc-search` (search query syntax and indices), `isc-workflows`, `isc-event-triggers`, `isc-notifications`, `isc-transforms`, `isc-rules`.

Not affiliated with SailPoint. The official reference is https://developer.sailpoint.com/docs/api.
