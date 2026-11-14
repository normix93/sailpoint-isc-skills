# Changelog

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
