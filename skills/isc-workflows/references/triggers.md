# Workflow triggers

Compiled from SailPoint's product docs (https://documentation.sailpoint.com/saas/help/workflows/workflow-triggers.html, full page re-checked 14 November 2026) and the Triggers API spec. Input fields per trigger: `trigger-payload-fields.md`. IDs marked ✔ are confirmed in the public API spec; for the others get the exact ID from your tenant:

```
GET /workflow-library/v1/triggers                      # all triggers available to you
GET /workflow-library/v1/triggers?filters=name eq "Identity Created"
```

Trigger types in the workflow JSON: `EVENT` (everything below unless noted), `SCHEDULED`, `EXTERNAL`.
Payload samples for event triggers: `isc-event-triggers` skill → `references/triggers/<name>.md`.

## Access requests and approvals

| Trigger | ID | Fires when | Notes |
|---|---|---|---|
| Access Request Submitted | `idn:access-request-pre-approval` ✔ | an access item whose **Approval Type is a workflow** is requested | Use with the **Approval Policy** action. Editing/disabling the workflow only affects new requests. Requires Access Request service. |
| Access Request Decision | `idn:access-request-post-approval` ✔ | final approve/deny decision on a request | Supports filter. `clientMetadata` comes from whoever called create-access-request. With several approvers, fires after the last decision. |
| Access Request Dynamic Approval | `idn:access-request-dynamic-approver` ✔ | after submission | REQUEST_RESPONSE event trigger (one subscriber); used through Event Triggers rather than as a workflow start in most designs. |

## Accounts

| Trigger | ID | Fires when | Notes |
|---|---|---|---|
| Account Created | (UI type `ACCOUNT_CREATED_V2`) | account created on a source or in ISC — via aggregation **or** provisioning | Filter supported. Older event-trigger equivalent: Account Correlated `idn:account-correlated` ✔ (account added to an identity). |
| Account Updated | (`ACCOUNT_UPDATED_V2`) | account changed, including entitlement add/remove | Filter supported. Older: Account Attributes Changed `idn:account-attributes-changed` ✔ (after aggregation). |
| Account Deleted | (`ACCOUNT_DELETED_V2`) | account deleted via aggregation or provisioning | Filter supported. |
| Account Inactivity Detected | — | N consecutive inactive days | Configure through the filter: `$[?(@.trigger.daysInactive > 180)]`; restrict to a source with `$[?(@.sourceID)]`-style conditions. |
| Account Aggregation Completed | `idn:account-aggregation-completed` ✔ | aggregation completed, terminated or failed | No filter in UI; check `status`/stats in the payload with a Compare step. |
| Accounts Collected for Aggregation | `idn:aggregation-accounts-collected` ✔ | accounts gathered, before processing | Good for pre-checks (e.g. too many deletes). |
| Native Change Account Created / Updated / Deleted | — | change made **outside** ISC detected at aggregation | Requires Native Change Detection configured on at least one source. |
| Dataset Account Created / Updated / Deleted | — | dataset / resource-aggregated machine accounts | Uncorrelated: no identity attributes. |

## Identities

| Trigger | ID | Fires when | Notes |
|---|---|---|---|
| Identity Created | `idn:identity-created` ✔ | identity created | Basic mode (attribute/operator/value) or advanced JSONPath filter. |
| Identity Attributes Changed | `idn:identity-attributes-changed` ✔ | one or more identity attributes changed during refresh | Payload has `changes[]` with `attribute`, `oldValue`, `newValue`. Filter e.g. `$.changes[?(@.attribute == "manager")]`. |
| Identity Lifecycle State Changed | — | `cloudLifecycleState` changes | |
| Identity Lifecycle State Change Processed | — | after the LCS configured actions are evaluated/applied (even if no access changed) | Use when the workflow must run after LCS provisioning. |
| Identity Deleted | — | identity removed from ISC | Its accounts can still exist on sources (uncorrelated). |

## Certifications

Campaign Activated `idn:campaign-activated` ✔ · Campaign Generated `idn:campaign-generated` ✔ · Campaign Ended `idn:campaign-ended` ✔ · Certification Signed Off `idn:certification-signed-off` ✔. Require the Certifications service.

## Sources, platform, provisioning

