---
name: iiq-to-isc-migration
description: Plan a SailPoint IdentityIQ (IIQ) to Identity Security Cloud (ISC/IdentityNow) migration — reads IIQ XML exports (Rule, Application, Workflow, Bundle, Policy, CertificationDefinition, TaskDefinition, QuickLink, Custom, Form, IdentityTrigger...), maps each object and rule type to its ISC equivalent (transform, cloud rule, connector rule, workflow, identity profile, lifecycle state, access profile, role, SOD policy, campaign) as direct, adapt or none, flags IIQ-only APIs (context, QueryOptions, Provisioner, rule libraries, JDBC/HTTP), checks rules that become ISC rules against SailPoint's review rules, and writes a migration plan. Use when someone moves from IIQ to ISC, asks what an IIQ rule becomes in ISC, or estimates migration effort.
---

# IdentityIQ → Identity Security Cloud

ISC does not import IIQ objects: everything is rebuilt, ideally simpler. The job is to know, for each IIQ object,
what it becomes in ISC, what cannot move as it is, and in which order to build. SailPoint runs an upgrade program
(assessment, then migration with AI-assisted tooling since June 2026): see `references/mapping.md` for what SailPoint
says moves well and what does not.

## Do this

1. Get an IIQ export: the objects as XML (console `export`, Debug pages, or the deployment accelerator's config
   folder). One `<sailpoint>` file, single-object files or a folder all work. No production data is needed.
2. Run the analyzer:
   ```bash
   python3 scripts/analyze_iiq.py iiq-export/ --plan migration-plan.md
   ```
   It prints each object with its level and ISC equivalent, the IIQ APIs found in rules with their replacement, and,
   for rules that become ISC cloud/connector rules, what SailPoint's rule review would reject (via
   `../isc-cloud-rule-review/scripts/review_rule.py`). `--json` for tooling.
3. Read the plan with the user; decide per **adapt**/**none** item: configuration, transform, rule, workflow, or drop.
4. Build in the plan's order. Rules you keep: rewrite, then `review_rule.py` before submitting to SailPoint.

## Rules of thumb that change answers

1. **Configuration before code.** IIQ correlation rules → ISC correlation config; IdentityAttribute/Creation/
   Customization rules → transforms; CertificationExclusion → campaign filters; IdentitySelector → membership criteria.
   Every ISC cloud rule costs a SailPoint review (Expert Services hours, about a business day).
2. **No `context` in ISC.** Reads go through `idn` helpers (searchable attributes, Equals/StartsWith, max 50 identities);
   writes are impossible from rules. Rule libraries do not exist: inline code.
3. **Rule types that do not exist in ISC**: AfterProvisioning (→ workflow on Provisioning Completed), IdentityCreation,
   ResourceObjectCustomization, ManagedAttributeCustomization, PreIterate/PostIterate/MergeMaps, FieldValue (→ Create
   Account field + transform or AttributeGenerator rule), AllowedValues/Validation, Refresh, Policy, Approver
   (→ approval config / dynamic approval trigger), and all task/email/listener rules.
4. **Gone entirely**: QuickLinks, custom objects, plugins, custom task executors, logical applications, advanced/
   activity policies, audit history. Plan replacements (Request Center, forms + workflows, lookup transforms,
   external jobs on the API).
5. **Different engine**: identity refresh and provisioning are event driven; no task schedules to tune. Re-test any
   logic that depended on IIQ task order.
6. **Migrate in phases**: sources first, compare identities and accounts with IIQ, then move access, requests,
   policies and certifications; switch IIQ off per application.

## Files

| File | Use for |
|---|---|
| `references/mapping.md` | curated mapping tables (rules, IIQ APIs, objects), SailPoint's framing, build order |
| `scripts/analyze_iiq.py` | the analyzer and plan generator (stdlib) |
| `scripts/iiq_mapping.json` | the mapping data the analyzer uses (edit it to match your project's decisions) |
| `../isc-cloud-rule-review/` | review rules you keep before submitting them to SailPoint |
| `../isc-transforms/`, `../isc-sources/`, `../isc-workflows/`, `../isc-rules/` | how to build each ISC replacement |
