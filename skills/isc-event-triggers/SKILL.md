---
name: isc-event-triggers
description: SailPoint Identity Security Cloud (ISC/IdentityNow) Event Triggers (webhooks) reference. Use when someone asks which event trigger fires in a situation, what its payload contains, how to subscribe (HTTP, EventBridge, workflow), write or validate a JSONPath trigger filter, respond to REQUEST_RESPONSE triggers (access request pre-approval, dynamic approver), or test and debug trigger subscriptions.
---

# SailPoint ISC Event Triggers

Event triggers push a JSON event to subscribers when something happens in ISC. Subscribers: an HTTP endpoint (your service, a no-code tool), AWS EventBridge, or a **workflow** (every workflow event trigger is a subscription under the hood).

## How to answer

1. **Which trigger?** Look it up in the table below or `references/triggers-index.md`; open `references/triggers/<name>.md` for the trigger's context, **sample payload** and notes. Always show the relevant payload fields — the user needs them to write filters and handlers.
2. **Filter?** Build a Jayway JSONPath on that payload (`references/filtering-events.md` has the full operator table). Show how to validate it (`POST /trigger-subscriptions/v1/validate-filter`).
3. **Subscribe?** UI: Admin > Event Triggers > Subscriptions. API: `POST /trigger-subscriptions/v1` (schema in `references/subscription-api-schemas.md`, steps in `references/subscribing-to-a-trigger.md`).
4. **REQUEST_RESPONSE?** Explain the response modes and the exact response body (`references/responding-to-a-request-response-trigger.md`).
5. **Not firing?** Walk the checklist in "Troubleshooting".

For workflows specifically (choosing triggers inside the workflow builder), the `isc-workflows` skill has the broader list (scheduled, external, form, interactive, newer V2 account triggers).

## Trigger catalog (public API spec)

| Trigger | ID | Type | Fires |
|---|---|---|---|
| Access Request Submitted | `idn:access-request-pre-approval` | REQUEST_RESPONSE | after submission, before approvals; subscriber approves/denies. If the subscriber doesn't answer correctly in time, the request fails after the SoD check |
| Access Request Dynamic Approval | `idn:access-request-dynamic-approver` | REQUEST_RESPONSE | after submission (after pre-approval); subscriber returns one identity or governance group added as the **last** approver |
| Access Request Decision | `idn:access-request-post-approval` | FIRE_AND_FORGET | after the final decision |
| Account Aggregation Completed | `idn:account-aggregation-completed` | F&F | aggregation completed, terminated or failed |
| Accounts Collected for Aggregation | `idn:aggregation-accounts-collected` | F&F | new/changed/deleted accounts gathered, being processed |
| Account Attributes Changed | `idn:account-attributes-changed` | F&F | after aggregation, account attributes changed |
| Account Correlated | `idn:account-correlated` | F&F | account added to an identity |
| Identity Created | `idn:identity-created` | F&F | identity created |
| Identity Attributes Changed | `idn:identity-attributes-changed` | F&F | identity attributes changed on refresh |
| Provisioning Completed | `idn:post-provisioning` | F&F | provisioning action completed on a source |
| Campaign Activated / Generated / Ended | `idn:campaign-activated` / `-generated` / `-ended` | F&F | certification campaign lifecycle |
| Certification Signed Off | `idn:certification-signed-off` | F&F | reviewer signed off |
| Scheduled Search | `idn:saved-search-complete` | F&F | scheduled search completed |
| Source Created / Updated / Deleted | `idn:source-created` / `-updated` / `-deleted` | F&F | source config lifecycle |
| VA Cluster Status Change | `idn:va-cluster-status-change` | F&F | VA cluster health changed |

Also documented (pages in `references/triggers/`): Account Created / Updated / Deleted, Identity Deleted, Native Change Account Created / Updated / Deleted, Machine Identity Created / Updated / Deleted, Outlier Detected, Form Submitted (`sp:form-submitted`), CIEM triggers, and SoD violation triggers in the spec. Early-access triggers need a support ticket. For the exact list and IDs in a tenant: `GET /triggers/v1` (filter `id eq "…"`).

