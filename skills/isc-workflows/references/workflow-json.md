# Workflow JSON

Structure rules from SailPoint's "Building Workflows" page and the Workflows API spec; step shapes taken from real exports in [sailpoint-oss/colab-workflows](https://github.com/sailpoint-oss/colab-workflows) (MIT). Full examples are in `examples/` (IDs and emails replaced by placeholders; they were exported a while ago and call legacy `/beta` URLs — use per-service paths like `/sources/v1/...` today).

## Top level

```json
{
  "name": "Notify on failed aggregation",
  "description": "…",
  "owner": { "type": "IDENTITY", "id": "<identityId>" },
  "enabled": false,
  "trigger": { "type": "EVENT", "attributes": { "id": "idn:account-aggregation-completed", "filter.$": "…" } },
  "definition": { "start": "<name of first step>", "steps": { "<step name>": { … } } }
}
```

Rules:
- Exactly one trigger, at least one action. Step names are unique keys in `steps`; `start` must match one.
- Every step except end steps has `nextStep` (choice steps use `choiceList[].nextStep` + `defaultStep`).
- Every branch ends with a `success` or `failure` step.
- `enabled` must be `false` on create; enable after testing (`PATCH /workflows/v1/{id}` with `/enabled`).
- Keys ending in `.$` take a JSONPath (`"id.$": "$.trigger.identity.id"`); keys without it are literals. Text fields can also embed `{{$.step.field}}`.
- Definition ≤ 400 KB.
- Import: UI "Create Workflow > Start with a JSON File" / "Upload New Script", or `POST /workflows/v1`.

## Step shapes

**Action**
```json
"Get Identity": {
  "actionId": "sp:get-identity",
  "attributes": { "id.$": "$.trigger.identity.id" },
  "nextStep": "Send Email",
  "type": "action",
  "versionNumber": 2
}
```
Action IDs seen in real exports: `sp:get-identity`, `sp:get-identities` (Get List of Identities), `sp:get-accounts`, `sp:manage-account`, `sp:access:get`, `sp:access:manage`, `sp:http`, `sp:send-email`, `sp:forms`, `sp:interactive-form`, `sp:interactive-message`, `sp:sleep` (Wait), `sp:snow` (ServiceNow ticket), `sp:create-campaign`. Confirm others (and the current `versionNumber`) with `GET /workflow-library/v1/actions`.

**Send Email**
```json
"Send Email": {
  "actionId": "sp:send-email",
  "attributes": {
    "recipientEmailList.$": "$.getIdentity.attributes.email",
    "subject": "Aggregation of {{$.trigger.source.name}} failed",
    "body": "Source <b>${sourceName}</b> failed at ${completedTime}.",
    "context": { "sourceName.$": "$.trigger.source.name", "completedTime.$": "$.trigger.completed" },
    "from": null
  },
  "nextStep": "success",
  "type": "action",
  "versionNumber": 2
}
```
`recipientEmailList` can be a literal list or `.$` JSONPath; `context` is the Velocity templating map (`${var}` in body/subject); `replyTo.$` is also accepted. Older examples use `recipientId.$` (identity ID).

**HTTP Request**
```json
"HTTP Request": {
  "actionId": "sp:http",
  "attributes": {
    "method": "post",
    "url": "https://{tenant}.api.identitynow.com/sources/v1/{{$.trigger.source.id}}/load-accounts",
    "authenticationType": "OAuth",
    "oAuthTokenUrl": "https://{tenant}.api.identitynow.com/oauth/token",
    "oAuthClientId": "<client id>",
    "oAuthClientSecret": "<client secret>",
    "oAuthCredentialLocation": "oAuthInHeader",
    "requestContentType": "json",
    "jsonRequestBody": { "disableOptimization": true },
    "urlParams": { "limit": "250" }
  },
  "nextStep": "Check Status",
  "type": "action",
  "versionNumber": 2
}
```
Other body keys: `jsonRequestBody.$`, `jsonPatchRequestBody` (for `json-patch`), `formRequestBody` (`requestContentType: "form"`); headers in `requestHeaders`. Output: `$.hTTPRequest.statusCode`, `$.hTTPRequest.body…`. Verify the exact path for the API being called (it may be experimental and need `X-SailPoint-Experimental: true` in `requestHeaders`). Keep secrets in sensitive headers/Parameter Storage, never in exported JSON you share.

