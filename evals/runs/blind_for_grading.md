## api-01
Question: Which endpoint gives me the status of access requests, what can I filter on and how do I paginate?
Must contain: ['GET /access-request-status/v1', 'filters on accessRequestId, accountActivityItemId, created (with their operators)', 'query params requested-for / requested-by / regarding-identity / assigned-to', 'limit max 250 + offset (record-based)', 'stable sorters (created, modified, accountActivityItemId, name)']
Must NOT contain: ['filtering on status with this endpoint', 'limit above 250']
Source of truth: api-specs access-requests/paths/access-request-status-v1.yaml

### Answer A
Use GET /access-request-status/v1 (scope idn:access-request-status:read; any user can see their own requests, ORG_ADMIN needed for others'). The filters parameter accepts only accessRequestId (eq, ne, gt, ge, lt, le, sw), accountActivityItemId (eq, in, ne, gt, ge, le, sw) and created (eq, ne, gt, ge, lt, le), e.g. filters=created ge 2026-01-01T00:00:00Z; sorters: created, modified, accountActivityItemId, name. Who/what is selected with separate query params: requested-for, requested-by, regarding-identity (mutually exclusive with the first two; 'me' = caller), assigned-to, and request-state=EXECUTING. Paginate with limit (default and max 250) and offset (starting at 0), with a stable sorters (e.g. -created), looping until a page returns fewer than limit items; count=true puts the total in X-Total-Count. For an org-wide admin view with a status filter there is the experimental GET /access-request-administration/v1 (header X-SailPoint-Experimental: true).

### Answer B
Use GET /v3/access-request-status (also /beta/access-request-status). Query params: requested-for, requested-by, regarding-identity (all identity IDs, or 'me'), assigned-to, count, plus filters and sorters. Supported filters include accessRequestId (eq, in, ge, gt, le, lt, ne, sw), status (eq, in, ne), created (eq, in, ge, gt, le, lt, ne, sw) and requestedFor.id; sorters: created, modified, accountActivityItemId, name. Paginate with limit (max 250) and offset; add count=true to get the X-Total-Count header and loop offset += limit until you have them all. Note: at least one of requested-for/requested-by/regarding-identity is typically required or it defaults to the caller's own requests unless you are an admin.

## api-02
Question: I want the approvals waiting for me. Endpoint and filters?
Must contain: ['GET /access-request-approvals/v1/pending', 'filters id, requestedFor.id, accessRequestId (eq,in), created/modified (comparisons)', 'sorters created, modified']
Must NOT contain: ['status filter on pending']
Source of truth: api-specs access-request-approvals pending

### Answer A
GET /access-request-approvals/v1/pending returns the access request approvals waiting for the caller (owner-id query param to target another approver as admin; /access-request-approvals/v1/completed gives the ones already decided). Filters: id (eq, in), requestedFor.id (eq, in), accessRequestId (eq, in), created and modified (eq, in, gt, ge, lt, le); sorters: created, modified. Example: GET /access-request-approvals/v1/pending?filters=requestedFor.id eq "2c91..."&sorters=-created&limit=250&offset=0 (URL-encode the filter). Approve/reject with POST /access-request-approvals/v1/{approvalId}/approve or /reject. Approvals from the generic approval framework (workflows, non-access tasks) are under /generic-approvals/v1 instead.

### Answer B
Use GET /v3/access-request-approvals/pending (completed ones are under /v3/access-request-approvals/approved and /rejected via /v3/access-request-approvals/completed). With a user token, owner-id defaults to the caller; admins can pass owner-id=<identityId> to view someone else's. Filters: id (eq), requestedFor.id (eq, in), modified (gt, lt, ge, le, eq, in); sorters: created, modified. Paginate with limit (max 250)/offset and count=true. Alternatively, generic work items for you are at GET /v3/work-items (and /v3/work-items/count), and the newer generic approvals API is GET /beta/generic-approvals (or /v2025 approvals) with filters like status eq "PENDING".

## api-03
Question: How do I list uncorrelated accounts of one source via API?
Must contain: ['GET /accounts/v1', 'filters sourceId eq "..." and uncorrelated eq true', 'paginate limit 250']
Must NOT contain: ['search index for uncorrelated accounts']
Source of truth: api-specs accounts filters

### Answer A
Call GET /v3/accounts with filters=sourceId eq "<sourceId>" and uncorrelated eq true, e.g. GET /v3/accounts?filters=sourceId eq "2c91..." and uncorrelated eq true&limit=250&offset=0&count=true. URL-encode the filter. uncorrelated supports eq; sourceId supports eq and in. Alternatively use Search (POST /v3/search, indices ["accounts"] isn't available - use identities with @accounts) or the source's uncorrelated accounts report, but /v3/accounts with that filter is the standard approach. Page with limit (max 250) and offset.

### Answer B
Use GET /accounts/v1 with filters=sourceId eq "<sourceId>" and uncorrelated eq true (sourceId supports eq, in, sw; uncorrelated supports eq). Paginate with limit (max 250) and offset plus a stable sorter such as sorters=id; count=true returns the total in X-Total-Count. Don't use Search for this: the identities index only contains correlated accounts, so @accounts(source.name:"X") won't find uncorrelated ones. Other useful filters on the same endpoint: identity.correlated, manuallyCorrelated, nativeIdentity, name.

## api-04
Question: My script calls /v3/access-request-status. What is the new path after the June 2026 versioning change?
Must contain: ['/access-request-status/v1', 'per-service versioning', "legacy paths still work until end of support (Q2 2028 supported / off 2029 or 'announced end of support')"]
Must NOT contain: ['/v2026 as the recommended target', '/latest in production']
Source of truth: api-versioning-migration.md

### Answer A
Since the June 2026 per-service versioning, /v3/access-request-status maps to GET /access-request-status/v1 (the same applies to beta, v2024, v2025 and v2026 paths of that route). The legacy /v3 path keeps working until its announced end of support, but you should migrate; avoid /latest in production. Filters/sorters are the same set (accessRequestId, accountActivityItemId, created; sorters created, modified, accountActivityItemId, name). Note that a few routes map to v2 rather than v1 (e.g. /v3/access-request-config -> /access-request-config/v2), so always check the versioning map.

### Answer B
I am not fully sure of the exact final path. My understanding is that SailPoint moved from the global /v3, /beta, /v2024, /v2025 prefixes to per-service versioning, where the version sits after the service segment, so /v3/access-request-status would become something like /access-requests/v1/access-request-status (or /access-request-status/v1). The old /v3 paths stay available through a deprecation window, so verify the exact new path in the current API reference before switching.

## api-05
Question: What Content-Type and body format does a PATCH to a source need?
Must contain: ['application/json-patch+json', 'JSON Patch array of operations (op, path, value)']
Must NOT contain: ['application/json merge patch']
Source of truth: patch-requests.md

### Answer A
PATCH /v3/sources/{id} uses JSON Patch (RFC 6902) with Content-Type: application/json-patch+json. The body is a JSON array of operations, e.g. [{"op": "replace", "path": "/description", "value": "New description"}, {"op": "add", "path": "/connectorAttributes/foo", "value": "bar"}]. Supported ops are add, remove, replace, move, copy, test. Sending application/json returns 415/400. Some fields (id, type, connector, created, modified) are read-only and cannot be patched.

### Answer B
PATCH /sources/v1/{id} requires Content-Type: application/json-patch+json and a JSON Patch (RFC 6902) array body, e.g. [{"op":"replace","path":"/description","value":"New description"}]. Supported ops: add, remove, replace, move, copy, test; /array/- appends to an array, and replace on an array replaces the whole array. Immutable fields (id, type, authoritative, created, modified, connector, connectorClass, passwordPolicies) return 400 if you try to change them. Typical use: attaching rules, e.g. {"op":"add","path":"/connectorAttributes/jdbcProvisionRule","value":"My Rule"}.

## api-06
Question: What is the ISC API rate limit and how should my client react?
Must contain: ['100 requests per 10 seconds', 'keyed per client_id (and API version)', '429 with Retry-After', 'retry with backoff']
Must NOT contain: ['per access token only']
Source of truth: rate-limit.md

### Answer A
The default gateway limit is 100 requests per 10 seconds per client_id (and applied separately per API version); some endpoints have stricter limits in their spec. When exceeded you get HTTP 429 Too Many Requests with a Retry-After header giving the seconds to wait. Your client should wait Retry-After (or back off exponentially), then retry; retry 5xx with backoff too, refresh the token once on 401, and never blindly retry other 4xx. Plan concurrency per client_id, not per token, and log the trackingId from error bodies.

### Answer B
The documented limit is 100 requests per access token per 10-second window (roughly 10 req/s per token); some endpoints have stricter limits. When exceeded you get HTTP 429 Too Many Requests with a Retry-After header (seconds). The client should honor Retry-After, otherwise back off exponentially with jitter, throttle concurrency, and retry idempotent calls; don't parallelize aggressively or spin up many tokens to bypass the limit.

## api-07
Question: Filter syntax: is 'name EQ "Finance"' valid in filters?
Must contain: ['operators must be lowercase (eq)', 'strings in double quotes']
Must NOT contain: ['EQ is fine']
Source of truth: standard-collection-parameters.md

### Answer A
Generally yes for field and value: ISC filters use the syntax field operator value with string values in double quotes, e.g. name eq "Finance". Operators are case-insensitive in practice (eq, EQ both accepted), but the documentation shows them lowercase, so prefer 'name eq "Finance"'. Also check that the endpoint actually supports eq on name (each endpoint lists its supported fields/operators), combine with and/or/not, and URL-encode the filter. Single quotes around values are not valid.

### Answer B
No. Filter operators must be lowercase: name eq "Finance" is valid, 'name EQ "Finance"' is rejected (400). Strings go in double quotes, dates are unquoted ISO-8601, lists use in ("a","b"), and you combine with and/or/not. Also, the field and operator must be ones listed for that specific endpoint, and the whole expression must be URL-encoded once (e.g. filters=name%20eq%20%22Finance%22).

## api-08
Question: How do I page through more than 10,000 search results?
Must contain: ['searchAfter', 'sort on a unique field like id', "pass the last record's sort values"]
Must NOT contain: ['offset beyond 10000']
Source of truth: standard-collection-parameters.md search paging

### Answer A
With POST /search/v1, limit can be up to 10,000 per call and offset paging stops at 10,000 results; beyond that use searchAfter. Send a sort on a unique field ("sort": ["id"]), and on each next call pass "searchAfter": [<sort value(s) of the last record of the previous page>], e.g. "searchAfter": ["2c9180835d38ca0c015d606b50851b1e"]. Keep the same query and sort for every page and stop when a page returns fewer than limit results. count=true gives the total in X-Total-Count.

### Answer B
POST /v3/search caps offset-based paging at 10,000 results (offset + limit <= 10000). To go beyond, use searchAfter: sort on a unique field (e.g. "sort": ["id"]) and pass the last record's sort value(s) in "searchAfter": ["<lastId>"] on the next request, keeping limit up to 250 (10000 for some). Loop until fewer than limit results come back. Alternatively narrow the query into slices (e.g. by created date ranges) or use the list endpoints (/v3/accounts, /v3/public-identities) which page with offset without the 10k cap.

## wf-01
Question: Which workflow trigger should I use to do something when an employee changes department?
Must contain: ['Identity Attributes Changed (idn:identity-attributes-changed)', 'filter $.changes[?(@.attribute == "department")]']
Must NOT contain: ['Identity Created as main answer']
Source of truth: workflow-triggers + triggers spec

### Answer A
Use the Identity Attributes Changed trigger (idn:identity-attributes-changed). It fires when an identity's attributes change after aggregation/identity refresh, and the payload contains identity plus a changes array with attribute, oldValue and newValue. Add a trigger filter such as $.changes[?(@.attribute == "department")] so the workflow only runs on department changes. The attribute must be an identity attribute mapped in the identity profile.

### Answer B
Use the Identity Attributes Changed trigger (idn:identity-attributes-changed), which fires when identity attributes change during refresh; the payload has identity plus changes[] with attribute, oldValue, newValue. Filter it to department changes with $.changes[?(@.attribute == "department")] (optionally && @.newValue == "Finance" for a specific target). Then read $.trigger.identity.id and the old/new values in later steps (e.g. Get Identity, Manage Access). The filter is Jayway JSONPath; test it with the trigger's sample payload.

## wf-02
Question: I need to run a workflow every weekday at 6:30. Possible?
Must contain: ['Scheduled trigger', "a cron string supports hours only (minutes ignored), so a cron like 30 6 * * 1-5 won't fire at 6:30", 'the Weekly/Daily options take times; check in the UI whether 06:30 is accepted (a SailPoint example stores a :30 weekly time)', 'runs can overlap']
Must NOT contain: ['cron 30 6 * * 1-5 works as is']
Source of truth: workflow-triggers Scheduled

### Answer A
Partly. The Scheduled trigger supports daily, weekly, monthly, yearly and cronSchedule frequencies with a timeZone, but cron schedules accept hours only, not minutes, so a cron like '30 6 * * 1-5' isn't possible; '0 6 * * 1-5' (weekdays 6:00) is. Options: a weekly schedule with weeklyDays Monday-Friday and weeklyTimes (whether a 06:30 time is accepted should be checked in the UI), or cron at 06:00 weekdays followed by a Wait step of 30m. Remember runs can overlap and a scheduled trigger has no input payload, so start with a search/get step.

### Answer B
Yes, use the Scheduled trigger (Scheduled Trigger / sp:scheduled) with a Custom/Cron schedule. A cron like 30 6 * * 1-5 runs Mon-Fri at 06:30; you can also choose weekly with selected days and a time. Set the timezone in the trigger config (otherwise UTC). Note scheduled workflows have no input payload, so the first steps typically fetch data via HTTP Request or Get actions.

## wf-03
Question: In a loop, how do I read the current item and data from a step before the loop?
Must contain: ['$.loop.loopInput', '$.loop.context with Context set on the loop', 'only Loop Input and Context visible inside']
Must NOT contain: ['direct $.getIdentity inside loop without context']
Source of truth: workflow-operators Loop

### Answer A
Inside a loop only two things are reachable: $.loop.loopInput (the current item of the array given as Loop Input) and $.loop.context (whatever you passed in the loop's Context field). So set Context to the earlier step's data (e.g. $.getIdentity) and read it as $.loop.context.<field>, e.g. $.loop.context.attributes.email; referencing $.getIdentity directly inside the loop won't work. After the loop, results are in loopOutput.successfulItems / failureItems.

### Answer B
Inside a Loop, the current element is referenced as $.loop.loopInput (e.g. $.loop.loopInput.id), and $.loop.index gives the iteration index (if available). Data from steps before the loop is not automatically visible inside the loop: you must pass it via the loop's 'context' field (e.g. context = $.getIdentity.attributes), then read it inside as $.loop.context. Results of steps inside the loop are referenced normally by step name within the loop body. Output of the loop step afterwards is available as $.loop<N>.loopOutput (array).

## wf-04
Question: Max number of items a parallel workflow loop can process?
Must contain: ['250 (parallel)', 'serial loop 1000', 'exceeding fails the workflow']
Must NOT contain: ['unlimited']
Source of truth: workflow-operators

### Answer A
The Loop operator processes up to 250 items per input list; larger arrays fail or are truncated, so batch them (e.g. split data or use multiple runs). I'm fairly but not entirely sure about 250 as the cap; loops run iterations in parallel by default unless you configure sequential execution, which has a lower practical throughput.

### Answer B
The parallel Loop accepts at most 250 items in its Loop Input; more and the workflow fails. The Serial Loop (for loop) handles up to 1000 items and stops at the first failed iteration, and test runs stop after 50 iterations. Loop iterations also count towards the per-workflow execution limits (alert at 100k, blocked at 150k per day). For larger sets, split the input (e.g. batches) or use several runs.

## wf-05
Question: After Manage Access, can my workflow wait until the access is approved and provisioned?
Must contain: ['Manage Access does not wait for approval', 'use a second workflow on Access Request Decision', 'Wait step if waiting for source provisioning', 'failedAccessRequests does not fail the execution']
Must NOT contain: ['Manage Access blocks until approved']
Source of truth: workflow-actions Manage Access

### Answer A
Not directly: the Manage Access action submits an access request and returns immediately with the request info; it does not block until approval/provisioning. To react to completion, use a separate workflow triggered by Access Request Decision / Provisioning Completed (or Access Request Post Approval), or inside the same workflow add a Wait step and poll GET /v3/access-request-status via HTTP Request in a loop. Workflows also have a max runtime, so long waits are limited.

### Answer B
No. Manage Access (30 min timeout) only submits the requests and returns successfulAccessRequests / failedAccessRequests; it does not wait for approvals or provisioning, and a failed request doesn't fail the workflow. To act after the decision, build a second workflow on the Access Request Decision trigger (filter on the accessRequestId or items), and/or use Provisioning Completed for the source-side result; a Wait step can be added if you only need to give the source time. Failed requests should be checked explicitly after the action.

## wf-06
Question: How do I put the user's display name inside the Send Email body?
Must contain: ['Templating Context map like {"name.$": "$.getIdentity..."}', '${name} in body', 'or inline {{$.step.field}}']
Must NOT contain: []
Source of truth: workflow-actions Send Email

### Answer A
Use inline variables with double curly braces in the body, e.g. Hello {{$.getIdentity.attributes.displayName}}, where getIdentity is a prior Get Identity step (use the step's actual technical name). If the trigger payload has it you can use {{$.trigger.identity.name}}, though trigger identity objects usually only carry id/name/type, so a Get Identity step is the reliable way. The email body supports HTML and Velocity-like templating via the variables, but only JSONPath references inside {{ }}.

### Answer B
In Send Email (sp:send-email), add the value to the Templating Context map, e.g. {"displayName.$": "$.getIdentity.attributes.displayName"} (after a Get Identity step), then write ${displayName} in the body or subject (Velocity). Loops work too, e.g. #foreach($i in $items)$i.name#end with "items.$": "$.getAccess.accessItems". In other text fields you can use inline variables like {{$.getIdentity.attributes.displayName}}. Note that < and > in the body only work surrounded by spaces.

## wf-07
Question: Our admin who built all workflows is leaving. Any risk?
Must contain: ['creator is owner and a personal access token is created', 'workflows become orphaned and fail with unauthorized', 'reassign owner or recreate before they leave']
Must NOT contain: ['no impact']
Source of truth: workflow-build

### Answer A
Yes. Workflows run as their owner: the owner field and the identity that created the client credentials/PAT used in HTTP Request actions. If the admin's identity is disabled/removed or loses admin rights, workflows they own can fail or be disabled, and any PAT/OAuth client they created (used for HTTP Request or external triggers) stops working. Before they leave, change the owner of each workflow (PATCH /v3/workflows/{id} on /owner) to a service or team identity, recreate PAT/clients under a non-personal account, export the workflow JSON as backup, and review email recipients referencing them.

### Answer B
Yes. The creating admin becomes the workflow owner and a personal access token is generated for the workflow under that identity; if the admin leaves (identity disabled/removed) the workflows are orphaned and fail with unauthorized errors. Before they leave, reassign ownership of each workflow to another admin (which generates a new token) or recreate them under a non-expiring/service admin identity. You can inventory them via GET /workflows/v1 and check the owner field, and then test each after reassignment.

## wf-08
Question: Which trigger lets ServiceNow start a workflow, and how does it authenticate?
Must contain: ['External Trigger', 'OAuth client (client id/secret) from + New Access Token', 'POST /workflows/v1/execute/external/{id} with input', 'read input with $.trigger.<field>']
Must NOT contain: []
Source of truth: workflow-triggers External + spec

### Answer A
Use the External Trigger (trigger type EXTERNAL). In the UI click + New Access Token (API: POST /workflows/v1/{id}/external/oauth-clients) to get a client ID, client secret (shown once) and URL; generating a new token overwrites the old one. ServiceNow gets an OAuth token with client credentials (POST /oauth/token) using that client, then calls POST /workflows/v1/execute/external/{workflowId} with body {"input": {...}} (test endpoint /workflows/v1/execute/external/{id}/test). Inside the workflow read the input with $.trigger.<field> typed by hand. (The separate ServiceNow Service Catalog triggers only apply to the ServiceNow Service Catalog integration events.)

### Answer B
Use the External Trigger (EXTERNAL type). After saving and enabling the workflow, generate the OAuth client via POST /v3/workflows/{id}/external/oauth-clients, which returns clientId, clientSecret and the trigger URL. ServiceNow obtains a bearer token with the client credentials grant at https://{tenant}.api.identitynow.com/oauth/token and then POSTs JSON to /v3/workflows/execute/external/{id} with Authorization: Bearer <token>. The JSON body becomes $.trigger input; you can also test with /v3/workflows/execute/external/{id}/test.

## wf-09
Question: In Access Request Submitted workflows, how do I get the requested item: requestedItemsStatus?
Must contain: ['Access Request Submitted payload has requestedItem (singular)', 'requestedItemsStatus belongs to Access Request Decision']
Must NOT contain: ['requestedItemsStatus in Submitted']
Source of truth: workflow trigger input samples

### Answer A
No: requestedItemsStatus[] belongs to the Access Request Decision trigger. The Access Request Submitted trigger runs once per requested item and exposes it as the singular requestedItem object: $.trigger.requestedItem.id, .name, .type, .operation, .comment, .addDate/.removeDate, .requestedAccounts, plus $.trigger.requestedFor, $.trigger.requestedBy, $.trigger.accessRequestId and $.trigger.sod. Use these with the Approval Policy action.

### Answer B
Yes: the Access Request Submitted trigger payload includes requestedItemsStatus, an array where each element has id, name, type (ACCESS_PROFILE, ROLE, ENTITLEMENT), operation (Add/Remove), comment, clientMetadata, approvalInfo. Reference e.g. $.trigger.requestedItemsStatus[0].name or loop over $.trigger.requestedItemsStatus. Other fields: accessRequestId, requestedFor (array of identity id/name/type), requestedBy. Note requestedFor is an array in this trigger.

## wf-10
Question: What variables do I get on the error branch of an action?
Must contain: ['Enable Error Handling creates success/error branches', 'workflowErrorMessage', 'workflowStatusCode']
Must NOT contain: []
Source of truth: workflow-build error handling

### Answer A
When you enable the error path (failure branch) on an action, the next step can reference $.<stepName>.error / errorMessage (I believe the fields are something like $.stepName.errorMessage and $.stepName.status/statusCode for HTTP). I'm not fully sure of exact names; the error output typically includes the error message and, for HTTP Request, the response status code and body. Use these in a Send Email or Compare step to handle the failure.

### Answer B
Enable error handling on the action (... > Enable Error Handling) to get success and error branches. On the error branch the step exposes error.workflowErrorMessage and error.workflowStatusCode (pick them with the Variable Selector to get the exact path, e.g. $.<stepTechnicalName>.error.workflowErrorMessage). Without error handling, an action error fails the whole execution. End the error branch with a Failure step if you still want the run marked failed.

## et-01
Question: I want an external service to approve or deny access requests before the normal approvals. Which trigger and what must it return?
Must contain: ['Access Request Submitted idn:access-request-pre-approval REQUEST_RESPONSE', 'response approved, comment, approver', 'one subscription only', 'no correct answer in time => request fails']
Must NOT contain: ['fire and forget']
Source of truth: triggers spec

### Answer A
Subscribe to Access Request Submitted (idn:access-request-pre-approval), a REQUEST_RESPONSE trigger that fires after submission and before the normal approvals; only one subscription is allowed per request/response trigger. Your service must respond with all three fields: {"approved": false, "comment": "Would cause an SoD violation", "approver": "AcmeCorpExternalIntegration"}. approver can be any string, but if you also subscribe to Access Request Decision it must be the username of an existing identity or Decision events won't fire. If your service doesn't respond in time or returns a wrong payload, the request fails after the SoD check. Respond SYNC within 10 s, or ASYNC via the callback URL.

### Answer B
Use the Access Request Pre Approval trigger (idn:access-request-pre-approval), a REQUEST_RESPONSE trigger. Your subscription receives the request (accessRequestId, requestedFor, requestedItems, requestedBy) and must respond with JSON {"approved": true|false, "comment": "...", "approver": "<name>"}. If approved is false the request is denied; if true it continues to normal approvals. Only one subscription is allowed for request/response triggers; respond within the configured timeout or the request proceeds per default behavior.

## et-02
Question: How long does my endpoint have to answer a SYNC request/response trigger and what if I need longer?
Must contain: ['10 seconds', 'ASYNC: reply 200 {} then POST to callbackURL with secret before responseDeadline', 'DYNAMIC option']
Must NOT contain: []
Source of truth: responding-to-a-request-response-trigger

### Answer A
In SYNC mode your endpoint must reply within 10 seconds with HTTP 200 and the output payload; otherwise the invocation terminates without a decision. If you need longer, set the HTTP subscription to ASYNC: acknowledge within 10 s (200 with {}), then later POST the result to _metadata.callbackURL (/trigger-invocations/v1/{id}/complete) with _metadata.secret before the subscription's responseDeadline (ISO-8601 duration, e.g. PT1H). DYNAMIC lets you choose per event (sync answer, or an ack per the docs a 202/200 {} and complete later).

### Answer B
For SYNC response mode the subscriber must respond within 10 seconds (fixed). If you need longer, use ASYNC response mode: return 200 immediately and later post the result to the callback URL (callbackURL with secret in the payload headers/_metadata), with a deadline you configure (up to 1 hour? the async deadline can be set, by default 1 hour); DYNAMIC mode lets the subscriber choose per call (respond 200 with body for sync, or 202 for async).

## et-03
Question: How many subscribers can a fire-and-forget trigger have?
Must contain: ['50']
Must NOT contain: []
Source of truth: trigger-types

### Answer A
A fire-and-forget trigger can have up to 50 subscriptions per trigger (request/response triggers allow only 1). I'm fairly confident 50 is the documented limit.

### Answer B
A fire-and-forget trigger can have up to 50 subscriptions (subscribers) per trigger. Request/response triggers allow only one. Fire-and-forget delivery is one-way with no retry guarantee, so make subscribers idempotent.

## et-04
Question: Write a trigger filter that fires only when lifecycle state becomes terminated.
Must contain: ['$.changes[?(@.attribute == "cloudLifecycleState" && @.newValue == "terminated")]', 'on Identity Attributes Changed']
Must NOT contain: ['AND instead of &&']
Source of truth: filtering-events

### Answer A
On Identity Attributes Changed (idn:identity-attributes-changed): $.changes[?(@.attribute == "cloudLifecycleState" && @.newValue == "terminated")]. It matches when the changes[] item for cloudLifecycleState has newValue terminated (the event is delivered only if the expression returns a non-empty result). In an API body escape the inner double quotes. Note the trigger doesn't detect null -> active for new identities, and lifecycle values are case-sensitive technical names.

### Answer B
For the Identity Attributes Changed trigger: $.changes[?(@.attribute == "cloudLifecycleState" && @.newValue == "terminated")] . The filter is JSONPath evaluated against the payload; it fires if the expression returns a non-empty result. Use the actual lifecycle state technical name (case-sensitive). Optionally add && @.oldValue != "terminated" to avoid re-firing.

## et-05
Question: How can I validate a trigger filter via API?
Must contain: ['POST /trigger-subscriptions/v1/validate-filter (or beta path)', 'body with input sample and filter', 'escape quotes']
Must NOT contain: []
Source of truth: filtering-events

### Answer A
Use POST /beta/trigger-subscriptions/validate-filter with body {"input": {...sample payload...}, "filter": "$.changes[?(@.attribute == 'cloudLifecycleState')]"}. It returns {"isValid": true/false, "isValidJSONPath": true/false, "isPathExist": true/false}. You can get a sample input from GET /beta/triggers (exampleInput) or test the subscription via POST /beta/trigger-invocations/test.

### Answer B
Use POST /trigger-subscriptions/v1/validate-filter (scope sp:trigger-service-subscriptions:manage, ORG_ADMIN) with a body containing the filter and a sample input, e.g. {"input": {...sample Identity Attributes Changed payload...}, "filter": "$.changes[?(@.attribute == \"cloudLifecycleState\")]"}; escape inner double quotes. Use the trigger's example input from its schema. In the UI, pasting the filter in the subscription and clicking Update also validates it. To test end-to-end, POST /trigger-invocations/v1/test sends a test event to subscriptions.

## nt-01
Question: Which email is sent when an access request is denied, to whom, and which variables can I use?
Must contain: ['Access Request Decision template to the requester', 'variables approved, approverName, rejecterName, reviewerComment, requestedObjectName, requesterName …', 'GET /notification-template-variables/v1/{key}/EMAIL for the tenant list']
Must NOT contain: []
Source of truth: et_ar_decision + spec

### Answer A
The 'Access Request Denied' / 'Access Request Decision - Denied' template (key ACCESS_REQUEST_DENIED or REQUESTED_ACCESS_DENIED) goes to the requester/recipient (requestedFor and requester if different). Variables include $requesterName, $requestedForName or $recipientName, $requestedObjects/$requestedObjectName, $approverName/$reviewerName, $comments/$deniedComment, plus global ones like $__global.productName and $__util helpers. I'm not fully sure of exact variable names; check the template defaults in Admin > Global > Notification Templates or via GET /beta/notification-template-defaults.

### Answer B
The Access Request Decision template (et_ar_decision.html) goes to the requester when the request is approved or denied; Access Request Decision for Other goes to the requested-for user when someone else made the request (revoke requests have their own Revoke Request Decision templates). Variables include approved (Boolean), reviewerComment (denial comment), rejecterName, approverName, requestedObjectName/requestedObjectType, accessProfileName, requesterName, requestedForIdentityName, accessibleItems, removeDate, sourceInformation, plus v1 globals ($user, ${PRODUCT_NAME}, $spTools.formatDate). Default subject: Your access request for ${accessProfileName} has been #if($approved)approved#{else}denied#end. The authoritative list for your tenant is GET /notification-template-variables/v1/{key}/EMAIL.

## nt-02
Question: How do I stop ISC from sending one specific email?
Must contain: ['first word of subject no_send or Stop', 'overrides process settings, careful with password reset/certifications']
Must NOT contain: ['delete the template']
Source of truth: using_email_templates

### Answer A
In the UI go to Admin > Global > Email Templates (Notification Templates), open the template and toggle it to disabled. Via API, update the template (PUT/POST /beta/notification-templates with the same key/medium/locale) setting the appropriate field, or delete the custom template so it reverts to default. Disabling a template only stops that email; others remain.

### Answer B
Edit that template (Admin > Global > Email Templates > template > Edit) and make no_send or Stop the first word of the subject (case-insensitive); ISC then won't send it. This overrides process settings, so be careful with password reset, certification and non-employee templates. Some notifications can also be turned off in their process configuration, and per-key mediums can be set via /notification-preferences/v1/{key}.

## nt-03
Question: Can I use $user in the Non-Employee Request Created template?
Must contain: ['no: v2 template, $user only in v1', 'use $__recipient / $__util']
Must NOT contain: ['yes']
Source of truth: available_templates globals

### Answer A
No. Non-Employee Request Created (et_ne_acctrequest.html) is a v2 template, and $user only works in v1 templates. Use the v2 globals instead: $__recipient (name, id, email, phone), $__global.productName, $__contentJson, $__util (getUser(), getIdentityDetailsByID()...), $__dateTool. Check the template variables with GET /notification-template-variables/v1/{key}/EMAIL.

### Answer B
Probably not: each template has its own specific set of variables, and $user is not documented for the Non-Employee Request Created template. That template exposes non-employee fields like $requesterName, $nonEmployeeName/$firstName/$lastName, $sourceName, plus globals. Using an undocumented variable renders blank or the literal text. I'm not completely sure of the exact variable list.

## nt-04
Question: My test email shows empty variables. Bug?
Must contain: ['test emails render only global variables', 'conditional sections excluded', 'test with a real event / redirect to test address']
Must NOT contain: []
Source of truth: using_email_templates testing

### Answer A
Not a bug: test emails from the template editor render only global variables; template-specific variables are null and conditional sections are skipped. To check real values, trigger the actual process in a sandbox with Email Templates > Settings > Test Address redirecting everything to you, optionally with <pre>$__contentJson</pre> in v2 templates for debugging. Also unknown variables render literally (${foo}) unless written as $!{foo}.

### Answer B
Usually not a bug: the 'send test email' feature doesn't populate the template context with real data, so most variables render empty or as literal $var. To validate, trigger the real event in a sandbox. Also check variable names are spelled exactly as documented for that template, and that you use the right syntax ($var or ${var}) and null-safe checks like #if($var).

## nt-05
Question: Can I put a <style> block and an HTML comment in a template?
Must contain: ['no: sanitizer, no head/comments', 'use inline style attributes']
Must NOT contain: ['yes']
Source of truth: using_email_templates permitted HTML

### Answer A
Inline styles work best; a <style> block may be stripped by ISC's HTML sanitization or by mail clients, so prefer inline style attributes. HTML comments are generally removed/allowed but serve no purpose; Velocity comments (## or #* *#) are better. I'm not fully certain whether ISC strips <style>; keep templates simple and test.

### Answer B
No. The HTML sanitizer strips <style> blocks, <head> and HTML comments (<!-- -->); use inline style= attributes instead, which are allowed on all elements. For comments use Velocity comments (## line or #* block *#), which aren't rendered. Templates have a 130 KB max size.

## nt-06
Question: Can I set a different From address on one template?
Must contain: ['From is global or per brand, not per template', 'must be verified', 'Reply-To can be per template']
Must NOT contain: ['per-template From']
Source of truth: using_email_templates

### Answer A
No. The From address is set globally or per brand and must be a verified address/domain (/verified-from-addresses/v1, /verified-domains/v1); it can't be changed per template. Reply-To, however, is per template and accepts #if/#else. If you need a different From for a custom email, a workflow Send Email step lets you set a verified From address.

### Answer B
Not per-template in the standard UI: the From address is tenant-wide (default no-reply@sailpoint.com or a verified sender configured under Admin > Global > Email Settings/Sender email, with domain verification via DKIM/SPF via /beta/verified-from-addresses). The template's 'from' field can be set via the API on the custom template to a verified address, but it must be a verified sender. I'm unsure whether per-template from is fully supported.

## tr-01
Question: Write a transform that sets lifecycle 'inactive' if endDate is in the past, else 'active'.
Must contain: ['dateCompare with firstDate/secondDate now/operator lt|gt and positive/negativeCondition', 'requiresPeriodicRefresh true']
Must NOT contain: ['conditional with < or >']
Source of truth: date-compare.md

### Answer A
Use a dateCompare transform: {"name": "LCS by endDate", "type": "dateCompare", "attributes": {"firstDate": {"type": "dateFormat", "attributes": {"input": {"type": "accountAttribute", "attributes": {"sourceName": "HR", "attributeName": "endDate"}}, "inputFormat": "yyyy-MM-dd", "outputFormat": "ISO8601"}}, "secondDate": "now", "operator": "LT", "positiveCondition": "inactive", "negativeCondition": "active"}}. Operators are LT, LTE, GT, GTE; firstDate/secondDate must be ISO8601 or 'now'. Handle null endDate with a firstValid fallback (e.g. default future date).

### Answer B
Use a dateCompare transform with requiresPeriodicRefresh: true so it is re-evaluated nightly: {"name":"LCS - inactive after endDate","type":"dateCompare","requiresPeriodicRefresh":true,"attributes":{"firstDate":{"type":"firstValid","attributes":{"values":[{"type":"dateFormat","attributes":{"inputFormat":"yyyy-MM-dd","outputFormat":"ISO8601","input":{"type":"accountAttribute","attributes":{"sourceName":"HR Source","attributeName":"endDate"}}}},"9999-12-31T00:00:00Z"]}},"secondDate":"now","operator":"lt","positiveCondition":"inactive","negativeCondition":"active"}}. Dates must be ISO8601 (hence the dateFormat; adjust inputFormat to your HR format), and the firstValid fallback keeps people without an endDate active. Operators are lt/lte/gt/gte. Attach it to the cloudLifecycleState mapping in the identity profile and check it with the identity profile preview.

## tr-02
Question: Can a conditional transform check if department != Sales?
Must contain: ['conditional only supports eq', 'swap positive/negative condition or use lookup']
Must NOT contain: ['!= works']
Source of truth: conditional.md

### Answer A
Yes. The conditional transform supports eq and ne in the expression: {"type": "conditional", "attributes": {"expression": "$department ne Sales", "positiveCondition": "true", "negativeCondition": "false", "department": {"type": "accountAttribute", "attributes": {"sourceName": "HR", "attributeName": "department"}}}}. Values are compared as strings, case-sensitive, without quotes; only eq/ne are supported, no and/or.

### Answer B
Not directly: the conditional transform's expression only supports eq (any other operator throws IllegalArgumentException) and compares case-sensitive strings, e.g. "expression": "$dept eq Sales". To express != just swap the outputs: positiveCondition is the 'is Sales' value and negativeCondition the 'not Sales' value, with dept defined as an attribute variable (e.g. an identityAttribute or accountAttribute transform). Operands must not be null, so wrap the input in firstValid with a static fallback. For multiple values use a lookup transform with a default.

## tr-03
Question: Which attributes does substring need?
Must contain: ['begin required', 'end optional, beginOffset/endOffset']
Must NOT contain: ['start required']
Source of truth: substring.md

### Answer A
substring requires begin (zero-based start index; -1 means start at 0) and optionally end (exclusive; -1 or absent = to the end of the string), plus optional beginOffset and endOffset added to them; input can be explicit or implicit. Example: {"type":"substring","attributes":{"begin":0,"end":5}}. Use begin, not start (some provisioning-policy docs show start, which doesn't match the operation reference). For the last n characters use getEndOfString.

### Answer B
substring requires begin (int, 0-based start index) and optionally end (exclusive). Optional beginOffset and endOffset adjust the indices; input is optional (otherwise uses the attribute value from the source mapping). Use -1 for begin to indicate start of string and end -1 for end of string. Example: {"type": "substring", "attributes": {"begin": 0, "end": 3}}.

## tr-04
Question: How do I get the manager's email into an identity attribute?
Must contain: ['getReferenceIdentityAttribute (rule-based, Cloud Services Deployment Utility) with uid manager and attributeName email']
Must NOT contain: []
Source of truth: get-reference-identity-attribute.md

### Answer A
Use the getReferenceIdentityAttribute operation, a rule-type transform backed by the built-in Cloud Services Deployment Utility rule: {"name":"Manager Email","type":"rule","attributes":{"name":"Cloud Services Deployment Utility","operation":"getReferenceIdentityAttribute","uid":"manager","attributeName":"email"}}. uid "manager" looks up the identity's manager (or give an identity's uid). Map it to your identity attribute (e.g. managerEmail) in the identity profile and preview it; it needs the manager attribute to be populated (manager correlation).

### Answer B
Use the getReferenceIdentityAttribute transform: {"type": "getReferenceIdentityAttribute", "attributes": {"name": "manager", "attributeName": "email"}} as the identity attribute mapping. name is 'manager' (or an identity ID/uid) and attributeName is the target identity attribute. Note it is evaluated at refresh time and won't update automatically when only the manager's email changes until the report is refreshed.

## ru-01
Question: Can my cloud rule call context.getObjectByName to load an identity?
Must contain: ['no: context. and getObjectByName are forbidden', 'use idn (IdnRuleUtil) helpers']
Must NOT contain: ['yes']
Source of truth: rules index restrictions

### Answer A
No. context. calls and object-store methods (getObject*, getObjectByName, search(, countObjects, update(...)) are forbidden in cloud rules and will be rejected by review/lint. Use the read-only IdnRuleUtil helpers via idn instead, e.g. idn.getIdentityById(...), idn.findIdentitiesBySearchableIdentityAttribute(...), idn.getAccountAttribute(...), idn.attrSearchGetIdentityName(...) (account search methods need the attribute promoted via /accounts/v1/search-attribute-config). Avoid iterating over all identities.

### Answer B
No. Cloud rules cannot use context (SailPointContext) methods like getObjectByName, search, or saveObject; those are forbidden in the ISC rule review. Use the provided idn (IdnRuleUtil) helpers such as idn.getIdentityById? (not available), idn.findIdentitiesBySearchableIdentityAttribute, idn.getFirstAccount/getAccountsByIdentity... or the identity object passed into the rule. Connector rules don't have context either.

## ru-02
Question: How do I deploy a JDBC provision rule and attach it to the source?
Must contain: ['connector rule: POST /connector-rules/v1 (no SailPoint review)', 'attach with PATCH /connectorAttributes/jdbcProvisionRule']
Must NOT contain: ['submit to SailPoint for review']
Source of truth: connector-rules index

### Answer A
JDBCProvision is a connector rule, so it's self-service: optionally validate with POST /connector-rules/v1/validate, then create it with POST /connector-rules/v1 (body with name, type JDBCProvision, signature, sourceCode.script, attributes); it must return a sailpoint.object.ProvisioningResult. Then attach it to the JDBC source with PATCH /sources/v1/{id}, Content-Type application/json-patch+json, body [{"op":"add","path":"/connectorAttributes/jdbcProvisionRule","value":"<Rule Name>"}]. Logs are in ccg.log on the VA; no SailPoint review is needed.

### Answer B
JDBC provision rules are connector rules (type JDBCProvision) executed on the VA, so they don't need SailPoint review. Create them with POST /beta/connector-rules (body with name, type JDBCProvision, sourceCode {version, script}); validate with /beta/connector-rules/validate. Attach by PATCH /v3/sources/{id} with op add/replace on /connectorAttributes/connectionParameters (or the operation-specific attribute) referencing the rule name, e.g. setting the provisioning rule name for Create/Modify etc. in connectionParameters or via 'jdbcProvisionRule'. I'm unsure of the exact attribute path.

## ru-03
Question: What must a Correlation rule return?
Must contain: ['Map with identityAttributeName and identityAttributeValue']
Must NOT contain: []
Source of truth: correlation_rule.md

### Answer A
A Correlation rule (inputs account, application, idn, log) must return a java.util.Map with the keys identityAttributeName and identityAttributeValue, e.g. returnMap.put("identityAttributeName", "email"); returnMap.put("identityAttributeValue", calculatedEmail); return returnMap;. The attribute named must be a searchable identity attribute. It is attached to the source as accountCorrelationRule and runs before the configured correlation; null-check the account attributes you read.

### Answer B
A Correlation rule must return a Map with either identityAttributeName and identityAttributeValue (e.g. returnMap.put("identityAttributeName", "email"); returnMap.put("identityAttributeValue", account.getStringAttribute("mail"))) or identity name/object... In ISC the supported keys are identityAttributeName/identityAttributeValue; return an empty map to leave the account uncorrelated. Inputs are account (ResourceObject), log, idn.

## ru-04
Question: File name convention for submitting a cloud rule?
Must contain: ['Rule - {type} - {name}.xml']
Must NOT contain: []
Source of truth: cloud-rules index

### Answer A
Name the file Rule - <Type> - <Name>.xml, e.g. Rule - BeforeProvisioning - Set AD OU.xml, where the XML <Rule name="..." type="..."> matches. Submit via a support ticket (expert services) for review; it is reviewed and deployed. Use the Rule XML with the DOCTYPE sailpoint.dtd header and a Description.

### Answer B
Name the file Rule - {type} - {name}.xml, e.g. Rule - IdentityAttribute - Calculate Lifecycle.xml or Rule - BeforeProvisioning - AD BeforeProvisioningRule.xml, where type matches the rule's type attribute and name its name attribute. Submit it via support ticket with the RDK/validator output and tenant; when updating logic, keep the same file/rule name so changes trace to a single object (use a -TEMP pattern for versioned testing as described in the process).

## se-01
Question: Search query: identities active with a disabled Active Directory account.
Must contain: ['attributes.cloudLifecycleState:active AND @accounts(source.name… AND disabled:true) in one @accounts group']
Must NOT contain: ['eq syntax', 'two separate @accounts groups']
Source of truth: building-query

### Answer A
Index identities: attributes.cloudLifecycleState:active AND @accounts(source.name.exact:"Active Directory" AND disabled:true). Both account conditions must sit inside the same @accounts( ) group so they apply to the same account; use your exact source name. API: POST /search/v1?limit=250 with {"indices":["identities"],"query":{"query":"..."},"sort":["id"],"queryResultFilter":{"includes":["id","name","attributes.email"]}}, paging with searchAfter beyond 10,000.

### Answer B
Index identities: attributes.cloudLifecycleState:active AND @accounts(source.name:"Active Directory" AND disabled:true). Alternatively use status/inactive flags: inactive:false. Use the exact source name in quotes; POST /v3/search with indices ["identities"] and query {"query": "..."}.

## se-02
Question: Find who updated a role last month in audit events.
Must contain: ['index events', 'technicalName ROLE_UPDATE_PASSED (or action)', 'created:[now-1M TO now]']
Must NOT contain: []
Source of truth: audit events docs

### Answer A
Search the events index: type:"Role" or objects:ROLE AND action:update? e.g. query "technicalName:ROLE_UPDATE* AND created:[now-1M/M TO now/M}" or "name:\"Update Role\" AND created:[2026-10-01 TO 2026-10-31]". The actor is in actor.name; target.name is the role. Use POST /v3/search with indices ["events"] and sort ["-created"].

### Answer B
Search the events index: technicalName:ROLE_UPDATE_PASSED AND created:[2026-10-01 TO 2026-10-31] (or created:[now-1M TO now] for the last month rolling); add target.name:"My Role" to restrict to one role. The actor.name field shows who did it. Via API: POST /search/v1 {"indices":["events"],"query":{"query":"technicalName:ROLE_UPDATE_PASSED AND created:[now-1M TO now]"},"sort":["-created"]}, or queryType DSL with match on target.name/actor.name for precise matching. Audit events are retained about one year plus the current month.

## se-03
Question: Is .exact supported on email?
Must contain: ['no (.exact not supported on email, id, phone, employeeNumber, processingState, type, tags, booleans, numbers)']
Must NOT contain: ['yes']
Source of truth: building-query

### Answer A
No. .exact (exact, case-sensitive match) isn't supported on email, nor on id, phone, employeeNumber, processingState, type, tags, booleans or numbers. Search is case-insensitive by default, so use email:"john.doe@acme.com" (or a wildcard like attributes.email:*@acme.com) and compare the exact value client-side if needed. .exact works on text fields like name and source.name.

### Answer B
Yes. Text fields like email have a .exact subfield for case-sensitive exact match, e.g. email.exact:"John.Doe@acme.com" or attributes.email.exact:... Without .exact the query is analyzed (tokenized, case-insensitive).
