# SailPoint ISC Skills (unofficial)

A set of [Agent Skills](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview) that turn Claude into a SailPoint **Identity Security Cloud** (formerly IdentityNow) reference you can ask in plain language:

> *"Which endpoint lists access requests? What can I filter on, and how do I paginate?"*
> *"Which workflow trigger should I use when a user's department changes?"*
> *"Which email goes out when an access request is denied? How do I edit it and which variables can I use?"*
> *"Write a BeforeProvisioning rule that moves terminated users to the Disabled OU."*
> *"How do I page through all NERM profiles, and which scope does my integration need?"*

Generic by design: no tenant data, no credentials, no calls to any tenant. Everything comes from SailPoint's public documentation and OpenAPI specs.

## Skills

| Skill | Ask it about |
|---|---|
| `isc-api` | endpoints, `filters`/`sorters` fields and operators per endpoint, pagination, auth and scopes, PATCH, rate limits, per-service versioning (legacy → new path map) |
| `isc-workflows` | choosing triggers, filters, actions, operators, JSONPath and inline variables, loops, limits, workflow JSON (with real examples) |
| `isc-event-triggers` | trigger catalog and payloads, subscriptions (HTTP, EventBridge), JSONPath filters, REQUEST_RESPONSE (pre-approval, dynamic approver), troubleshooting |
| `isc-notifications` | which email is sent when, editing templates, Velocity, global and template variables, From/Reply-To, disabling, notifications API |
| `isc-transforms` | every transform operation with attributes and examples, Velocity tools, identity vs account transforms |
| `isc-rules` | cloud rules and connector rules: signatures, templates, IdnRuleUtil, forbidden code, review process, connector rule API, attaching to sources |
| `isc-search` | query syntax, searchable fields per index, `POST /search/v1`, `searchAfter` paging, audit events |
| `isc-sources` | source object and connector settings, account schema, aggregation (optimized, delta, delete threshold, schedules), correlation and manager correlation, uncorrelated accounts, create profile / provisioning policies, attribute sync, native change detection, health statuses, SaaS connector commands and customizers |
| `isc-nerm` | Non-Employee Risk Management (separate product on `{tenant}.nonemployee.com`): NERM vs ISC Non-Employee Lifecycle Management, profiles and profile types, workflows and actions, workflow sessions, risk scoring, ISC connectors, the NERM API (ISC tokens, `nerm:` scopes, wrapped bodies, `after_id` paging, advanced search) |

Each skill is a short `SKILL.md` (how to answer + the core rules) plus `references/` that Claude opens only when needed. The API skill ships a generated page for every service (~1,100 operations) listing scopes, user levels and the exact filterable/sortable fields.

## It checks, not just explains

Every skill comes with a script Claude runs before handing you something (Python 3, standard library only — you can run them yourself too):

| Script | What it catches |
|---|---|
| `isc-workflows/scripts/validate_workflow.py` | broken step graph (missing `nextStep`/`defaultStep`, dead ends, unreachable steps), bad trigger filters, `.$` keys without JSONPath, `{{ }}` errors, references to non-existent step names, cron minutes, secrets in plain text, legacy API URLs |
| `isc-transforms/scripts/validate_transform.py` | unknown types (case-sensitive), missing required attributes, `name` on nested transforms, `conditional` with operators other than `eq`, wrong `dateCompare` operators, missing `requiresPeriodicRefresh` |
| `isc-api/scripts/check_filter.py` | fields/operators an endpoint doesn't accept, uppercase operators, single quotes; prints the encoded query string; maps legacy paths |
| `isc-rules/scripts/lint_rule.py` | SailPoint's forbidden code list, deprecated/unsupported rule types, file naming, sensitive logging, hard-coded credentials |
| `isc-notifications/scripts/check_template.py` | unbalanced `#if/#end`, variables the template doesn't have, `$user` in v2 templates, HTML the sanitizer strips, subjects that disable the email |
| `isc-sources/scripts/check_source_config.py` | create-profile fields computed in the wrong order, invalid usage types and field types, duplicate fields, broken field transforms, unknown source features, delete threshold outside 0–100, plain-text secrets in connector attributes, correlation operators other than EQ, native change detection that can never fire, non-Quartz cron schedules |
| `isc-nerm/scripts/check_nerm.py` | NERM bodies sent unwrapped, ISC NELM payloads or URLs used against NERM, unknown paths/methods, invalid statuses and enums, names where ids are required, advanced-search operators that don't fit the attribute type, `after_id` mixed with `offset`, `limit` over 500, ISC-only `filters`/`count`, workflow sessions that won't start, and whether a token's `nerm:` scopes allow a call |
| `isc-search/scripts/lint_query.py` | API filter syntax in search queries, lowercase boolean operators, split nested conditions, `.exact` on unsupported fields |

The forbidden-code list, transform types and endpoint filters are generated from SailPoint's own sources, so they stay current with the weekly refresh. `tests/` runs every validator against SailPoint's published examples (they must pass) and against deliberately broken fixtures (they must fail).

