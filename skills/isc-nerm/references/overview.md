# NERM: the product, its data model and how it connects to ISC

Hand-written summary, checked on 2026-11-15 against the SailPoint product help linked in each section (summarised in
our own words). SaaS products change: check the linked page when a detail matters.

## Two different things called "non-employee"

| | **Non-Employee Risk Management (NERM)** | **Non-Employee Lifecycle Management (NELM) in ISC** |
|---|---|---|
| What | Separate SaaS product (ex SecZetta), add-on to ISC | A feature of Identity Security Cloud itself |
| Where | `https://{tenant}.nonemployee.com` | Inside the ISC tenant (`https://{tenant}.identitynow.com`) |
| API | `https://{tenant}.nonemployee.com/api/...` (`/profiles`, `/workflow_sessions`, ...) | `https://{tenant}.api.identitynow.com/...` (`/non-employee-sources`, `/non-employee-records`, `/non-employee-requests`, `/non-employee-approvals`) |
| Model | Any number of profile types (people, organizations, assignments, assets) with custom attributes, relationships and risk | Non-employee *sources*, each with its own attribute schema and records; each source is an ISC source |
| Process | Configurable workflows (create, update, batch, automated, registration, login, password reset) with 25+ action types, external portal | Simple request/approval of records by account managers |
| Risk | Risk scoring per attribute (impact, probability, inherited) | None |