| Trigger | ID | Notes |
|---|---|---|
| Source Created / Updated / Deleted | `idn:source-created` / `idn:source-updated` / `idn:source-deleted` ✔ | Updated = configuration change. |
| Provisioning Completed | `idn:post-provisioning` ✔ | after a provisioning action completes on a source; payload holds account requests and results. Requires Provisioning service. |
| VA Cluster Status Change | `idn:va-cluster-status-change` ✔ | VA cluster health changed. |
| Scheduled Search | `idn:saved-search-complete` ✔ | a scheduled (saved) search finished; results/links in payload. |
| Outlier Detected | — | Identity outlier detected (Data Intelligence). |
| Machine Identity Created / Updated / Deleted | — | needs Machine/Agent Identity Security licence; JSONPath filter. |
| SoD Violation Created / Reopened / Mitigated / Closed | — | present in the Triggers API spec (webhooks). |
| CIEM New Scope Detected / Auto-Include Scope Setting Changed / Scope Selection Changed | — | CIEM sources; filter supported. |
| Risk Signal Created / Updated | — | JSONPath filter. |
| CAEP events (credential change, device compliance, risk level, session revoked, token claims) | — | Shared Signals Framework service. |
| Intel Response Actions / Intel Response Actions – NHI | — | disable/deactivate requests from XDR/SIEM/SOAR; Response and Remediation service. |
| DAS Activity Alert | — | Data Access Security alert. |
| ServiceNow Access Request Cancelled / Completed, Approval Request Created / Updated (Service Catalog) | — | ServiceNow Service Catalog service; example filter `$.accessRequestItems[?(@.clientMetadata.origin == 'ServiceNow Service Catalog Integration')]`. |

## Forms and users

| Trigger | ID | Notes |
|---|---|---|
| Form Submitted | `sp:form-submitted` ✔ | Basic: `formDefinitionId` + `attributeToFilter`/`operatorValue`/`attributeValue` (operators like `StringEquals`, `StringContains`, `StringStartsWith`, `NumericGreaterThan`, `BooleanEquals`, `ArrayAnyOf`). Advanced filter: `$[?(@.formDefinitionId == '<formId>' && @.formData.department == "sales")]`. Read answers with `$.trigger.formData.<field>`, submitter with `$.trigger.submittedBy.id`. |
| Interactive Trigger | `idn:interactive-process-launched` (seen in SailPoint's colab exports) | user starts it from a Launcher on Launchpad; "Create Launcher" also creates an entitlement to control who sees it. Search `LAUNCHER_LAUNCHED` events for history. |

## Scheduled trigger (`type: SCHEDULED`)

Attributes: `frequency` = `daily | weekly | monthly | yearly | cronSchedule`, `timeZone` (IANA, e.g. `Europe/Rome`), `cronString` (for cronSchedule), `weeklyDays`, `weeklyTimes`, `yearlyTimes`, … (see `workflow-api-schemas.md`).
- Cron strings: hours only, minutes are not supported. The Daily/Weekly/Monthly/Yearly options use time pickers instead (`weeklyTimes` etc.; a SailPoint export stores `1969-12-31T20:30:00.000Z`, i.e. a time with minutes, and another `"00:00"`) — confirm in the UI whether the minute you need is selectable. The generated schema's `weeklyTimes` example (`"Monday"`) is a typo in SailPoint's spec.
- A new run can start before the previous finished: design for overlap (idempotent steps).
- No input payload: start with a search/get step (Get List of Identities with a search query, HTTP Request to the ISC API, etc.).

## External trigger (`type: EXTERNAL`)

- In the UI: **+ New Access Token** → client ID, client secret (shown once) and the client URL. Generating a new token overwrites the old one. API: `POST /workflows/v1/{id}/external/oauth-clients`.
- Caller: get a token with client credentials using that client, then `POST /workflows/v1/execute/external/{id}` with body `{"input": {...}}` (test endpoint: `/workflows/v1/execute/external/{id}/test`).
- Inside the workflow read the input with `$.trigger.<field>` typed by hand (the variable selector doesn't know your payload).

## Filter tips

- Basic mode compiles to a JSONPath (`filterDefinition` → `filter.$`); max 5 conditions in basic mode (advanced filters can be longer: a SailPoint example uses 7); operators per type: string `== != =~ size contains is empty|is not empty|is null|is not null`, number `== != < <= > >=`, boolean `== !=`.
- Advanced mode: any Jayway JSONPath — see `isc-event-triggers/references/filtering-events.md` for the operator table (`in`, `nin`, `anyof`, `=~ /regex/i`, `&&`, `||`).
- A filter that returns a non-empty result = the workflow runs. Validate with `POST /trigger-subscriptions/v1/validate-filter` using the sample payload, or the JSONPath evaluator at https://developer.sailpoint.com/tools/json-path-evaluator.
