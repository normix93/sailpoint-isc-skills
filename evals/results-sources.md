# Results

10 questions, 0–2 points each (max 20). Blind grading by a separate agent.

| Skill | Questions | Without skills | With skills |
|---|---|---|---|
| isc-sources | 10 | 9/20 | 20/20 |
| **Total** | 10 | **9/20 (45%)** | **20/20 (100%)** |

## Per question

| id | without | with | grader note (without) | grader note (with) |
|---|---|---|---|---|
| src-01 | 1 | 2 | Ordered first-match ok; missing account-name vs identity-name fallback. | Ordered first-match, Equals case-insensitive, name fallback all present. |
| src-02 | 0 | 2 | Claims a UI option disables optimization (must_not). | Optimization skip and API-only disableOptimization on v1 load-accounts correct. |
| src-03 | 1 | 2 | Percentage ok; says aggregation fails instead of delete phase skipped with warning; omits deletion-enabled. | Percentage, skip with warning, full-only with deletion enabled; all correct. |
| src-04 | 1 | 2 | Order fix correct; omits generator limitation, claims static reads identity attributes. | Order dependence, static refs earlier fields, generators cannot reference fields. |
| src-05 | 0 | 2 | Misses core limits (no Manager, 3/24h, direct mapping); several dubious claims. | All limits present: correlated only, direct mapping, no Manager, case-sensitive, 3/24h. |
| src-06 | 1 | 2 | Types and Quartz ok, but beta path not v1 and claims UTC. | v1 schedules endpoint, both types, Quartz with seconds and ? correct. |
| src-07 | 1 | 2 | Core points present but dubious claims (baseline, direct-only, optimized detects). | Aggregation-only detection, operation+attribute selection, trigger names all covered. |
| src-08 | 1 | 2 | PUT CREATE ok but v3 path; one-per-usageType yet no v2 multi-policy mention. | v1 GET/PUT CREATE, one per usageType, v2 experimental multi-policy correct. |
| src-09 | 1 | 2 | Filter ok; correlation file UI only, no endpoint, no manuallyCorrelated. | v1 filter, correlation file upload endpoint, manuallyCorrelated survives unoptimized. |
| src-10 | 2 | 2 | Advises against editing, unsupported config, enable via JDBC provisioning config. | Cites spec warning, don't modify features, enable via supported config. |