SailPoint's own ISC help describes NELM as the basic option and points to NERM for automated workflows, self-service
onboarding, delegated administration and external collaboration portals
([ISC help: non-employee management](https://documentation.sailpoint.com/saas/help/common/non-employee-mgmt.html)).
**If a question mentions `non-employee-sources` or `non-employee-records`, it is about NELM in ISC, not NERM** — use the
isc-api skill.

Naming: in late 2026 some SailPoint help pages call the ISC platform "SailPoint Human Fabric"; the NERM connector
pages use that name. It is the same platform the API calls Identity Security Cloud.

## Data model

([admin help: profile types](https://documentation.sailpoint.com/ne-admin/help/profile-types/manage-prof-types.html))

- **Profile** — one record of anything NERM governs: a person, a vendor, a project, a laptop. Has a `name`, a
  `status`, a `profile_type_id` and `attributes` keyed by attribute **uid**.
- **Profile type** — groups profiles; decides the attributes, forms, pages and workflows used for them. A new tenant
  has four **core** profile types: Non-Employees, Organizations, Jobs, Assignments. Core types and their default
  attributes cannot be deleted; custom types use only custom attributes.
- **Category** of a profile type (API `category`): `employee`, `non-employee`, `organization`, `assignment`, `other`
  (the UI also lists *Job*). Category matters for ISC sync: only person types (core Non-Employees, custom employee or
  non-employee categories) can be synced as identities.
- **Assignment** — the time-bound link of a person to a job or project; a person can have several assignments, each
  assignment points to one person through a profile search/select attribute.
- **Profile status**: `Active`, `Inactive`, `On Leave`, `Terminated`. The UI's Active tab shows Active + On Leave; the
  Inactive tab shows Inactive + Terminated; archived profiles have their own tab.
- **Attribute** types (API `type`): TextField, TextArea, DropDown, RadioButtons, CheckBoxes, Date, Tags, Attachment,
  ProfileSelect/ProfileSearch (link to another profile — this is how relationships are built), OwnerSelect/OwnerSearch,
  ContributorSelect/ContributorSearch (link to users). Date attributes have a per-attribute `date_format`.
- **Forms** (sets of attributes, three columns) are combined into **pages**; pages are used by workflow steps and as
  profile pages. Text on pages supports Liquid.
- **Users** (people who log in to NERM) are not profiles. `type` `NeprofileUser` = lifecycle (internal) user,
  `NeaccessUser` = collaboration-portal user. What a user can see and do comes from **roles** and from being an
  **owner** or **contributor** of a profile.

## Workflows

([workflow types](https://documentation.sailpoint.com/ne-admin/help/workflows/lc-workflow-types.html),
[actions](https://documentation.sailpoint.com/ne-admin/help/workflows/actions.html))

- **Lifecycle** workflows, one set per profile type:
  - **Create** — starts from the dashboard, creates a profile.
  - **Update** — starts from a profile page, changes that profile.
  - **Batch** — runs the same steps over many selected profiles (optionally one request per profile).
  - **Automated** — no button; runs **once a day** at a fixed time that depends on the tenant's AWS region and cannot be
    changed. Selects profiles with filters (ID, attribute, risk level, status, type — all must match); typically driven
    by date attributes (e.g. end date reached → status change).
- **Collaboration** workflows for the external portal: **Registration**, **Login**, **Password reset**.
- API endpoints: `POST /workflows/{create|update|batch|automated|registration|login|password_reset}_workflows`.
- **Actions** (steps) include approval, request form, review form, notification, fulfillment, status change, set
  attribute values, update, create, contributors, auto assign, un-assign, duplicate prevention, profile check, profile
  select, email verification, identity proofing (ID Dataweb, Microsoft Entra ID), invitation, username and password,
  security questions, run workflow, REST API, SOAP API, LDAP, close session. API: `POST /workflow_actions/<type>_actions`.
- Behaviour worth knowing:
  - **Status Change applies immediately** — put it after the approval if approval is required.
  - **REST API** steps time out after **60 seconds** and the session fails.
  - **Close Session** ends the workflow; later steps do not run.
- A running instance is a **workflow session** (`/workflow_sessions`): its `status` moves through values like
  `pending_approval`, `approved`, `rejected`, `completed`, `failed`.

## Risk scoring

([risk](https://documentation.sailpoint.com/ne-admin/help/risk/index.html))

- Disabled by default; enabled per profile type. Scale 0–10, default levels Low / Medium / High (`/risk_levels`).
- Only **option-based** attributes carry risk: drop-down, check boxes, radio buttons, profile search, profile select.
  Risk type per attribute: Impact, Probability, Impact and Probability, Inherited (only profile search/select: the
  linked profile's risk), None. **Mitigation** attributes lower an attribute's risk.
- **Overall score = average of (average impact, average probability)**, rounded to two decimals; an inherited profile
  with a higher score overrides it. Subcategories are shown but do not change the score.
- API: `GET /risk_scores` (objects of type `Profile` or `WorkflowSession`, with overall, impact and probability scores
  and level ids); advanced search can filter with a `RiskRule` on `OverallRisk`.

## Integration with ISC

([NERM connector](https://documentation.sailpoint.com/ne-admin/help/connector/profile_connector.html))

1. **Profiles → ISC identities** (the *SailPoint Non-Employee Risk Management* connector). Turn on sync for a person
   profile type (Admin > System > Identity Security Cloud Connection Settings, NON-EMPLOYEE or ASSIGNMENT tab), or
   create the source manually in ISC. Automatic setup creates one source for all synced profile types, the account
   schema and an identity profile.
   - Required core attributes: First Name, Last Name, Business Email. **Non-Employee Profile ID** is aggregated
     automatically and mapped to Employee Number; default correlation is Non-Employee Profile ID = Employee Number
     (changing it can create duplicate identities).
   - Status filter on the source: All, or Active (Active + On Leave). Archived profiles are never aggregated.
   - Schema attributes are strings; entitlement aggregation is not supported for profile sources; extended attributes
     do not sync. Assignments come in as additional accounts correlated through their profile search/select attribute.
   - Make only person profiles authoritative.
   - API side: `/isc/accounts` (schema-mapped profiles), `/profile_types/{id}/synced_attributes`.
2. **NERM users ↔ ISC** (the *Non-Employee Risk Management Users* connector). Manages NERM lifecycle users and their
   roles from ISC; roles are aggregated as entitlements. Requires *Identity Security Cloud Entitlements for Roles* ON
   (Admin > System > Authentication > ISC AUTHENTICATION). Users are matched by the `sailpoint_identity_id` attribute.
   No custom schemas; not meant to be authoritative.
3. **Authentication**: ISC can be the login for NERM, and ISC personal access tokens work for the NERM API (see
   `api-gotchas.md`).

## Audit and retention

- `POST /audit_events/query` searches audit events by `subject_type`, `type`, subject id and date (`created_at` with
  `gt`/`lt`/`eq`); page size max 100.
- Profile history is kept for the life of the tenant; workflow request history for 18 months.
