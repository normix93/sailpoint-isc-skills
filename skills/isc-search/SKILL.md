---
name: isc-search
description: SailPoint Identity Security Cloud (ISC/IdentityNow) Search reference. Use when someone needs a search query (identities, accounts, access profiles, entitlements, roles, events/audit, account activities, workflow history), asks about query syntax (nested @accounts/@access, .exact, ranges, wildcards, _exists_), searchable fields, POST /search/v1 bodies, paging past 10,000 results, aggregations, innerHit, or saved/scheduled searches.
---

# SailPoint ISC Search

Search runs on Elasticsearch over denormalized indices. Use it in the UI search bar, in saved/scheduled searches, in workflows (Get List of Identities, Get Access), and through `POST /search/v1`.

## How to answer

1. Pick the **index** (table below) — the object you want back, not the one you filter on (identities *with* an AD account → index `identities` + `@accounts(...)`).
2. Build the query with the syntax rules; use only fields listed in `references/searchable-fields.md`.
3. For the API, give the full body with `indices`, `query.query`, `sort`, `queryResultFilter.includes`, and the paging plan.
4. Warn about the traps: case sensitivity (`.exact`), multi-word terms without quotes become OR, nested conditions must sit inside the same `@…( )`, index lag after writes.

## Indices

| `indices` value | Contents | Notes |
|---|---|---|
| `identities` | identities with nested `@accounts`, `@access`, `@apps` | most queries |
| `accessprofiles` | access profiles (`@entitlements`, `@apps`) | |
| `entitlements` | entitlements (`@accessModelMetadata`) | `privilegeLevel.*`, `owners.*` |
| `roles` | roles (`@entitlements`, `@dimensions`, `@accessModelMetadata`) | |
| `events` | audit events | kept ~1 year + current month; filter on `action`, `technicalName`, `type`, `actor.name`, `target.name`, `created` |
| `accountactivities` | account activities (requests, refreshes, LCS changes…) with nested `@accountRequests`, `@originalRequests`, `@expansionItems`, `@approvals` | completed actions kept 7 days |
| `workflowsummaries` | workflow executions (closest API index to the UI's Workflow History category — check returned fields) | UI history: 90 days |
| (UI only) Cloud Resources | CIEM resources | needs CIEM |

API enum (Nov 2026): `accessprofiles`, `accountactivities`, `entitlements`, `events`, `identities`, `roles`, `workflowsummaries`, `*`. Re-check in `references/search-request-schema.md` (field `indices`) or `isc-api` → `endpoints/search.md`.

## Query syntax (SailPoint query string)

| Rule | Example |
|---|---|
| `field:term`, no spaces around the colon | `attributes.department:Sales` |
| nested object fields | `manager.name:amanda.ross`, `source.name:"Active Directory"` |
| nested arrays need `@type( )`; all conditions on the same item go inside one group | `@accounts(source.name:"Active Directory" AND disabled:true)` |
| AND / OR / NOT uppercase (or `&&` `||` `!`); no operator = OR | `@access(name:VPN) AND NOT attributes.cloudLifecycleState:inactive` |
| phrases need double quotes (single quotes are literal) | `attributes.location:"sao paulo"` |
| grouping | `lastName:(trent OR primrose)` |
| wildcards `*` `?` (text only; inside double quotes behaviour varies — check the count, or use `.exact:/regex/`) | `name:j*n`, `attributes.email:*@acme.com` |
| comparison / ranges | `accountCount:>12`, `created:[2026-01-01 TO 2026-03-31]`, `{ }` exclusive |
| date math | `created:[now-30d TO now]`, `attributes.endDate:[now TO now+1y]` |
| exact, case-sensitive (not on booleans, numbers, `email`, `id`, `phone`, `employeeNumber`, `processingState`, `type`, `tags`) | `name.exact:"jon-smith"`, `@accounts(source.name.exact:"AD")` |
| null / not null | `_exists_:attributes.endDate`, `NOT _exists_:manager.name` |
| regex with special characters | `attributes.lastname.exact:/.*-.*/` |
| escape `:` in times | `created:2026-01-01T10\:00\:00Z` |

Search is case-insensitive unless `.exact`; a regex with capitals needs `.exact`.

## API body

```json
POST /search/v1?limit=250&count=true
{
  "indices": ["identities"],
  "query": { "query": "attributes.cloudLifecycleState:active AND @accounts(source.name.exact:\"Active Directory\" AND disabled:true)" },
  "queryResultFilter": { "includes": ["id", "name", "attributes.email", "accounts.source.name"] },
  "sort": ["id"]
}
```

- `limit`: up to 10 000 per call (always set it explicitly; send `count=true` to read `X-Total-Count`).
- `offset` paging needs a `sort`; **beyond 10 000 results use `searchAfter`** = values of the sort fields of the last record (`"sort": ["id"]`, `"searchAfter": ["2c9180835d38ca0c015d606b50851b1e"]`).
- `queryType`: `SAILPOINT` (default, query string above), `DSL` with `queryDsl` (Elasticsearch Query DSL — handy for events), `TEXT`, `TYPEAHEAD`.
- `query.innerHit` (`{"type": "access", "query": "source.name:Finance"}`) returns only the matching nested items.
- Large ID lists: the query is limited to roughly 800 terms.
- Fields prefixed `_` (`_type`, `_index`) are internal; don't rely on them.
- Results can include partial matches: compare the exact value client-side when it matters.
- The index is updated asynchronously: read-after-write via the object's GET endpoint, not search.
- Also: `POST /search/v1/count`, `POST /search/v1/aggregate` (aggregations or `aggregationsDsl`), `GET /search/v1/{index}/{id}`. Saved searches `/saved-searches/v1`, scheduled `/scheduled-searches/v1` (results e-mailed, and the `idn:saved-search-complete` trigger fires).

## Ready-made queries

| Need | Query (index) |
|---|---|
| active identities without manager | `attributes.cloudLifecycleState:active AND NOT _exists_:manager.name` (identities) |
| terminated but with enabled AD account | `attributes.cloudLifecycleState:terminated AND @accounts(source.name.exact:"Active Directory" AND disabled:false)` (identities) |
| who has an entitlement | `@access(type:ENTITLEMENT AND source.name:"Active Directory" AND name.exact:"VPN Users")` (identities) |
| privileged access holders | `@access(privileged:true)` (identities) |
| uncorrelated accounts on a source | `@accounts(source.name:"X")` won't find them — search identities only covers correlated accounts; use `GET /accounts/v1?filters=sourceId eq "…" and uncorrelated eq true` |
| entitlements without owner | `NOT _exists_:owner.name` (entitlements) |
| requestable roles not enabled | `requestable:true AND enabled:false` (roles) |
| who changed a role last month | `technicalName:ROLE_UPDATE_PASSED AND created:[now-1M TO now]` (events) |
| failed provisioning on a source in 7 days | `@accountRequests(source.name:"X" AND result.status:failed) AND created:[now-7d TO now]` (accountactivities) |
| failed workflow executions | `status:Failed AND workflowName:"My Workflow"` (workflowsummaries) |

Verify field names against `references/searchable-fields.md` before relying on a query; events use `action` *or* `technicalName` depending on the event (`references/audit-events-reference.md`).

## Lint before delivering

```bash
python3 scripts/lint_query.py '<query>' --index identities
```
Catches API-filter syntax in search (`eq`, `==`), lowercase and/or, spaces around `:`, unbalanced quotes/parentheses, the same nested object split across separate `@groups`, `.exact` on unsupported fields, nested objects that don't exist on the index.

## Reference map

| File | Contents |
|---|---|
| `references/searchable-fields.md` | fields per index: first-level, second-level, nested |
| `references/audit-events-search.md` | searching the events index with Query DSL, key fields |
| `references/audit-events-reference.md` | every audit event name, type, and whether to search by `action` or `technicalName` |
| `references/search-request-schema.md` | generated schema of the `POST /search/v1` body |

Not affiliated with SailPoint. Docs: https://documentation.sailpoint.com/saas/help/search/index.html, https://developer.sailpoint.com/docs/api/standard-collection-parameters#paginating-search-queries
