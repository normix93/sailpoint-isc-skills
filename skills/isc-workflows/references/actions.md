# Workflow actions

Compiled from https://documentation.sailpoint.com/saas/help/workflows/workflow-actions.html (full page re-checked 14 November 2026). Action IDs (`actionId` in JSON) are tenant-visible through `GET /workflow-library/v1/actions` (returns `id`, `name`, `formFields`, `outputSchema`, `exampleOutput`). Confirmed in the public spec: `sp:send-email`, `sp:create-campaign`. For any other action, export a workflow that uses it or call the library endpoint instead of guessing the ID.

Reference outputs in later steps as `$.<stepTechnicalName>.<field>` (e.g. `$.getIdentity.attributes.department`).

## Identities, accounts, access

| Action | Purpose | Key inputs | Output | Limits |
|---|---|---|---|---|
| Get Identity | one identity with default + custom attributes | identity (picker or JSONPath to the ID) | `id`, `name`, `attributes`, `identityStatus`, `managerRef`, `isManager`… | 1 min |
| Get List of Identities | many identities | Search Query, Saved Search, Tag, Managers, or Direct Reports | `identities[]` | 250 identities, 1 min |
| Get Identity History | audit history of access changes | identity, optional From date, Event Type (`AccessItemAssociated`, `AccessItemRemoved`, `AttributesChanged`, `AccessRequested`, `IdentityCertified`, `AccountStatusChanged`) | events with `accessItem`, `eventType`, `dateTime`, `identityId` | 1 min |
| Get Accounts | source accounts | By Identity, or By Account Data (Equals / In List on technical ID, identity ID, name, native ID, source ID, uncorrelated) | `accounts[]` with `id`, `name`, `sourceId`, `identityId`, `disabled`, `locked`, `uncorrelated`, `hasEntitlements` | 250, 1 min |
| Manage Accounts | Enable, Disable, Unlock, Delete (Delete = flat-file sources only) | accounts, e.g. `$.getAccounts.accounts[*].id` | `successfulAccounts`, `failedAccounts`, `accountsErrorDetails` | 1 h |
| Get Access | access items of an identity or matching a search query | By Identity / By Search Query (e.g. `id:{{$.form.formData.accessProfile}}`, or `[0].id` when the form field allows several); types: access profiles, roles, entitlements | `accessItems[]` (`id`, `name`, `type`) | 250, 1 min |
| Manage Access | add or remove access for identities (replaces Create Request for Access / Request Access Removal) | request type, identities, access list `[{"id","name","type"}]` (Get Access output fits as is), comments, start date (begins 00:00 UTC), duration (error if beyond the item's end date / max duration) | `successfulAccessRequests`, `failedAccessRequests` (a failed request does **not** fail the workflow) | 30 min; revoke = one entitlement per request. **Doesn't wait** for approvals or provisioning: to act after the decision use a second workflow on Access Request Decision; to wait for the source, add a Wait step |

## Access requests and approvals

| Action | Purpose | Notes |
|---|---|---|
| Approval Policy | approval step for **Access Request Submitted** workflows (that trigger is mandatory; runs only if the item is requested and the workflow enabled) | Single, Multi-Step or Quorum; up to 5 reviewers (Manager, Governance Group, Identity, …), serial/parallel, quorum %, priority, reminders (≤ 90 days, cron hours only), timeout ≤ 90 days with action Approve or Expire. Output: `approvalId`, `status`, `approvers`, `approvedBy`/`rejectedBy`. |
| Generic Approval Policy | approval for anything (no access item needed) | name ≤ 50 chars, description/comments ≤ 150; requester/requested-for; same approval types; Force Reauthentication needs SSO. Output also has `approvalCriteria`, `comments`, `completedDate`. |
| Approve Access Request / Deny Access Request | decide a request by ID with comment | 90 s; only when the business process explicitly asks for automatic decisions |
| Get Pending Access Requests | up to 250 pending requests for a reviewer, optional standard filters | 1 min |
| Get Access Request Recommendations | up to 250 recommendations for an identity | needs Recommendations AI |
| Create Request for Access / Request Access Removal | legacy, replaced by Manage Access | 90 s |

## Certifications

| Action | Notes |
|---|---|
| Create Certification Campaign | reviewer type Manager, Source Owner (needs source IDs), Individual, Governance Group; duration, AI recommendations, notifications, undecided-item handling; must be activated unless "Start Campaign when Created". Output: campaign `id`, `status`, `filter`. Timeout 36 h. |
| Activate Certification Campaign | by campaign ID, 2 h |
| Get Certification Campaign | by ID, 1 min |

## Communication

**Send Email** (`sp:send-email`)
- To / CC / BCC: up to 10 addresses each. In JSON a recipient can come from JSONPath (`"recipientId.$": "$.trigger.identity.id"` addresses an identity).
- From: must be a verified address; blank = Branding "From" address. Reply-To: blank = Branding address.
- Subject/Body: HTML editor; `<` and `>` only work surrounded by spaces (`4 < 5`).
- **Templating Context**: map of variables → `{"approver.$": "$.getIdentity.attributes.displayName", "items.$": "$.getAccess.accessItems"}`; use `${approver}`, `#foreach($i in $items)$i.name#end` in body/subject (Velocity).
- Timeout 1 min.

**Send Slack Message** — recipient = ISC username, message text; falls back to email if the user isn't in Slack; needs the Slack integration.

**Interactive Message / Interactive Form** — for Interactive Trigger flows: message (≤ 400 KB) or form shown to the user (30 days to complete).

## Forms

**Form** — assigns a form with a deadline and pauses until submitted. Inputs mapped from workflow variables become required. Output includes `Submitted` (check with Compare Boolean) and the answers. Deadline ≤ 30 days, reminders ≤ 29 days; an expired deadline raises a cancellation error — handle it with error handling or the workflow fails.

## Integration

**HTTP Request**
- Methods: GET, POST, PUT, PATCH, DELETE. Auth: none, Basic, Custom Authorization (header), OAuth 2.0 client credentials. Content types: JSON, JSON Patch, SCIM+JSON, Form, XML, Text, CSV.
- URL parameters, headers, **sensitive headers** (masked in execution history — put secrets there).
- 90 s timeout; response must be JSON when there is a body; retries respecting `Retry-After`, `RateLimit-Reset`, `X-RateLimit-Reset`, `X-Rate-Limit-Reset`; QUIC not supported.
- With GET + JSON (and POST whose output feeds a loop) executions keep only the output data later steps use; tests keep everything.
- OAuth 2.0 can take an optional scopes parameter. Credentials can come from Parameter Storage.
- Output read as `$.hTTPRequest.body…` (check the exact technical name in execution history).
- Calling the ISC API itself: use OAuth 2.0 client credentials against `https://{tenant}.api.identitynow.com/oauth/token` with a dedicated API client.

**Manage ServiceNow Ticket** — create / update status / get status; Basic or OAuth; 300 s.

**Manage Agent** — activate/deactivate an enterprise agent.

**Privileged Task Automation** — Active Directory (users, groups, OUs), Entra ID (users, groups), Windows Server (firewall rules, services, PowerShell scripts with SHA-512 checksum) commands through a VA cluster with the Privileged Access Gateway component; connection via Parameter Storage or inline.

## Flow control

**Wait** — *Wait For* a Go duration (`90m`, `1h30m`, `1.5h`; 60 s–30 days; can be a variable) or *Wait Until* a date ≤ 180 days ahead (ISO 8601 variable allowed). Step timeout 182 days.

Operators (compare, loops, variables, end steps) are in `operators.md`.
