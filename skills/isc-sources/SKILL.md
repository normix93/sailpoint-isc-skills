---
name: isc-sources
description: SailPoint Identity Security Cloud (ISC/IdentityNow) sources reference — source object and connector settings, account and entitlement schemas, account and entitlement aggregation (schedules, optimized vs unoptimized, delta, delete threshold), account correlation and manager correlation, uncorrelated accounts, create profile / provisioning policies (usage types, generators, field order), attribute sync, native change detection, source health statuses, the sources API, and SaaS connector commands/customizers. Use when someone onboards, configures, reviews or debugs a source, asks why accounts are not correlated, created, updated or deleted, or writes source JSON.
---

# SailPoint ISC sources

A **source** is ISC's connection to one system (AD, Entra ID, Workday, a JDBC database, a CSV file, a SaaS app).
It holds the connector settings, the **account schema** (and entitlement/group schemas), how accounts are matched to
identities (**correlation**), how new accounts are built (**create profile** = provisioning policy `CREATE`), which
attributes are kept in sync, and when data is read (**aggregation**). A source referenced by an identity profile is
**authoritative**: its accounts create identities.

## Anatomy (UI section → API)

| What | UI (Admin > Connections > Sources > *source*) | API (service `sources`, see `references/source-endpoint-index.md`) |
|---|---|---|
| Connection settings, cluster/VA, owner, governance group | Base Configuration, Connection Settings | `GET/PUT/PATCH /sources/v1/{id}` — object `source` |
| Account / group schema | Account Schema, Entitlement Types | `/sources/v1/{sourceId}/schemas` — object `schema`, `attributedefinition` |
| Aggregation and delete threshold | Account Management > Account Aggregation | `POST /sources/v1/{id}/load-accounts`, `/load-entitlements`, `/schedules`, status `GET /account-aggregations/v1/{id}/status`, field `deleteThreshold` |
| Correlation | Account Management > Correlation | `GET/PUT /sources/v1/{id}/correlation-config`; `managerCorrelationMapping` on the source |
| Uncorrelated accounts | Account Management > Uncorrelated Accounts | `POST /sources/v1/{id}/load-uncorrelated-accounts` (correlation file) |
| Create Account (create profile) and other policies | Account Management > Create Account | `/sources/v1/{sourceId}/provisioning-policies/{usageType}` (v2 by id: experimental) |
| Attribute sync | Account Management > Attribute Sync | `GET/PUT /sources/v1/{id}/attribute-sync-config`, `POST /sources/v1/{id}/synchronize-attributes` (both experimental) |
| Native change detection | Account Management > Native Change Detection | `/sources/v1/{sourceId}/native-change-detection-config` |
| Rules | (assigned by API) | fields `beforeProvisioningRule`, `accountCorrelationRule`, `managerCorrelationRule`; connector rules via `/connector-rules/v1` (see `../isc-rules`) |
| Health, connection test | source card, Test Connection | `GET /sources/v1/{sourceId}/source-health`, `POST /sources/v1/{sourceId}/connector/check-connection`, `ping-cluster`, `test-configuration`; `status` on the source |

Exact field names, enums and examples: `references/source-api-schemas.md` (generated from the OpenAPI spec).
Endpoint details (scopes, user levels, filters, bodies): `../isc-api/references/endpoints/sources.md`.

## Onboarding order (do it in this order, or redo work)

1. Create the source on the right **VA cluster**, owner and (optional) governance group; **Test Connection**.
2. **Discover / fix the account schema**: identity attribute (unique, stable), display attribute, which attributes
   are entitlements; add group/entitlement types.
3. Configure **correlation before the first aggregation** (changing it later needs an unoptimized aggregation).
4. Aggregate accounts, then entitlements; check uncorrelated accounts; correlate the rest with the correlation file.
5. Set the **delete threshold** and enable account deletion only after the first clean aggregations.
6. Build the **Create Account** profile (field order matters) and optional attribute sync, native change detection.
7. Authoritative source: map it in an identity profile, preview, then run identity processing.
8. Schedule aggregations.

## Rules that prevent most source problems

1. **Correlation is "any one pair matches", in order, Equals only**, case-insensitive by default. If none matches,
   ISC falls back to account name = identity `name`. Put the most reliable pair (employee ID) first.
2. **Optimized aggregation skips unchanged accounts**, including correlation. After changing correlation (or
   manager correlation) run one aggregation with `disableOptimization=true` (API only; UI runs are always optimized).
3. **Deletes happen only in full aggregations** and only if account deletion is enabled; above the threshold
   percentage the delete phase is skipped with a warning. Delta and single-account aggregations never delete.
4. **Create profile fields are computed top to bottom.** A static/Velocity value can use earlier fields only;
   generator patterns cannot use other create-profile fields at all.
5. **Attributes you create on accounts are not read back** unless they are also in the account schema.
6. **Attribute sync only updates existing correlated accounts**, only for attributes mapped directly from an
   identity attribute in Create Account, is case-sensitive, and the built-in Manager attribute cannot be synced.
7. **Do not touch `features`** on SailPoint-supported connectors (SailPoint warns it can break the source).
8. **Validate JSON before PUT/PATCH**: `python3 scripts/check_source_config.py file.json`.

## Checker

`scripts/check_source_config.py` (stdlib) recognizes provisioning policies, source objects, correlation configs,
NCD configs and schedules, and reports: invalid usage types, field types and keys, duplicate fields, static values
that reference later fields (order bug), generator patterns that read other fields, field transforms (via
`../isc-transforms/scripts/validate_transform.py`), unknown features/statuses, a delete threshold outside 0–100,
plain-text secrets in `connectorAttributes`, correlation operations other than EQ, NCD enabled with nothing selected,
non-Quartz cron expressions. It cannot know your source's schema or connector: test with a real aggregation.

## References

| File | Use for |
|---|---|
| `references/aggregation.md` | full/delta/single, optimized vs unoptimized, delete threshold, schedules, files, entitlements, limits |
| `references/correlation.md` | correlation config, default correlation, manual correlation, rules, manager correlation |
| `references/provisioning-policies.md` | create profile ↔ API, usage types, mapping types, generators, examples, attribute sync |
| `references/troubleshooting.md` | source statuses, "why was/wasn't X", native change detection, useful searches |
| `references/source-api-schemas.md` | GENERATED: `source`, `schema`, policies, correlation, schedules, NCD, health, enums |
| `references/source-endpoint-index.md` | GENERATED: every endpoint of sources, connectors, aggregations, subtypes, usages |
| `references/saas-connectivity/` | SailPoint docs: SaaS connector spec, commands (`commands-index.md`), connector customizers |

Related skills: `../isc-transforms` (field transforms, usernameGenerator), `../isc-rules` (BeforeProvisioning,
Correlation, ManagerCorrelation, AttributeGenerator, connector rules), `../isc-workflows` and
`../isc-event-triggers` (Native Change, account events), `../isc-api` (auth, paging, PATCH).
