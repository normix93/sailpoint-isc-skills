# Results

10 questions, 0–2 points each (max 20). Blind grading by a separate agent.

| Skill | Questions | Without skills | With skills |
|---|---|---|---|
| isc-nerm | 10 | 3/20 | 20/20 |
| **Total** | 10 | **3/20 (15%)** | **20/20 (100%)** |

## Per question

| id | without | with | grader note (without) | grader note (with) |
|---|---|---|---|---|
| nerm-01 | 1 | 2 | Correct host and wrapped plural body, but never states required fields; mentions NERM API token; workflow body shown unwrapped. | Correct host, singular/plural endpoints, wrapped body, required profile_type_id/status, attributes by uid. |
| nerm-02 | 0 | 2 | Claims ISC PAT will not work and only NERM tokens work: must_not. | PAT exchanged at ISC /oauth/token, JWT to NERM; legacy keys deprecated, no scopes, unavailable after June 2025. |
| nerm-03 | 0 | 2 | Invents scopes (profiles:read, workflow_sessions:create); misses nerm:api:workflow-operator and generic 403 detail. | nerm:api:workflow-operator, generic 403 not naming scope, general:manage too broad, scopes only on ISC tokens. |
| nerm-04 | 0 | 2 | Recommends offset paging; misses after_id keyset rules and constraints, the core fact. | after_id keyset, id ascending, no offset, filter limits, limit 500 default 100, metadata, updated_after. |
| nerm-05 | 0 | 2 | Misses the run=true parameter entirely; blames approvals/forms instead. | run=true default false, PATCH ?run=true, wrapped body with three required fields, profile_id/profile_ids. |
| nerm-06 | 0 | 2 | Uses operator starts_with: must_not. | advanced_search/run wrapped, status != Terminated, attribute rule by id/type, start_with? operator. |
| nerm-07 | 2 | 2 | Separate ex-SecZetta product with workflows, portal, risk; NELM built-in with /non-employee-records; NERM connector. | All facts present: separate add-on host and API, NELM endpoints on api.identitynow.com, connector to identities. |
| nerm-08 | 0 | 2 | Describes weighted sum with thresholds; wrong formula, misses average impact/probability and default-off detail. | Option-based attributes only, average of impact and probability averages, inherited override, off by default, mitigation. |
| nerm-09 | 0 | 2 | Says identity correlation typically on email: must_not; vague on mapping. | Profile ID to Employee Number correlation, person types only, Active/All filter, archived excluded, core attributes only. |
| nerm-10 | 0 | 2 | Order fix right, but states ~30 s timeout (wrong) and misses daily fixed schedule. | Status Change immediate, move after approval; 60 s REST timeout fails session; automated daily fixed run. |
