# Correlation

Correlation links an **account** to an **identity**. Uncorrelated accounts get no access and are not governed.
Summarized from SailPoint's product documentation (Account Correlation, checked 2026-11-14:
https://documentation.sailpoint.com/saas/help/accounts/correlation.html) and the OpenAPI spec.

## Account correlation configuration

- Pairs of **identity attribute** ↔ **account attribute**, operation fixed to **Equals**.
- Pairs are tried **one at a time, in order**; the **first** pair that matches correlates the account (it is not an
  AND of all pairs). Put the most reliable identifier first (employee number, immutable ID), names last or never.
- Case-insensitive by default; `ignoreCase` per assignment changes it through the API.
- **Default correlation**: if no configured pair matches, ISC compares the account name with the identity `name`
  (case-insensitive, not configurable). Be aware of it when account names look like usernames of other people.
- Only **searchable** identity attributes can be used; up to 6 additional searchable identity attributes can be added
  via the identity attribute API, and identities must be processed before they work for correlation.
- Account attribute values over 128 characters are not supported for correlation.
- Configure correlation **before the first aggregation**. After a change, run an unoptimized aggregation
  (`disableOptimization=true`), see `aggregation.md`.

API: `GET/PUT /sources/v1/{id}/correlation-config` — object `correlationconfig-2`:

```json
{
  "name": "HR Source Account Correlation",
  "attributeAssignments": [
    { "property": "<identity attribute>", "value": "<account attribute>", "operation": "EQ",
      "complex": false, "ignoreCase": true, "matchMode": "ANYWHERE", "filterString": "" }
  ]
}
```

Read the current object first and change it: the exact form of `property`/`value` is the one ISC returns for your
tenant (the spec documents the fields but not the naming of the values). `operation` only supports `EQ`;
`matchMode` is `ANYWHERE`, `START` or `END`. The source references the config in `accountCorrelationConfig`
(`type: ACCOUNT_CORRELATION_CONFIG`).

## Correlation rule

`accountCorrelationRule` on the source points to a **Correlation** cloud rule for logic the attribute pairs cannot
express (transformations, lookups, conditional matching). Cloud rules go through SailPoint's review process; see
`../isc-rules`. Prefer attribute pairs whenever possible.

## Manual correlation (uncorrelated accounts)

- UI: source → Account Management → *Uncorrelated Accounts* → *Download Correlation File*, fill the identity's
  account ID in `userName`, upload. API: `POST /sources/v1/{id}/load-uncorrelated-accounts` (multipart `file`).
- Manual links are kept (`manuallyCorrelated=true`); unoptimized aggregation does not undo them. Up to 100 accounts can
  be linked to one identity. Accounts created by ISC through provisioning are also `manuallyCorrelated=true`.
- To undo: remove the account, re-upload a corrected file, or reset the source's accounts and entitlements.
- *Admin > Global > Reports* has an *Uncorrelated Accounts* report across sources. Via API:
  `GET /accounts/v1?filters=sourceId eq "<id>" and uncorrelated eq true` (identity search does not see
  uncorrelated accounts, see `../isc-search`).

## Manager correlation

Authoritative sources usually carry the manager. `managerCorrelationMapping` on the source:

```json
"managerCorrelationMapping": { "accountAttributeName": "managerEmployeeId", "identityAttributeName": "employeeNumber" }
```

The value of the account attribute is searched in the identity attribute to find the manager identity. For logic
beyond one attribute, `managerCorrelationRule` points to a ManagerCorrelation cloud rule (`../isc-rules`).

## Checklist when accounts do not correlate

1. Does the identity attribute exist, is it **searchable**, and do identities have values (after processing)?
2. Same value format on both sides (leading zeros, domain prefixes, case if `ignoreCase` is false)?
3. Correlation configured **after** the first aggregation? Run an unoptimized aggregation.
4. Is the value unique? A value shared by several identities cannot correlate reliably: keep correlation attributes unique.
5. Account attribute present in the account schema (and returned by the connector)?
