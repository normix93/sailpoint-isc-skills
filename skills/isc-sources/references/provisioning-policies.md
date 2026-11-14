# Create profile, provisioning policies and attribute sync

Summarized from SailPoint's product documentation (Create Account and Attribute Sync pages, checked 2026-11-14:
https://documentation.sailpoint.com/saas/help/provisioning/create_profile.html ,
https://documentation.sailpoint.com/saas/help/provisioning/attr_sync.html), the developer docs and the OpenAPI spec.

## UI ↔ API

The UI's **Create Account** definition (source → Account Management) is the provisioning policy with
`usageType: CREATE`. Other usage types exist only through the API:
`CREATE, UPDATE, ENABLE, DISABLE, DELETE, ASSIGN, UNASSIGN, CREATE_GROUP, UPDATE_GROUP, DELETE_GROUP, REGISTER,
CREATE_IDENTITY, UPDATE_IDENTITY, EDIT_GROUP, UNLOCK, CHANGE_PASSWORD` (enum `usagetype`).

| Operation | Endpoint |
|---|---|
| list | `GET /sources/v1/{sourceId}/provisioning-policies` |
| create | `POST /sources/v1/{sourceId}/provisioning-policies` |
| read / replace / patch / delete one | `/sources/v1/{sourceId}/provisioning-policies/{usageType}` (one policy per usage type) |
| several at once | `POST /sources/v1/{sourceId}/provisioning-policies/bulk-update` |
| by id, several per usage type (source subtypes) | `/sources/v2/{sourceId}/provisioning-policies[/{id}]` — **experimental** (header `X-SailPoint-Experimental: true`) |

With the v1 API a source has **at most one policy per usage type** (so one CREATE policy): it is addressed by the
usage type in the path. The v2 API addresses policies by id and adds `subtypeId` and the usage type
`CREATE_MACHINE_ACCOUNT`, for machine-account subtypes; it is experimental.

Direct-connect sources create the account automatically. Flat-file sources cannot be written to: ISC opens a
manual task for the source owner with the computed values.

## Policy structure

```json
{
  "name": "Account",
  "description": "Create profile for Corporate LDAP",
  "usageType": "CREATE",
  "fields": [
    { "name": "givenName", "type": "string", "isRequired": false, "isMultiValued": false, "attributes": {},
      "transform": { "type": "identityAttribute", "attributes": { "name": "firstname" } } },
    { "name": "uid", "type": "string", "isRequired": true, "isMultiValued": false,
      "transform": { "type": "rule", "attributes": { "name": "Create Unique Account ID" } },
      "attributes": { "template": "$(firstname).$(lastname)$(uniqueCounter)", "cloudMaxUniqueChecks": "50",
                      "cloudMaxSize": "20", "cloudRequired": "true" } },
    { "name": "mail", "type": "string", "isRequired": false, "isMultiValued": false, "attributes": {},
      "transform": { "type": "static", "attributes": { "value": "$uid@example.com" } } },
    { "name": "password", "type": "secret", "isRequired": false, "isMultiValued": false, "attributes": {},
      "transform": { "type": "rule", "attributes": { "name": "Create Password" } } }
  ]
}
```

- `name` = account attribute, **case-sensitive**, must exist on the source and support create.
- `type`: `string, int, long, date, boolean, secret` (`secret` is masked and encrypted).
- `transform`: any transform (see `../isc-transforms`); field-level `attributes` carry generator settings.

## Mapping types (UI) and their JSON

| UI mapping | JSON | Notes |
|---|---|---|
| Identity Attribute | `{"type": "identityAttribute", "attributes": {"name": "<identity attr>"}}` | most fields |
| Generator *Create Unique Account ID* | `{"type": "rule", "attributes": {"name": "Create Unique Account ID"}}` + field attributes `template` (`$(technicalName)`, `$(uniqueCounter)`), `cloudMaxUniqueChecks` (max 50), `cloudMaxSize`, `cloudRequired` | for more control use the `usernameGenerator` transform (patterns tried in order; `uniqueCounter` must be in the last one) |
| Generator for other unique attributes (mail, sAMAccountName when it is not the account ID) | `{"type": "rule", "attributes": {"name": "Create Unique LDAP Attribute"}}` + the same `template`/`cloudMax*` attributes | *Create Unique Account ID* is meant for the account ID; this one checks uniqueness of any attribute |
| Generator *Create Password* | `{"type": "rule", "attributes": {"name": "Create Password"}}`, field `type: "secret"` | generates the initial password |
| Static | `{"type": "static", "attributes": {"value": "..."}}` | text or Velocity; can use **earlier** fields as `$fieldName`; cannot read identity attributes directly (map them to an earlier field, or use a transform) |
| Disable | field omitted | |
| Custom generator | Attribute Generator cloud rule (`../isc-rules`) | |

## Rules of thumb

1. **Order matters**: fields are computed top to bottom; a field used by a later static value must come first.
   Generator patterns cannot use other create-profile fields.
2. The account's **identity attribute** (e.g. `sAMAccountName`, `distinguishedName`, `uid`) must be produced here,
   and must be unique: use a generator.
3. A field created here is **not aggregated back** unless it is in the account schema.
4. Changing many attributes at provisioning time (e.g. moving OUs, clearing groups) is a job for a
   **BeforeProvisioning** rule (`beforeProvisioningRule` on the source), not for more policies.
5. The built-in Manager identity attribute works in Create Account but not in attribute sync.
6. Accounts created by ISC are marked `manuallyCorrelated=true`.

Check a policy before uploading it (from the skill folder): `python3 scripts/check_source_config.py policy.json`.
The usual flow: `GET .../provisioning-policies/CREATE`, edit, check, `PUT` the whole object back.

## Attribute sync

Keeps account attributes equal to identity attributes after the account exists.

- An attribute can be synced only if it is in **Create Account** and mapped **directly** from an identity attribute.
- Runs automatically when an authoritative aggregation changes an identity attribute, when an aggregation detects a
  native change on a synced attribute (sync may overwrite it), or when an account moves to another identity;
  manually per identity (*Synchronize Attributes*) or in bulk per source (*Sync*, at most 3 full syncs per 24 h,
  only when the source is healthy). Failed syncs are retried up to 10 times.
- Updates every correlated account of the identity; never creates accounts; ignores uncorrelated ones.
- Case-sensitive. Nulls are propagated. Multi-valued attributes need custom rules.
- Do not sync attributes that rules or aggregation also change: the values never converge and sync keeps retrying.
- API (experimental): `GET/PUT /sources/v1/{id}/attribute-sync-config`, `POST /sources/v1/{id}/synchronize-attributes`.
