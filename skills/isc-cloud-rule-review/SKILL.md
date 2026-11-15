---
name: isc-cloud-rule-review
description: Pre-submission review of SailPoint Identity Security Cloud (ISC/IdentityNow) cloud rules and connector rules against SailPoint's published rule guidelines — rule XML format, supported and deprecated rule types, code restrictions (context, getObjectByName, System.out, threads...), logging, IdnRuleUtil methods and signatures, null handling, external calls, file access, loops over identities, commented-out code, file naming — with a Markdown report to attach to the SailPoint review ticket. Use before sending a rule to SailPoint, when a rule was rejected, or when someone asks whether a rule will pass review.
---

# ISC rule review before submission

Every cloud rule goes through **SailPoint's rule review** before it is deployed (support ticket, Expert Services
hours). The review is an integrity check against the published guidelines — it does **not** check that the rule
works. A rejection costs a resubmission and another day. This skill finds what the reviewers reject, before they do.

Writing the rule itself (signatures, templates, examples, IdnRuleUtil): `../isc-rules/`. Process details and
timings: `references/review-process.md`.

## Do this

1. Run the reviewer on the exact file you will attach:
   ```bash
   python3 scripts/review_rule.py "Rule - IdentityAttribute - Calculate Lifecycle.xml" --report review.md
   ```
   Bare BeanShell: add `--type IdentityAttribute`. Connector-rule JSON (`POST /connector-rules/v1` body) works too.
   `--codes` lists every check with the guideline it comes from; `--json` for tooling.
2. Fix every **ERROR** (breaks a documented restriction or standard: SailPoint rejects or the platform blocks it).
   Fix or justify every **WARNING** (guideline/best-practice issues that slow the review or are likely rejections);
   justifications go in comments in the rule ("I did this because...").
3. Test the rule (RDK or a sandbox); the reviewer is static.
4. Submit: rule file named `Rule - {type} - {name}.xml`, the report as validator output, tenant name
   (`acme-sb.identitynow.com` / `acme.identitynow.com`), approval for Expert Services hours. One rule per ticket
   unless they must be deployed together.

## What gets a rule rejected (and the check that catches it)

| Guideline | Checks |
|---|---|
| Supported rule types only, correct type annotated; no deprecated types (CertificationExclusion, IdentitySelector, Integration) | R003–R005, R008 |
| Code restrictions: `context.`, `getObjectById/ByName`, `.search()`, `.toXml()`, `System.out`, `Thread`, `.sleep()`, `public static`, BeanShell commands... (generated list) | R020, R021 |
| Logging: right levels (no `log.error` for info), no sensitive data, no own loggers, no full-object dumps | R030–R033 |
| Execution: no connections or call-outs (connector rules use the supplied connection), no files, no waits | R040–R042 |
| Error handling: try/catch that does something, null checks, no dead code | R050–R052 |
| Performance: no iteration over accounts/identities, no lookups in loops | R060, R061 |
| Only real IdnRuleUtil methods with the right arguments; search operations `Equals`/`StartsWith` only | R070–R072 |
| Uniqueness checks belong in AttributeGenerator rules, not IdentityAttribute | R073 |
| Variables that the rule type does not receive (e.g. `context`, `application` where it is not an input) | R074 |
| Outputs: value-returning types must return; BeforeProvisioning changes `plan`; correlation returns the map | R080–R082 |
| Standards: no commented-out code or TODOs, indented, UTF-8, no `&amp;`/`&lt;`/`&gt;`, file naming, description, no secrets | R002, R010–R015, R090–R093 |
| One rule per use case (no `v2`/`new`/`copy` names; `-TEMP` only for change windows) | R095 |

## Reading the report

- **Ready to submit**: no findings. **Can be submitted**: only warnings — read them, fix or explain.
  **Fix before submitting**: at least one error.
- Each finding has the line in the file (counted from the top of the XML) and the guideline URL.
- Known limits: it cannot prove a value is never null, judge if a rule is "the last resort", or see your tenant.

## Typical rewrites

| Instead of | Use |
|---|---|
| `context.getObjectByName(Identity.class, name)` | `idn.getIdentityById(id)` or `idn.findIdentitiesBySearchableIdentityAttribute(attr, "Equals", value, sortAttr)` (max 50 results) |
| `context.search(...)` over links | `idn.getAccountByNativeIdentity(app, id)`, `idn.getFirstAccountNativeIdentity(app, identityName)`, `idn.attrSearchCountAccounts(...)` |
| `for (Link l : identity.getLinks())` | one targeted `idn` call for the source you need |
| `System.out.println(x)` / `log.error("ok")` | `log.debug(...)` / `log.info(...)` |
| HTTP/JDBC from a cloud rule | a workflow HTTP action, a connector, or a connector rule using the provided connection |
| uniqueness loop in an IdentityAttribute rule | AttributeGenerator rule on the target source's create profile |

## Files

| File | Use for |
|---|---|
| `scripts/review_rule.py` | the reviewer (stdlib); report with `--report` |
| `scripts/rule_catalog.json` | GENERATED: rule types with execution, inputs, outputs and doc page; IdnRuleUtil method signatures; deprecated types |
| `references/review-process.md` | how to submit, SLAs, deployment windows, versioning, promotion with sp-config, rejections |
| `../isc-rules/scripts/forbidden_tokens.json` | GENERATED: SailPoint's code-restriction list (shared with isc-rules) |
