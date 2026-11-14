# Variables and JSONPath in workflows

Sources (re-checked on the full pages 14 November 2026): SailPoint "Building Workflows", "JSONPath Expressions" and "Operators" pages; examples from sailpoint-oss/colab-workflows.

## Where data lives

| Data | Path |
|---|---|
| Trigger input | `$.trigger.<field>` — e.g. `$.trigger.identity.id`, `$.trigger.changes`, `$.trigger.formData.department`, `$.trigger.submittedBy.id`, `$.trigger.requestedItemsStatus[0].name` |
| Output of an earlier step | `$.<technicalName>.<field>` — technical name = step name in lowerCamelCase: "Get Identity" → `getIdentity`, "HTTP Request" → `hTTPRequest`, "Get Identity 1" → `getIdentity1`, "Define Variable" → `defineVariable` |
| Define Variable result | `$.defineVariable.<variableName>` |
| Inside a loop | `$.loop.loopInput` (current item), `$.loop.context.<…>` (data passed via the loop's Context) |
| Loop result after the loop | `$.loop.loopOutput.successfulItems` / `failureItems` (check the technical name of the loop step in execution history) |
| Error branch | `error.workflowErrorMessage`, `error.workflowStatusCode` |

The technical name is shown in Execution history (step input/output). Only steps that run *before* the current one are referenceable. Inside a loop, only Loop Input and Context are visible.

## Three ways to use a value

1. **JSONPath field** (UI "Choose Variable", JSON key ending in `.$`): `"id.$": "$.trigger.identity.id"`. Keeps the type (object, array, number).
2. **Inline variable** in any text field: `Hello {{$.getIdentity.attributes.firstname}}` — always a string. Two braces, `$`, dot path; spaces inside optional; same-step variables can drop the step name. Works inside URLs and search queries: `"query": "name.exact:\"{{$.defineVariable.roleName}}\""`.
3. **Send Email templating context** → Velocity: `"context": {"mgr.$": "$.getIdentity.managerRef.name"}` then `${mgr}` in body/subject.

## JSONPath support in steps (RFC 9535 + jsonslice)

- Filters: `$.getAccounts.accounts[?(@.sourceName == "Active Directory")]`, combine with `&&`, `||`; regex `=~`.
- Slices/unions: `$.users[0:5]`, `$.roles[0,2,4]`, wildcards `$.*.body.user.name`.
- Functions at the end of a path: `length()`, `count()` (may not be numeric with a condition), `size()`, `now()` → current timestamp, `RFC3339()` (e.g. `$.now().RFC3339()`), `JSON()` (object → JSON string).
- An inline variable can be used inside a filter: `$.getAccounts.accounts[?(@.sourceName == "{{$.defineVariable2.sourceName}}")]`.

## Trigger filters (different engine: Jayway)

- Must return a non-empty result for the workflow to start; the basic editor allows max 5 conditions (advanced expressions can be longer).
- Operators: `== != < <= > >= =~ in nin subsetof anyof noneof size contains && || !`; functions `length()`, `concat()`.
- Recipes:
  - attribute changed: `$.changes[?(@.attribute == "department")]`
  - lifecycle to terminated: `$.changes[?(@.attribute == "cloudLifecycleState" && @.newValue == "terminated")]`
  - one of several values: `$.changes[?(@.attribute == "department" && @.newValue in ["Sales","Finance"])]`
  - specific source on aggregation: `$[?(@.source.name == "Active Directory")]`
  - failed aggregation: `$[?(@.status == "Error")]`
  - access request for a given item type: `$.requestedItemsStatus[?(@.type == "ROLE")]`
  - identity triggers, booleans as strings: `$[?($.attributes.isManager == "false" && $.attributes.department == "Sales")]`
  - form answers: `$[?(@.formDefinitionId == "<id>" && @.formData.department == "IT")]`
- Validate before saving: `POST /trigger-subscriptions/v1/validate-filter` with `{"input": <sample payload>, "filter": "<expression>"}` (escape inner quotes), or https://developer.sailpoint.com/tools/json-path-evaluator.

## Common mistakes

- Using `$.getIdentity…` before the Get Identity step runs, or from inside a loop without passing it as Context.
- Writing the display name instead of the technical name (`$.Get Identity.name`).
- Forgetting `.$` on a key in JSON → the JSONPath is sent as a literal string.
- Expecting `{{ }}` to keep arrays/objects — use a JSONPath field instead.
- Testing a trigger filter in the step evaluator (or the reverse): the engines differ.