## Measured, not claimed

On a 40-question set ([`evals/`](evals/)) graded blind by a separate agent, the same model scored **35/80 (44%) without the skills and 80/80 (100%) with them** (no web access in either run). Without them it invented filter fields, said `EQ` works, said ISC's rate limit is per token, read the wrong payload field in Access Request Submitted workflows, and missed the `no_send` switch for emails. Per-skill table: [`evals/results.md`](evals/results.md); side-by-side answers: [`evals/demo.md`](evals/demo.md).

Honest caveat: the questions were written from the same sources the skills use, so this shows the skills deliver what SailPoint documents, not that they cover everything. Real-world questions are the most useful contribution.

Added in 0.2.0: 10 questions on sources (`src-*`), same protocol: **9/20 (45%) without the skills, 20/20 (100%) with them**. Without them the model said a UI option disables optimized aggregation, said a delete-threshold breach fails the aggregation (it skips the delete phase with a warning), missed every real attribute-sync limit and used legacy `/beta` and `/v3` paths. Details: [`evals/results-sources.md`](evals/results-sources.md).

Added in 0.3.0: 10 questions on NERM (`nerm-*`): **3/20 (15%) without the skills, 20/20 (100%) with them**. Without them the model said ISC personal access tokens don't work with NERM, invented scopes such as `nerm:profiles:read`, paged 200,000 profiles with `offset`, missed that workflow sessions need `?run=true`, used a `starts_with` operator, described risk as a weighted sum and assumed email correlation. Details: [`evals/results-nerm.md`](evals/results-nerm.md).

## Install

**Claude Code**

```
/plugin marketplace add normix93/sailpoint-isc-skills
/plugin install sailpoint-isc-skills@sailpoint-isc-skills
```

**Claude apps (claude.ai / desktop)**: zip a skill folder (e.g. `skills/isc-workflows`) and upload it in *Settings > Capabilities > Skills*, or upload the plugin.

**Any agent that reads skills**: copy the folders under `skills/` into its skills directory (e.g. `.claude/skills/`).

Works well together with an MCP server over the live OpenAPI specs (such as the companion `sailpoint-isc-docs` plugin): when its `search_endpoints` / `get_endpoint` tools are available, `isc-api` uses them to double-check.

## Keeping it current

A GitHub Action (`.github/workflows/refresh-references.yml`) rebuilds every Monday the files whose first line says `GENERATED`, runs the tests and opens a pull request only if SailPoint changed something. No secrets needed. To run it by hand:

```bash
git clone --depth 1 https://github.com/sailpoint-oss/api-specs.git /tmp/api-specs
git clone --depth 1 --filter=blob:none --sparse https://github.com/sailpoint-oss/developer.sailpoint.com.git /tmp/dev-docs
(cd /tmp/dev-docs && git sparse-checkout set docs)
python3 tools/build_references.py --specs /tmp/api-specs --docs /tmp/dev-docs
```

The other references (workflow triggers/actions/operators, email template catalog, search fields) are hand-written summaries of the product documentation at documentation.sailpoint.com, dated in each file. PRs welcome when SailPoint changes something.

## Findings while building it

- SailPoint's provisioning-policy guide shows a `substring` transform with `start`/`end`, while the operation reference requires `begin` — the transform validator flags it (kept as a known issue in the tests).
- An early draft of these skills said trigger filters allow at most 5 conditions; running the workflow validator on SailPoint's own exported workflows (one uses 7) showed the limit applies to the basic editor only. Fixed.

- NERM's API guide examples call `/api/v1/non-employee-sources` (an ISC endpoint name), two advanced-search examples are invalid JSON (missing quote), one uses the operator `includes?` instead of `include?`, and the examples use `object_type: NeAttribute` where the OpenAPI spec defines `condition_object_type`. The guide says `offset` starts at 0, the spec says minimum 1; the rule enum says `Leave of absence`, profiles say `On Leave`; the v2025 pagination page is a copy of the ISC page. All kept as known issues in the tests and explained in `isc-nerm/references/api-gotchas.md`.

## Accuracy

The skills tell Claude to answer from the references, quote fields exactly, and point to the API call that confirms tenant-specific details (`GET /workflow-library/v1/triggers`, `GET /notification-template-variables/v1/{key}/{medium}`, `GET /triggers/v1`…). Still: verify before you change production.

## License and attribution

MIT (see `LICENSE`). Generated references and the example workflows contain material from SailPoint's [developer.sailpoint.com](https://github.com/sailpoint-oss/developer.sailpoint.com), [api-specs](https://github.com/sailpoint-oss/api-specs) and [colab-workflows](https://github.com/sailpoint-oss/colab-workflows) repositories, © SailPoint Technologies, MIT License (see `NOTICE`).

Not affiliated with, endorsed by, or supported by SailPoint Technologies. "SailPoint", "IdentityNow" and "Identity Security Cloud" are trademarks of their owner.
