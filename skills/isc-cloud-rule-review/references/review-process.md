# SailPoint rule review: process

Hand-written summary of SailPoint's pages
[Rules](https://developer.sailpoint.com/docs/extensibility/rules) and
[Cloud Rules](https://developer.sailpoint.com/docs/extensibility/rules/cloud-rules), checked on 2026-11-15. The full
pages (MIT) are bundled in `../../isc-rules/references/` (`rules-overview.md`, `cloud-rules-process.md`).

## What the review is

- Every rule deployed to a tenant is reviewed by SailPoint, because a bad rule can slow down other tenants in the
  same cloud. Reviews need an Expert Services contract (billable hours; typically 15–30 minutes per rule, more if
  complex or resubmitted).
- It is an **integrity check**: guidelines, code restrictions, intended use of the rule type. SailPoint does **not**
  check that the rule works or gives the right result.
- Rules are configuration: SailPoint supports the platform, not your rule logic. Use product features (transforms,
  workflows, campaign filters, role criteria) first; a rule is the last resort.

## Submitting

- Open a request on the SailPoint support portal (or email support). Attach:
  1. the rule file, named `Rule - {type} - {name}.xml` (e.g. `Rule - IdentityAttribute - Calculate Lifecycle.xml`);
  2. the validator output (this skill's `--report` file, plus SailPoint's community rule validator if you use it);
  3. the tenant name (`acme-sb.identitynow.com` for sandbox, `acme.identitynow.com` for production);
  4. approval for Expert Services to proceed.
- Submit one rule at a time, or only rules that must be deployed together.
- Keep your contact details current so reviewers can reach you.

## Timing

- SLA: 24 hours for weekday submissions, next business day for weekend submissions. About 65% are done in under
  4 business hours; average 3–6 hours after assignment.
- Reviewers work 9:00–17:00 Monday–Friday in their time zones, excluding holidays.
- Need a specific deployment window: tell SailPoint at least 48 hours ahead.
- Weekend go-live: get the rules deployed to the sandbox first and promote them yourself; rule deploys are not part
  of Weekend Go-Live Support.
- Expedited review exists for real emergencies only; abuse can lead to refused requests.
- Complex, poorly documented or hard-to-read rules, and rules rejected repeatedly for the same reason, take longer.

## Changing an existing rule

- Keep **one rule per use case** and update it under the same name; versioned copies are not supported.
- For full control of when new logic goes live: submit `<original name>-TEMP`, switch to it in the change window,
  validate, submit the update of the original, switch back, then ask to delete the TEMP rule. "Switching" means
  pointing the configuration at the other rule: e.g. the source field `beforeProvisioningRule` (PATCH
  `/sources/v1/{id}`), the identity profile mapping for IdentityAttribute rules, the Create Account field for
  AttributeGenerator rules.

## Promoting sandbox → production

- An approved rule (any type, cloud rules included) can be moved to production with the **sp-config** export/import
  API without a new review: the approved signature travels with it.

## Rejections

- Fixing the rule is the submitter's job; reviewers may give advice or examples.
- Open a new ticket for the resubmission (the original case owner may be away).
- Mistaken rejections happen: reply to the review team with the extra context; escalate if you still disagree.

## Connector rules are different

Connector rules run on the virtual appliance and are created with `POST /connector-rules/v1` (JSON with the script
escaped and a `signature`), then attached to the source. They must follow the same code guidelines; they cannot call
out except through the connection they are given. See `../../isc-rules/references/connector-rules-process.md`.
