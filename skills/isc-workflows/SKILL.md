---
name: isc-workflows
description: SailPoint Identity Security Cloud (ISC/IdentityNow) Workflows reference. Use when someone asks which workflow trigger to use for a scenario, how to filter a trigger, which action or operator does something, how to reference variables (JSONPath, inline {{ }} variables, loops), workflow limits, error handling, testing, external/scheduled triggers, or wants a workflow JSON written, reviewed or debugged.
---

# SailPoint ISC Workflows

A workflow = **one trigger + steps** (actions, operators, end steps). The trigger provides a JSON input; every step adds its output to the context, and later steps read it with JSONPath. Built in the UI (Admin > Workflows), stored and exchanged as JSON, also manageable through `/workflows/v1` and `/workflow-library/v1`.

## How to answer

**"Which trigger should I use for X?"**
1. Classify the scenario: something happened in ISC (event) · on a timetable (scheduled) · started by another system (external) · started by a user (form submitted / interactive launcher) · access request approval (Access Request Submitted + Approval Policy).
2. Pick from the decision table below, then open `references/triggers.md` for the exact trigger, its filter support and caveats.
3. Give a **filter** that narrows the events (JSONPath on the trigger payload; payload samples are in the `isc-event-triggers` skill under `references/triggers/`).
4. Mention prerequisites (licence/service, NCD configured, etc.) and gotchas (e.g. "fires on aggregation *and* provisioning").

**"Which action / how do I…"** → `references/actions.md` (inputs, outputs, limits) and `references/operators.md`.
**Variables, JSONPath, loops** → `references/variables-and-jsonpath.md`.
**Write or fix a workflow JSON** → `references/workflow-json.md` (structure, rules, full examples) + `references/workflow-api-schemas.md` (field-level schema).
**Programmatic management** → `isc-api` skill, `endpoints/workflows.md` and `endpoints/workflow-library.md`; `GET /workflow-library/v1/triggers|actions|operators` returns the exact IDs and form fields available **in the user's tenant** — recommend it whenever an ID isn't in the references.

## Trigger decision table

