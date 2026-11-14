# Workflow operators

Compiled from https://documentation.sailpoint.com/saas/help/workflows/workflow-operators.html (re-checked 14 November 2026). Every choice operator needs a default path; every branch ends with an end step.

## Comparisons (choice)

| Operator | Value 1 | Operators | Value 2 |
|---|---|---|---|
| Compare Boolean | JSONPath to a boolean | Equals | static or JSONPath |
| Compare Numbers | JSONPath to a number | Equals, Is Less Than, Is Greater Than, Is Less Than or Equal To, Is Greater Than or Equal To | static or JSONPath |
| Compare Strings | JSONPath to a string (required) | Equals, Does Not Equal, Contains, Does Not Contain, Is Less/Greater Than (or Equal To), Starts With, Ends With, **Matches** (RE2 regex, matches anywhere; invalid pattern = no match) | required |
| Compare Timestamps | JSONPath to a timestamp | date: Is on the Date, Is Before, Is After, Is On or Before, Is On or After · relative: Is After/Before/On or Before/On or After **X Days Ago** or **X Days in the Future** | ISO 8601 date, or an integer number of days (no unit) |
| Verify Data Type | JSONPath | Exists, Boolean, Number, String, Timestamp, Null | — |
| Define Comparison | several conditions of the types above with And/Or, Not, groups (groups joined with And); Advanced JSON editor available | | |

## Variables

**Define Variable** — builds a new variable from text or an attribute through up to **50** chained operations; output is a string (an integer if the last op is Get Index).
- Text: Substring (start, length; `end`/last-n chars only in Advanced editor), Concatenate Strings, Trim, Replace (pattern → replacement), Get Index.
- Dates: Add Time (s, min, h, days, months; result ≤ 1 year from the original), Subtract Time (… years), Date Formatter.
- Numbers: Add, Subtract, Multiply, Divide, Modulo with precision and rounding mode (Half Up default, Half Down, Always Round Down/Up, Truncate).

**Update Variable** — same operations on an existing variable in scope (outside a loop: variables defined outside loops; inside a loop: only variables of that loop).

The older "Beta" Define Variable keeps running in existing workflows but can't be added to new ones.

## Loops

**Loop (parallel)**
- Loop Input: JSONPath to an array from an earlier step — **max 250 items** (more = workflow fails).
- Context: JSONPath to another step whose data you need inside the loop. Inside the loop only Loop Input and Context are reachable: `$.loop.loopInput` (current item) and `$.loop.context`.
- Order isn't guaranteed; every iteration runs even if some fail; each branch inside needs its own end step.
- Output: `loopOutput` with `successfulItems` and `failureItems`.

**Serial Loop (sequential)**
- For Loop over an array (**max 1000 items**) or While Loop on a condition checked before each iteration.
- Stops at the first failed iteration; **Break Loop** exits early. Test runs stop after 50 iterations.

## End steps

- **Success** — execution succeeded.
- **Failure** — execution failed; Failure Name (required) and Failure Details (optional, appears in execution results). Tests that end here count as failed.
