# Example workflows

Real exports from https://github.com/sailpoint-oss/colab-workflows (© SailPoint, MIT), with IDs, client IDs and e-mail addresses replaced by placeholders.

| File | Trigger | Shows |
|---|---|---|
| `event-aggregation-failed-email.json` | `idn:account-aggregation-completed` + filter | Compare Strings, Send Email with templating `context`, inline `{{ }}` in subject |
| `event-access-decision-loop-manage-accounts.json` | `idn:access-request-post-approval` | Define Variable (`Mutation`) with transforms, parallel Loop with context, Get Access by search query, Manage Accounts |
| `external-emergency-termination.json` | External | Get Identity, Get Access, Manage Access (`REVOKE_ACCESS`), Manage Accounts |
| `scheduled-http-aggregation.json` | Scheduled (weekly) | HTTP Request to the ISC API with OAuth, Compare Numbers on `statusCode` |
| `recipe-ad-attribute-changed-powershell.json` | Account Updated (ID to fill from your tenant) + filter on `singleValueAttributeChanges` | written for this repo, not a SailPoint export: source check, uncorrelated check (`IsPresent`), employee check on an identity attribute, HTTP call to the service that runs PowerShell. If you license Privileged Task Automation, replace the HTTP step with the **Windows Server** action (runs a script on a VA cluster with the Privileged Access Gateway; script path, arguments, SHA-512 checksum) |
| `event-identity-created-form-roles.json` | `idn:identity-created` | Get List of Identities, Form, Loop |

They were exported in 2022–2024: URLs use legacy paths such as `/beta/...`. Use the current per-service paths (`/sources/v1/...`, see the `isc-api` skill's `versioning-map.md`) in new workflows, and check each action's current `versionNumber` with `GET /workflow-library/v1/actions`.