**Choice (compare)**
```json
"Is Error": {
  "type": "choice",
  "choiceList": [
    { "comparator": "StringEquals", "variableA.$": "$.trigger.status", "variableB": "Error", "nextStep": "Send Email" }
  ],
  "defaultStep": "success"
}
```
Comparators seen: `StringEquals`, `StringDoesNotEquals`, `StringEndsWith`, `StringMatches`, `NumericEquals`, `NumericGreaterThan`, `NumericGreaterThanEquals`, `TimestampGreaterThanEquals`, `IsPresent`. The others follow the same naming (`StringContains`, `StringStartsWith`, `NumericLessThan`, `BooleanEquals`, …) — check by building the step in the UI and exporting if unsure.

**Define Variable** (`type: "Mutation"`)
```json
"Define Variable": {
  "type": "Mutation",
  "attributes": {
    "id": "sp:define-variable",
    "variables": [
      { "name": "roleName", "description": "Requested role", "variableA.$": "$.trigger.requestedItemsStatus[0].name",
        "transforms": [ { "id": "sp:transform:substring:string", "input": { "start": 0, "length": 5 } } ] }
    ]
  },
  "nextStep": "Next"
}
```
Read it later as `$.defineVariable.roleName` (technical name of the step + variable name).

**Loop (parallel)**
```json
"Loop": {
  "actionId": "sp:loop:iterator",
  "attributes": {
    "input.$": "$.getAccounts.accounts",
    "context.$": "$",
    "start": "Disable",
    "steps": {
      "Disable": { "actionId": "sp:manage-account", "attributes": { "operation": "disable", "accountIds.$": "$.loop.loopInput.id" }, "nextStep": "Done", "type": "action", "versionNumber": 1 },
      "Done": { "type": "success" }
    }
  },
  "nextStep": "success",
  "type": "action"
}
```
Inside: `$.loop.loopInput` = current item, `$.loop.context` = whatever `context.$` pointed at (here the whole workflow context, so `$.loop.context.getIdentity.name` works). Max 250 items.

**Wait**: `{"actionId": "sp:sleep", "attributes": {"type": "waitFor", "duration": "1h"}, …}`.

**End steps**: `{"type": "success"}` · `{"type": "failure", "failureName": "No operation matched"}`.

## Triggers

```json
{ "type": "EVENT", "attributes": { "id": "idn:identity-attributes-changed", "filter.$": "$.changes[?(@.attribute == \"department\")]" } }
{ "type": "EVENT", "mode": "basic", "attributes": { "id": "idn:identity-attributes-changed",
    "filter.$": "$.changes[?(@.attribute == \"manager\")]",
    "filterDefinition": { "path": "changes", "logic": "and", "conditions": [ { "path": "attribute", "operator": "==", "type": "string", "value": "manager" } ] } } }
{ "type": "EVENT", "attributes": { "id": "sp:form-submitted", "formDefinitionId": "<formId>" } }
{ "type": "SCHEDULED", "attributes": { "frequency": "weekly", "timeZone": "Europe/Rome", "weeklyDays": ["Monday"], "weeklyTimes": ["07:00"] } }
{ "type": "SCHEDULED", "attributes": { "frequency": "cronSchedule", "timeZone": "Europe/Rome", "cronString": "0 6 * * 1-5" } }
{ "type": "EXTERNAL", "attributes": { "description": "Called by ServiceNow" } }
```
`mode: "basic"` requires `filterDefinition` and `filter.$` must equal what it compiles to; in advanced mode omit `filterDefinition`.

## Testing via API

`POST /workflows/v1/{id}/test` with `{"input": { …sample trigger payload… }}` — runs the real actions. Then `GET /workflow-executions/v1/{executionId}` and `/history-v2` for step-by-step input/output. Cancel a running one with `POST /workflow-executions/v1/{id}/cancel`.

## Review checklist

1. Trigger and filter match the scenario; filter tested on a sample payload.
2. Every `.$` key has a valid JSONPath; every `{{ }}` points to a step that runs earlier.
3. Choice steps have `defaultStep`; every branch ends.
4. Error handling on HTTP/provisioning steps; failure branches end in `failure` with a clear name.
5. Loops: input ≤ 250 (parallel) / 1000 (serial); context set if the loop needs outer data.
6. No secrets in the JSON; least-privilege owner/API client.
7. Idempotent if the trigger can fire twice or the schedule overlaps.
