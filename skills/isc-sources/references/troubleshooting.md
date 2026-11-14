# Source troubleshooting

## Source status (field `status` on the source, `GET /sources/v1/{sourceId}/source-health`)

| Status | Meaning | First thing to check |
|---|---|---|
| `SOURCE_STATE_HEALTHY` | last check passed | — |
| `SOURCE_STATE_UNCHECKED_SOURCE` | not tested yet | run Test Connection |
| `SOURCE_STATE_UNCHECKED_SOURCE_NO_ACCOUNTS` | no accounts aggregated yet | run the first aggregation |
| `SOURCE_STATE_UNCHECKED_CLUSTER`, `SOURCE_STATE_UNCHECKED_CLUSTER_NO_SOURCES` | cluster not checked / empty | VA cluster health |
| `SOURCE_STATE_ERROR_SOURCE`, `SOURCE_STATE_FAILURE_SOURCE` | connector cannot reach or authenticate to the system | host/port, service account, password expiry, firewall from the VA, certificates |
| `SOURCE_STATE_ERROR_CLUSTER`, `SOURCE_STATE_FAILURE_CLUSTER` | cluster problem | VA online? cluster status in Admin > Connections > Virtual Appliances |
| `SOURCE_STATE_ERROR_VA` | virtual appliance problem | VA services, disk, connectivity to the tenant |
| `SOURCE_STATE_ERROR_ACCOUNT_FILE_IMPORT` | the last file import failed | file encoding, header, delimiter, size (keep under ~500 MB) |

Connection checks through the API: `POST /sources/v1/{sourceId}/connector/check-connection`,
`.../ping-cluster`, `.../test-configuration`, and `.../peek-resource-objects` to see raw objects the connector returns.
Attribute sync's bulk *Sync* button only works when the source is healthy.

## "Why did / didn't X happen?"

| Symptom | Likely cause | Where to look |
|---|---|---|
| Accounts never correlate | correlation pairs, attribute not searchable, optimized aggregation skipped them | `correlation.md` checklist |
| New users get no account on a target | no access profile/role granting it, missing Create Account fields, identity attribute empty, provisioning disabled for the source | access request / role, create profile, the identity's account activities (failed `Create` operations and their error) |
| Account created with wrong values | field order in Create Account, transform output, BeforeProvisioning rule changing the plan | `provisioning-policies.md`, rule code |
| Accounts deleted in the system still in ISC | deletion off, threshold exceeded, delta aggregation only | `aggregation.md` |
| Changes made directly in the system are not noticed | aggregation not scheduled, delta does not cover it, native change detection off | below |
| Attribute keeps flipping back | attribute sync overwriting native changes, or a rule and sync fighting | Attribute Sync page, *View Events* |
| Aggregation slow or timing out | page size/timeouts in connector settings, VA resources, `aggregateTimeout` (max 600 s) | aggregation history |

Search for failures: account activities and audit events (see `../isc-search`), e.g. events of the source by name,
aggregation results in *Admin > Connections > Sources > source > Aggregation History*.

## Native change detection (NCD)

Detects accounts **created, updated or deleted outside ISC**, by comparing what an aggregation reads with what ISC
stored. Summarized from SailPoint's documentation (Native Change Detection, checked 2026-11-14:
https://documentation.sailpoint.com/saas/help/sources/native_change_detection.html).

- Enable per source (Account Management → *Enable Native Change Detection*) or with
  `PUT /sources/v1/{sourceId}/native-change-detection-config`:

```json
{ "enabled": true, "operations": ["ACCOUNT_CREATED", "ACCOUNT_UPDATED", "ACCOUNT_DELETED"],
  "allEntitlements": true, "allNonEntitlementAttributes": false,
  "selectedEntitlements": [], "selectedNonEntitlementAttributes": ["title"] }
```

- At least one operation and at least one attribute must be selected, otherwise nothing fires. Changes are found only
  when an aggregation runs.
- Event triggers: *Native Change Account Created / Updated / Deleted* — one event per changed account, correlated or
  not; payload includes account, source, identity, entitlements added/removed and changed attributes (see
  `../isc-event-triggers`). Audit events: *Create/Update/Delete Native Change Detected*.
- Workflow templates exist to revoke entitlements added natively (they need all entitlements monitored for all
  operations, and skip entitlements without an ID).
- Not available for Non-Employee sources; SAML Just-in-Time sources must be configured through the API.

NCD on, but nothing arrives? Check in this order: (1) the config has `enabled: true`, at least one operation and at
least one attribute or entitlement (`python3 scripts/check_source_config.py ncd.json`); (2) an aggregation ran after
the change, and the change touched a monitored attribute (multiple selected attributes combine with AND);
(3) a subscription to the Native Change trigger exists, is enabled, and its JSONPath filter does not drop the event;
(4) the trigger is available in the tenant (some triggers are early access). Subscriptions and filters:
`../isc-event-triggers`.
