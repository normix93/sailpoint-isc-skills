# Results

10 questions, 0–2 points each (max 20). Blind grading by a separate agent.

| Skill | Questions | Without skills | With skills |
|---|---|---|---|
| iiq-to-isc-migration | 5 | 7/10 | 9/10 |
| isc-cloud-rule-review | 5 | 5/10 | 10/10 |
| **Total** | 10 | **12/20 (60%)** | **19/20 (95%)** |

## Per question

| id | without | with | grader note (without) | grader note (with) |
|---|---|---|---|---|
| mig-01 | 1 | 1 | No import, re-implementation, assessment; misses phased side-by-side approach and cleanup; claims ISC has no Workflow objects. | Correct no-import, phased side-by-side, upgrade assessment and AI tool; misses cleaning up unused objects first. |
| mig-02 | 1 | 2 | Correct workflow/event trigger approach; omits that HTTP calls from cloud rules are not allowed. | No AfterProvisioning type, Provisioning Completed workflow with HTTP/ServiceNow, notes HTTP not allowed in cloud rules. |
| mig-03 | 1 | 2 | Correlation and creation fine but vague on rule return; claims ResourceObjectCustomization connector rule exists in ISC, hesitant. | All three mapped correctly: correlation config then rule with return map, profile mappings/transforms, transforms/BuildMap/customizer. |
| mig-04 | 2 | 2 | All three absent; Request Center, Forms+workflows, lookup/external store, external apps with UI Dev Kit. | All facts present: none exist, Request Center, Forms+workflow, lookup/external store, UI Development Kit apps. |
| mig-05 | 2 | 2 | Membership criteria, campaign filters, roles with access profiles, IT roles to access profiles; implicitly no rules. | States both deprecated; membership criteria, campaign filters, IT roles to access profiles. |
| rev-01 | 1 | 2 | Correct naming; misses validator output, ES approval, integrity-check nature; wrong 'few business days' SLA. | Portal request, rule file, validator output, tenant, ES approval, correct naming, integrity check, 24h SLA. |
| rev-02 | 2 | 2 | Context rejected, correct idn helpers, getReferenceIdentityAttribute transform; hedged identity.getManager() suggestion slightly dubious. | Context/getObjectByName restricted; correct idn methods; suggests transform instead. |
| rev-03 | 1 | 2 | Covers System.out, own logger, sensitive data, toXml; misses log.error reserved for real errors. | Covers System.out, own logger, sensitive data, toXml, log.error only for real errors. |
| rev-04 | 0 | 2 | Recommends 'v2' new-name rule contrary to versioning guidelines; no -TEMP procedure, no 48h notice. | Full -TEMP procedure, no versioned copies, 48h advance notice. |
| rev-05 | 1 | 2 | Contains unsupported and searchable noted but StartsWith hedged; getLinks issue; invents getLinkAttribute helper; no AttributeGenerator uniqueness note. | Equals/StartsWith only, searchable, getLinks cache bloat with targeted lookups, bounded uniqueness loop documented pattern. |
