# Changelog

## 0.4.0 — 2026-11-15

- New skill `isc-cloud-rule-review`: pre-submission review of ISC rules. `scripts/review_rule.py` runs 42 checks,
  each tied to a section of SailPoint's rule guidelines, separates ERROR (rejected/blocked) from WARNING, and writes
  a Markdown report to attach to the review ticket. Rule types, inputs/outputs and IdnRuleUtil signatures are
  generated from developer.sailpoint.com (`scripts/rule_catalog.json`); the forbidden-code list is shared with
  `isc-rules`. Tests: clean good rules, bad rules with the exact expected checks, and every SailPoint example rule
  (doc issues kept as known issues).
- New skill `iiq-to-isc-migration`: curated IIQ → ISC mapping (rule types, IIQ APIs, objects) and
  `scripts/analyze_iiq.py`, which reads IIQ XML exports, classifies each object, flags IIQ-only APIs, sends future ISC
  rules to the reviewer and writes a migration plan. Tests on a fictional IIQ export.
- 10 new evaluation questions (`rev-*`, `mig-*`).

## 0.3.0 — 2026-11-15

- New skill `isc-nerm` for SailPoint Non-Employee Risk Management: NERM vs ISC Non-Employee Lifecycle Management,
  data model, workflows and actions, risk scoring, ISC connectors, and the NERM API (authentication with ISC tokens,
  `nerm:` scopes, wrapped bodies, paging with `after_id`, advanced search, workflow sessions, audit query).
- Generated for it from SailPoint's NERM OpenAPI specs (v1 and v2025): endpoint index, endpoint details with body
  wrappers, schemas, and the enums/scope matrix used by the checker; SailPoint's NERM API guide pages.
- New checker `isc-nerm/scripts/check_nerm.py` (request bodies, URLs and query parameters, scopes), tested on good and
  broken fixtures and on the guide's examples (doc defects kept as known issues).
- 10 new evaluation questions for NERM.

## 0.2.0 — 2026-11-14

- New skill `isc-sources`: source anatomy (UI ↔ API), onboarding order, aggregation (optimized vs unoptimized,
  delta, delete threshold, schedules), correlation and manager correlation, uncorrelated accounts, create profile /
  provisioning policies with generators, attribute sync, native change detection, source health statuses.
- Generated for it from the OpenAPI spec: source configuration schemas with complete enums
  (`references/source-api-schemas.md`), an endpoint index for sources/connectors/aggregations, and the enums used
  by the new checker; SailPoint's SaaS connectivity docs (connector spec, commands, customizers).
- New checker `isc-sources/scripts/check_source_config.py` (provisioning policies, source objects, correlation,
  native change detection and schedule JSON), with regression tests on SailPoint's documented policies.
- 10 new evaluation questions for sources.

## 0.1.0 — 2026-11

First public release.

- Seven skills: `isc-api`, `isc-workflows`, `isc-event-triggers`, `isc-notifications`, `isc-transforms`, `isc-rules`, `isc-search`.
- Generated references from SailPoint's public repos: one page per API service (~1,100 operations with scopes, filters, sorters), transform operations, rules, event triggers, audit events.
- Hand-written references checked against the full product-documentation pages (workflow triggers with input fields, actions, operators, email templates, search fields).
- Executable checks: `validate_workflow.py`, `validate_transform.py`, `check_filter.py`, `lint_rule.py`, `check_template.py`, `lint_query.py`, with regression tests.
- Evaluation set (40 questions with rubrics) and results with/without the skills.
- GitHub Actions: CI on every push, weekly refresh of the generated references (opens a PR only when SailPoint changed something).
