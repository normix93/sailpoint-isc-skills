# Results

40 questions, 0–2 points each (max 80). Blind grading by a separate agent.

| Skill | Questions | Without skills | With skills |
|---|---|---|---|
| isc-api | 8 | 6/16 | 16/16 |
| isc-event-triggers | 5 | 6/10 | 10/10 |
| isc-notifications | 6 | 3/12 | 12/12 |
| isc-rules | 4 | 6/8 | 8/8 |
| isc-search | 3 | 3/6 | 6/6 |
| isc-transforms | 4 | 3/8 | 8/8 |
| isc-workflows | 10 | 8/20 | 20/20 |
| **Total** | 40 | **35/80 (44%)** | **80/80 (100%)** |

## Per question

| id | without | with | grader note (without) | grader note (with) |
|---|---|---|---|---|
| api-01 | 0 | 2 | Lists status as a filter (forbidden); legacy path unmapped. | Correct path, filters with operators, query params, limit 250/offset, stable sorters. |
| api-02 | 1 | 2 | Legacy path unmapped; filters incomplete (no accessRequestId, created). | Correct path, all filters with operators, sorters created/modified. |
| api-03 | 0 | 2 | Suggests Search with @accounts as alternative (forbidden); legacy path unmapped. | Correct endpoint, filters, limit 250; correctly warns against Search. |
| api-04 | 1 | 2 | Hedged, guesses a wrong path first; correct one only as alternative. | Correct mapping, per-service versioning, legacy until end of support, avoid /latest. |
| api-05 | 2 | 2 | json-patch+json and JSON Patch op array. | json-patch+json and JSON Patch op array, correct examples. |
| api-06 | 0 | 2 | States limit is per access token (forbidden). | 100/10s per client_id and version, 429 Retry-After, backoff. |
| api-07 | 0 | 2 | Says EQ is accepted (forbidden). | Lowercase operators required, double-quoted strings. |
| api-08 | 2 | 2 | searchAfter, unique sort field, last record's sort values. | searchAfter, sort on id, pass last sort values. |
| wf-01 | 2 | 2 | Correct trigger and department filter. | Correct trigger and department filter. |
| wf-02 | 0 | 2 | Claims cron 30 6 * * 1-5 works (forbidden). | Cron hours only, weekly option to check in UI, overlap noted. |
| wf-03 | 1 | 2 | loopInput and context right; speculative $.loop.index and output path. | loopInput, context, only these two visible. |
| wf-04 | 1 | 2 | 250 hedged; no serial 1000; says fail or truncate. | 250 parallel, 1000 serial, exceeding fails. |
| wf-05 | 1 | 2 | No-wait and second workflow right; missing failedAccessRequests behavior. | All must facts present. |
| wf-06 | 1 | 2 | Only inline {{}}; misses Templating Context and ${name}. | Templating Context map, ${displayName}, and inline alternative. |
| wf-07 | 1 | 2 | Reassign advice good; misses auto-created PAT and orphaned/unauthorized failure. | Owner+PAT, orphaned unauthorized failure, reassign before leaving. |
| wf-08 | 1 | 2 | Correct concept but legacy /v3 paths unmapped; no UI token step. | External trigger, New Access Token, correct execute path, $.trigger. |
| wf-09 | 0 | 2 | Claims requestedItemsStatus in Submitted (forbidden). | requestedItem singular; requestedItemsStatus belongs to Decision. |
| wf-10 | 0 | 2 | Guessed wrong variable names; misses workflowErrorMessage/StatusCode. | Enable Error Handling, workflowErrorMessage, workflowStatusCode. |
| et-01 | 0 | 2 | Says request proceeds on timeout, contradicting failure behavior. | Trigger, three response fields, one subscription, failure on no response. |
| et-02 | 1 | 2 | 10s, ASYNC, DYNAMIC present; deadline vague and hedged. | 10s, ASYNC ack then callback with secret before responseDeadline, DYNAMIC. |
| et-03 | 2 | 2 | 50. | 50. |
| et-04 | 2 | 2 | Correct filter on Identity Attributes Changed. | Correct filter on Identity Attributes Changed. |
| et-05 | 1 | 2 | Path and body right; no quote escaping, uses single quotes. | Correct path, input+filter body, escape quotes. |
| nt-01 | 0 | 2 | Wrong template name/keys, guessed variables, no variables endpoint. | Access Request Decision to requester, correct variables, endpoint. |
| nt-02 | 0 | 2 | Suggests deleting template/toggle; misses no_send/Stop. | no_send/Stop subject, overrides process settings caveat. |
| nt-03 | 1 | 2 | Probably not, but misses v1/v2 reason and v2 globals. | v2 template, $user v1 only, use $__recipient/$__util. |
| nt-04 | 1 | 2 | Real event advice; misses globals-only and conditional sections. | Only globals, conditionals skipped, real event with test address. |
| nt-05 | 1 | 2 | Inline styles advised but hedged; unclear on comments. | Sanitizer strips style/head/comments; use inline styles. |
| nt-06 | 0 | 2 | Suggests per-template From via API; misses Reply-To. | Global/brand From, verified, Reply-To per template. |
| tr-01 | 1 | 2 | dateCompare correct; missing requiresPeriodicRefresh. | dateCompare with now, operator, conditions, requiresPeriodicRefresh true. |
| tr-02 | 0 | 2 | Claims ne works in conditional (forbidden). | Only eq; swap outputs or use lookup. |
| tr-03 | 2 | 2 | begin required, end optional, offsets. | begin required, end optional, offsets. |
| tr-04 | 0 | 2 | Wrong JSON: non-existent type and name instead of uid; not rule-based. | Rule-type transform, Cloud Services Deployment Utility, uid manager, attributeName email. |
| ru-01 | 1 | 2 | Right core; confusing wrong note on getIdentityById availability. | Forbidden context/getObjectByName; idn helpers. |
| ru-02 | 1 | 2 | Connector rule no review right; unsure/wrong attach path. | POST /connector-rules/v1, no review, PATCH jdbcProvisionRule. |
| ru-03 | 2 | 2 | Map with identityAttributeName/Value. | Map with identityAttributeName/Value. |
| ru-04 | 2 | 2 | Rule - Type - Name.xml. | Rule - {type} - {name}.xml. |
| se-01 | 2 | 2 | Correct query, single @accounts group. | Correct query, single @accounts group. |
| se-02 | 1 | 2 | Events index and wildcard technicalName; speculative messy syntax. | Events, ROLE_UPDATE_PASSED, created:[now-1M TO now]. |
| se-03 | 0 | 2 | Says yes (forbidden). | No, with full unsupported list. |
