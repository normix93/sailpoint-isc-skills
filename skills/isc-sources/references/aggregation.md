# Aggregation

Summarized from SailPoint's product documentation (Loading Account Data, checked 2026-11-14:
https://documentation.sailpoint.com/saas/help/accounts/loading_data.html) and the OpenAPI spec. Verify numbers
on that page before quoting them to a customer: SailPoint changes them.

## Kinds

| Kind | How it starts | Deletes accounts? | Notes |
|---|---|---|---|
| **Full** account aggregation | schedule, *Start Aggregation*, `POST /sources/v1/{id}/load-accounts` | yes, if account deletion is enabled and the threshold is not exceeded | reads every account |
| **Delta** aggregation | schedule/connector setting, only on connectors that support it (e.g. Active Directory, Entra ID, Okta, Workday) | no | does not see OU moves: run full aggregations too |
| **Single-account** | account page *Reload*, `POST /accounts/v1/{id}/reload` | no | refreshes one account |
| **Entitlement** (group) aggregation | schedule type `GROUP_AGGREGATION`, `POST /sources/v1/{sourceId}/load-entitlements` | — | loads groups/entitlements and their attributes; separate from account aggregation |
| **Flat file** (delimited) sources | file upload only (UI *Import* or the same endpoints with `multipart/form-data` and `file`) | as above | sort the file by account ID, otherwise only one entitlement per account is kept; keep files under ~500 MB |

Progress of a running aggregation: `GET /account-aggregations/v1/{id}/status` (id = the task id returned by
`load-accounts`). Aggregations can be cancelled from the UI.

## Optimized vs unoptimized

- **Optimized (default, and always for UI-started runs)**: accounts whose data did not change are skipped, and
  correlation and manager correlation are not re-evaluated for them.
- **Unoptimized**: every account is processed and correlation is recomputed.
  `POST /sources/v1/{id}/load-accounts` with multipart field `disableOptimization=true`; applies to that run only.
- Run one unoptimized aggregation after changing correlation, manager correlation, or searchable identity attributes
  used for correlation.

## Account deletion and the delete threshold

- *Enable Account Deletion* must be on, otherwise accounts missing from the source are never removed.
- Deletions are processed only by **full** aggregations.
- The threshold is a **percentage** of the source's accounts (API field `deleteThreshold`, 0–100). If an aggregation
  would delete more, the delete phase is skipped and a warning is raised ("Account deletion was skipped ... threshold
  exceeded"). Accounts stay in ISC until you raise the threshold for one run or fix the source.
- Small sources: the percentage is rounded to whole accounts; if it rounds below one account, only a 100% deletion is
  blocked.
- Typical practice: a low value (around 10%) so that an empty or truncated read (VA problem, wrong base DN, empty file)
  cannot wipe access.

## Schedules

- UI: daily (optionally repeating every N hours until midnight), weekly, monthly (days 1–28). Times are in the VA
  cluster's time zone and do not follow daylight saving time.
- API: `POST /sources/v1/{sourceId}/schedules` with `{"type": "ACCOUNT_AGGREGATION" | "GROUP_AGGREGATION",
  "cronExpression": "0 0 5,13,21 * * ?"}` — a **Quartz** cron: seconds first, `?` in day-of-month or day-of-week,
  optional 7th year field (SailPoint's own example is `0 0 12 1/1 * ? *`), days of week 1–7 = Sunday–Saturday.
  One schedule per type. Change it with `PATCH /sources/v1/{sourceId}/schedules/{scheduleType}` (JSON Patch; `type`
  is immutable, there is no PUT); remove it with `DELETE`.
- Quick Compliance sources: at most 3 runs a day, 8 hours apart (does not apply to Org Admins).

## Limits worth knowing

- `aggregateTimeout` connector setting: seconds, maximum 600.
- Default retry: 3 attempts, 5000 ms apart.
- Emoji and some special characters are not supported (UTF8MB3 storage).

## Typical questions

| Question | Answer |
|---|---|
| "Accounts deleted in the source are still in ISC" | account deletion off, delta/single aggregation only, or threshold exceeded (check the aggregation warning) |
| "Changed correlation, nothing happened" | optimized aggregation skipped unchanged accounts: run once with `disableOptimization=true` |
| "Moved users to another OU, ISC still shows the old DN" | delta aggregation does not handle OU moves: run a full aggregation |
| "Only one group per account from my CSV" | file not sorted by account ID |
| "How do I trigger aggregation from a workflow?" | HTTP Request action to `POST /sources/v1/{id}/load-accounts` (see `../isc-workflows`) |