| Scenario | Trigger |
|---|---|
| New hire / identity appears (joiner) | Identity Created |
| Attribute changes: department, manager, location (mover) | Identity Attributes Changed, filtered on `$.changes[?(@.attribute == "department")]` |
| Lifecycle state change, e.g. → terminated (leaver) | Identity Lifecycle State Changed, or Identity Attributes Changed filtered on `cloudLifecycleState`; use *Lifecycle State Change Processed* if you must run after the LCS actions were applied |
| Identity removed from ISC | Identity Deleted |
| Account created / updated / deleted (via aggregation **or** provisioning) | Account Created / Account Updated / Account Deleted |
| Change made directly on the source, outside ISC | Native Change Account Created / Updated / Deleted (needs Native Change Detection on the source) |
| Account unused for N days | Account Inactivity Detected (`$[?(@.trigger.daysInactive > 180)]`) |
| Aggregation finished / failed | Account Aggregation Completed (or Accounts Collected for Aggregation, before processing) |
| Provisioning finished on a source (success/failure) | Provisioning Completed |
| Custom approval for an access item | Access Request Submitted (item's approval type = workflow) + **Approval Policy** action |
| React to an approved/denied request | Access Request Decision |
| Certification campaign lifecycle | Campaign Activated / Generated / Ended, Certification Signed Off |
| Run every night / weekly report | Scheduled Trigger (daily, weekly, monthly, yearly with time pickers, or a cron string — cron strings honour hours only, not minutes) |
| Saved search results are ready | Scheduled Search |
| Ticketing tool, script, another system starts it | External Trigger (OAuth client per workflow) |
| A form is submitted | Form Submitted (basic: one element/value; advanced: JSONPath) |
| A user clicks a launcher | Interactive Trigger (Launchpad) |
| Source created/updated/deleted, VA cluster status, outliers, machine identities, SoD/CIEM, risk signals, ServiceNow catalog | see `references/triggers.md` |

If two triggers fit, say which one fires earlier/more often and why you'd pick one.

## Core facts to get right

- **Step references**: `$.trigger.<field>` for trigger input; `$.<stepTechnicalName>.<field>` for step output — the technical name is camel-cased from the step name (e.g. `$.getIdentity.attributes.email`, `$.hTTPRequest.body`); check it in Execution history if unsure. Inside loops: `$.loop.loopInput` and `$.loop.context`.
- **In JSON**, an attribute that takes a JSONPath ends with `.$`: `"recipientId.$": "$.trigger.identity.id"`. Static values use the plain key.
- **Inline variables** in text fields: `{{$.getIdentity.attributes.displayName}}`. One variable per pair of braces; a syntax error renders that variable as an empty string (or plain text), and a value that resolves to an empty string shows the variable as plain text.
- **Send Email** body/subject use Velocity variables from the *Templating Context* map: `{"name.$": "$.getIdentity.name"}` → `${name}` in the body.
- **Trigger filters** use the Jayway JSONPath engine (the basic editor allows max **5 conditions**); **step expressions** use RFC 9535 + jsonslice extensions (`length()`, `count()`, `now()`, `RFC3339()`, `JSON()`). Same syntax mostly, not identical — test each in its own place.
- **Error handling** is per action (… > Enable Error Handling): creates success/error branches; on the error branch the step exposes `error.workflowErrorMessage` and `error.workflowStatusCode` (pick them with the Variable Selector to get the exact path). Without it, an action error fails the execution. To fail on purpose, end the error branch in a Failure step.
- **Every branch ends** in Success or Failure; choice operators need a default path.
- **Testing executes real actions** (emails, provisioning). Disable a step ("Enable Step" off) to mock it and supply mock output.
- Workflows are created **disabled**; enable after testing. There are tenant limits on steps per workflow and on enabled workflows (numbers not published; the UI errors when exceeded).
- **Ownership**: the creating admin becomes owner and a personal access token is generated for the workflow. If that admin leaves, the workflow is orphaned and fails with unauthorized errors — reassign the owner (UI, or `PATCH /workflows/v1/{id}` with `[{"op":"replace","path":"/owner","value":{"type":"IDENTITY","id":"<new admin>"}}]`, which generates a new token) or recreate it under a non-expiring admin before they leave.

## Limits (from SailPoint docs)

| Item | Limit |
|---|---|
| Definition size | 400 KB; definition + input 1.5 MB; payload 10 MB |
| Trigger filter | basic editor: max 5 conditions (advanced JSONPath filters can be longer) |
| Executions | ~400k/day per tenant at full speed, then 5/s; per workflow: alert at 100k, blocked at 150k (loop runs count here) |
| Execution history | 90 days in UI (API for longer); search index `workflow history` 90 days |
| Loop (parallel) | 250 items; Serial loop (for) 1000 items; test runs stop after 50 iterations |
| Define/Update Variable | 50 operations |
| HTTP Request | 90 s timeout, honours Retry-After headers |
| Get Identity / Get Accounts / Get Access / Get List of Identities | 1 min, max 250 items |
| Manage Access | 30 min; Manage Accounts 1 h |
| Form | deadline ≤ 30 days; Wait For 60 s–30 days; Wait Until ≤ 180 days |
| Approval Policy / Generic Approval | timeout ≤ 90 days, up to 5 reviewers |
| Scheduled trigger | cron strings: hours only (no minutes); daily/weekly/monthly use time pickers (a SailPoint export stores a `:30` weekly time — check minutes in the UI); runs can overlap |

Limits change; when one is decisive for a design, tell the user to confirm it in the current SailPoint docs (links at the top of each reference file).

## Validate before delivering

Whenever you write or review workflow JSON, save it and run:
```bash
python3 scripts/validate_workflow.py workflow.json
```
It checks trigger shape, filters, step graph (start, `nextStep`, `defaultStep`, every branch ends, no dead ends, reachability), loop bodies, `.$` keys, `{{ }}` syntax, references to step technical names, secrets in plain text, legacy API URLs. Fix every ERROR; explain any WARNING you leave. It can't prove the actions will succeed: say that the workflow still needs a test run in the tenant.

## Reference map

| File | Contents |
|---|---|
| `references/triggers.md` | every trigger: ID (when known), filter support, caveats, use cases |
| `references/actions.md` | every action: inputs, outputs, limits |
| `references/operators.md` | compare operators, Define Comparison, Define/Update Variable, loops, end steps |
| `references/trigger-payload-fields.md` | input fields of every workflow trigger (what `$.trigger.…` contains) |
| `references/variables-and-jsonpath.md` | `$.trigger`, step names, inline vars, loop context, functions, filter recipes |
| `references/workflow-json.md` | JSON structure rules + complete examples (event, scheduled + loop, external + HTTP) |
| `references/workflow-api-schemas.md` | generated schema: workflow body, trigger, attributes, execution |

Payload samples for event triggers live in the `isc-event-triggers` skill. Not affiliated with SailPoint; product docs: https://documentation.sailpoint.com/saas/help/workflows/index.html