## Key rules

- **Fire and forget**: one-way, no retry guarantee, up to **50 subscriptions** per trigger.
- **Request/response**: **one subscription** per trigger. Response modes:
  - `SYNC` — answer within **10 s** with HTTP 200 and the output payload.
  - `ASYNC` — answer within 10 s with `200 {}`; later `POST` the result to the `_metadata.callbackURL` (`/trigger-invocations/v1/{id}/complete`) using `_metadata.secret`, before the subscription's `responseDeadline` (ISO-8601 duration, e.g. `PT1H`).
  - `DYNAMIC` — decide per event: reply with the output within 10 s (sync), or `202 Accepted` and complete later via the callback (async). Note the difference: plain `ASYNC` mode acknowledges with `200 {}`, `DYNAMIC`-async with `202`.
  - Pre-approval output (all three required): `{"approved": false, "comment": "Would cause an SoD violation", "approver": "AcmeCorpExternalIntegration"}`. Dynamic approver output: `{"id": "<identity or group id>", "name": "...", "type": "IDENTITY" | "GOVERNANCE_GROUP"}`; send empty values to add nobody (see the trigger page).
- **Subscription types**: `HTTP` (needs `httpConfig`: URL, auth `NO_AUTH` / `BASIC_AUTH` / `BEARER_TOKEN`, `httpDispatchMode` `SYNC|ASYNC|DYNAMIC`), `EVENTBRIDGE` (needs `eventBridgeConfig`: AWS account and region), `WORKFLOW` (managed by workflows), plus `INLINE`/`SCRIPT` in the schema. `enabled: false` still receives test invocations.
- **Filters**: Jayway JSONPath; the event is delivered only if the expression returns a non-empty result. Escape inner double quotes in API bodies. A filter is the cheapest way to cut traffic and cost.
- **Endpoint requirements**: publicly reachable HTTPS; respond fast (ack and process asynchronously); idempotent (the same event can arrive twice; use the event/request IDs to de-duplicate); validate the auth header you configured.
- Triggers don't consume API rate limit, but anything your handler calls back into the API does.

## Troubleshooting checklist

1. Subscription enabled? Correct trigger ID?
2. Activity log of the subscription (UI) — are invocations sent? Errors?
3. Filter matches the real payload? Test it on the sample payload with validate-filter.
4. Auth correct (basic/bearer), certificate valid, endpoint reachable from the internet, answers 2xx in < 10 s.
5. `POST /trigger-invocations/v1/test` (or UI "Test Subscription") with the sample input; `GET /trigger-invocations/v1/status` for recent invocation results.
6. Use https://webhook.site only with test data.

Details: `references/testing-triggers.md`, `references/preparing-a-subscriber-service.md`.

## Reference map

| File | Contents |
|---|---|
| `references/triggers-index.md` → `references/triggers/*.md` | one page per trigger: context, sample payload, notes |
| `references/trigger-types.md` | fire-and-forget vs request/response |
| `references/filtering-events.md` | JSONPath operators, functions, examples, validation |
| `references/subscribing-to-a-trigger.md` | UI and API subscription |
| `references/subscription-api-schemas.md` | generated schemas: subscription, complete invocation, test |
| `references/responding-to-a-request-response-trigger.md` | SYNC / ASYNC / DYNAMIC with full examples |
| `references/preparing-a-subscriber-service.md`, `references/testing-triggers.md` | building and debugging subscribers |

API endpoints: `isc-api` skill → `endpoints/triggers.md`, `endpoints/trigger-subscriptions.md`, `endpoints/trigger-invocations.md`. Not affiliated with SailPoint; official docs: https://developer.sailpoint.com/docs/extensibility/event-triggers
