---
name: isc-transforms
description: SailPoint Identity Security Cloud (ISC/IdentityNow) transforms reference. Use when someone needs to compute or reshape an identity attribute or an account attribute in a create profile (lowercase, concatenate, dates, lookups, conditionals, usernames, lifecycle state, e-mail), asks which transform type does something, wants a transform JSON written, reviewed or debugged, or asks about Velocity in transforms or transforms vs rules.
---

# SailPoint ISC transforms

A transform is a JSON object `{ "name", "type", "attributes" }` that turns an input value into an output value. Used in **identity profile mappings** (identity attributes) and **account create profiles / provisioning policies** (account attributes). Nest them freely; only the root has a `name`. Max 400 KB.

## How to answer

1. Restate the input → output the user wants with a concrete example value.
2. Pick the operation(s) from the table below; open `references/operations/<file>.md` for the exact attributes, defaults and examples. Don't invent attributes.
3. Write the complete JSON (root `name`, nested transforms without `name`), with **explicit inputs** where the source matters, and handle missing data (`firstValid`, `static` fallback, `conditional`).
4. Say where to attach it (identity profile mapping vs create profile field) and how to test it (identity profile preview; account side needs a real create event).
5. Mention API management: `GET/POST/PUT/DELETE /transforms/v1` (see `isc-api` → `endpoints/transforms.md`); `requiresPeriodicRefresh: true` when the value depends on time (date compares, lifecycle by date).

## Operations

| Need | `type` | File |
|---|---|---|
| Read an account attribute from a source | `accountAttribute` (`sourceName`, `attributeName`, optional `accountSortAttribute`, `accountSortDescending`, `accountReturnFirstLink`, `accountFilter`, `accountPropertyFilter`) | account-attribute |
| Read an identity attribute | `identityAttribute` | identity-attribute |
| First non-null of several inputs | `firstValid` | first-valid |
| Fixed value / Velocity template | `static` (`value`, can use `$var` from other attributes) | static |
| Reuse another saved transform | `reference` (`id`) | reference |
| If/else | `conditional` (`expression` `eq`-only Velocity compare, `positiveCondition`, `negativeCondition`) | conditional |
| Map values (code → label) | `lookup` (`table`, `default`) | lookup |
| Concatenate | `concat` (`values[]`) | concatenation |
| Case / trim | `lower`, `upper`, `trim` | lower, upper, trim |
| Substrings & search | `substring`, `indexOf`, `lastIndexOf`, `split` (`delimiter`, `index`), `getEndOfString` (rule-based), `leftPad`, `rightPad`, `join` | substring, index-of, last-index-of, split, get-end-of-string, left-pad, right-pad, join |
| Replace | `replace` (`regex` → `replacement`, all matches), `replaceAll` (`table` of several regex → replacement pairs) | replace, replace-all |
| Clean names | `normalizeNames`, `decomposeDiacriticalMarks` (é → e) | name-normalizer, decompose-diacritical-marks |
| Dates | `dateFormat` (ISO8601, LDAP, PEOPLE_SOFT, EPOCH_TIME_JAVA/WIN32 or Java patterns), `dateMath` (`expression` like `now-5d/d`, `roundUp`), `dateCompare` (`firstDate`, `secondDate`, `operator` lt/lte/gt/gte, `positiveCondition`, `negativeCondition`) | date-format, date-math, date-compare |
| Display name | `displayName` | display-name |
| Phone / country / language codes | `e164phone`, `iso3166`, `rfc5646` | e164-phone, iso-3166, rfc-5646 |
| Encode | `base64Encode`, `base64Decode` | base64-* |
| Random / unique values (create profile) | `randomAlphaNumeric`, `randomNumeric`, `uuid`, `usernameGenerator` (patterns + uniqueness, create profile only), `generateRandomString` (rule-based) | random-*, uuid-generator, username-generator, generate-random-string |
| Manager's (or any referenced identity's) attribute | `getReferenceIdentityAttribute` (rule-based, e.g. `uid: "manager"`) | get-reference-identity-attribute |
| Custom Java logic | `rule` (calls a cloud rule; see `isc-rules`) | rule |

Full list with one-line descriptions: `references/operations-index.md`.

## Key concepts

- **Implicit input**: the attribute chosen in the UI mapping feeds the transform. **Explicit input**: `"input": { "type": "accountAttribute", "attributes": {...} }` inside `attributes` — use it in nested transforms and anything non-trivial.
- **Velocity**: every string goes through Velocity. In `static`, other attributes of the same transform are variables: `"value": "$first.$last"` with `"first": {...transform...}`. Context: identity mappings get `identity`, `attributeDefinition`, `oldValue`; create profiles get `field`, `identity`, `application`, `current`. Tools: `$__dateTool`, `$__mathTool`, `$__numberTool`, `$__esc` (default TZ GMT, locale en_US). Guide: `references/guides/velocity-tools.md`.
- **substring** takes `begin` (required) and `end`; SailPoint's provisioning-policy guide shows `start`, which doesn't match the operation reference — use `begin`.
- **conditional** compares only with `eq` on strings: `"expression": "$dept eq Sales"`. For ranges/dates use `dateCompare`, or a lookup.
- Account-side transforms (create profiles) can use `usernameGenerator`, uniqueness checks and random generators; identity-side can't.
- Lifecycle state by dates and other recipes: `references/guides/lifecycle-state-transforms.md`, `identity-context.md`, `temporary-password.md`, `provisioning-policy-transform.md`, `use-preferred-name.md`, `your-first-transform.md`.

## Example: email = firstname.lastname@domain, lowercase, no accents

```json
{
  "name": "Email - first.last",
  "type": "lower",
  "attributes": {
    "input": {
      "type": "decomposeDiacriticalMarks",
      "attributes": {
        "input": {
          "type": "static",
          "attributes": {
            "first": { "type": "identityAttribute", "attributes": { "name": "firstname" } },
            "last":  { "type": "identityAttribute", "attributes": { "name": "lastname" } },
            "value": "$first.$last@example.com"
          }
        }
      }
    }
  }
}
```
(Spaces/apostrophes in names: wrap with a `replace` transform, `"regex": "[^A-Za-z0-9.@-]"`, `"replacement": ""`; uniqueness belongs in the create profile with `usernameGenerator`.)

## Validate before delivering

```bash
python3 scripts/validate_transform.py transform.json      # also accepts a create-profile field or a whole provisioning policy
```
Checks every nested transform against the documented types and attributes (`scripts/transform_types.json`, generated from SailPoint's docs), `name` only at the root, `conditional`/`dateCompare` syntax, Velocity variables in `static`, size. Fix ERRORs before handing the JSON over.

## Transforms vs rules

Use transforms whenever the logic is expressible with these operations; a cloud rule needs SailPoint review and is your code to maintain. Use `rule` only for things like complex uniqueness checks or logic transforms can't express. See `isc-rules`.

## Reference map

| Path | Contents |
|---|---|
| `references/transforms-overview.md` | how transforms work, syntax, template engine, implicit/explicit input, account transforms, testing, best practices |
| `references/operations-index.md` | all operations |
| `references/operations/*.md` | one page per operation: attributes, defaults, examples |
| `references/guides/*.md` | lifecycle state, identity context, provisioning policy, temp password, preferred name, Velocity tools, first transform |

Not affiliated with SailPoint; docs: https://developer.sailpoint.com/docs/extensibility/transforms
