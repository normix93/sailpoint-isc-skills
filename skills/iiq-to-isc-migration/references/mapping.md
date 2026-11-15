# IdentityIQ → Identity Security Cloud: what maps to what

Hand-written and checked on 2026-11-15. ISC facts come from the other skills in this repo (generated from SailPoint's
MIT docs and specs) and from documentation.sailpoint.com; IIQ rule types from the IdentityIQ help
([Rules tab](https://documentation.sailpoint.com/identityiq/help/application_configuration/configure/using_edit_application_page/rules_tab.html)).
Levels: **direct** = same concept, small changes; **adapt** = an ISC equivalent exists, rebuild the logic;
**none** = no equivalent, redesign. The same table drives `scripts/iiq_mapping.json`.

## How SailPoint frames it (paraphrased)

- SailPoint sells this as an *upgrade program*: a free Upgrade Assessment, then a migration with SailPoint or
  partners. In June 2026 it announced **SailPoint Agentic Acceleration**, with an AI tool (*Virtual Architect*) that
  converts IIQ configuration, workflows and policies into an ISC starting point, at no extra cost through its forward
  deployed engineers ([news, 17 Jun 2026](https://securitybrief.co.uk/story/sailpoint-launches-ai-tool-to-speed-cloud-migrations)).
- A SailPoint answer on the Developer Community (May 2026) groups IIQ content in three buckets: identity and role
  models, SOD policies, access requests, certifications and email templates move well; application-to-source mapping,
  workflows, connector rules and LCM need tool-assisted rework; heavy Java customization, plugins, legacy audit
  history and old risk models do not move
  ([thread](https://developer.sailpoint.com/discuss/t/guidance-on-migrating-from-identityiq-iiq-to-identity-security-cloud-isc/144977)).
- ISC does **not** import IIQ XML: objects are rebuilt (UI, API, sp-config JSON for supported object types).
  Practitioners agree it is a re-architecture, best done in phases with IIQ and ISC running side by side.

## Rules

| IIQ rule type | ISC equivalent | Level | Why |
|---|---|---|---|
| BuildMap (Delimited File) | BuildMap connector rule | direct | same purpose, runs on the VA; no `context` |
| JDBC BuildMap / JDBCProvision | JDBCBuildMap / JDBCProvision connector rules | direct | use only the connection the rule receives |
| JDBCOperationProvisioning | JDBCProvision (one rule, branch per operation) | adapt | ISC documents one provisioning rule |
| SAP BuildMap, SapHrOperationProvisioning | same connector rules | direct | |
| Web Services Before/After Operation | same connector rules (or SaaS connector customizer) | direct | |
| IQService before/after (Connector{Before,After}{Create,Modify,Delete}) | same connector rules | direct | |
| PreIterate, PostIterate, MergeMaps | none — prepare the file before upload; Delimited File merge settings | none | not ISC rule types |
| Correlation | source **correlation config** (attribute pairs, Equals, first match wins); only if impossible a Correlation cloud rule | adapt | most IIQ correlation rules are attribute matches; the ISC rule returns `identityAttributeName`/`identityAttributeValue` |
| ManagerCorrelation | `managerCorrelationMapping`; else ManagerCorrelation cloud rule | adapt | |
| IdentityCreation (Creation) | identity profile mappings with transforms | adapt | no creation rule; attributes are recomputed on every refresh |
| IdentityAttribute | **transform** (preferred) or IdentityAttribute cloud rule | adapt | transforms need no SailPoint review |
| IdentityAttributeTarget | attribute sync (identity attribute mapped in Create Account) or workflow | adapt | |
| ResourceObjectCustomization (Customization) | transforms where the value is used; BuildMap for file/JDBC; connector customizer for SaaS | adapt | no customization rule |
| ManagedAttributeCustomization | entitlement metadata via API, access profile settings | none | |
| BeforeProvisioning | BeforeProvisioning cloud rule | direct | rewrite `context`/`Provisioner` use |
| AfterProvisioning | workflow on **Provisioning Completed** | adapt | no AfterProvisioning rule |
| Integration | BeforeProvisioning | adapt | deprecated in ISC |
| FieldValue (provisioning policy) | Create Account field with transform; **AttributeGenerator** cloud rule for uniqueness | adapt | |
| AllowedValues, Validation, FormProvisioning | ISC Forms (static options, built-in validation, conditions) | none | no scripts in ISC forms |
| Workflow (rule libraries, step scripts) | ISC Workflows (triggers, actions, operators) | adapt | BeanShell does not run in ISC workflows |
| CertificationExclusion | campaign filters | adapt | deprecated in ISC |
| IdentitySelector | role membership criteria | adapt | deprecated in ISC |
| Approver | approval settings, governance groups, Access Request Dynamic Approval trigger | adapt | |
| Certifier | campaign reviewer type | adapt | |
| Refresh, Policy, Violation, Owner, TaskCompletion, EmailRecipient, RequestObjectSelector, ListenerRule | none | none | redesign with configuration, workflows or event triggers |

### IIQ code that has no place in ISC rules

| IIQ code | ISC replacement |
|---|---|
| `context.getObjectByName(Identity.class, x)` | `idn.getIdentityById(id)`, `idn.findIdentitiesBySearchableIdentityAttribute(attr, "Equals", v, sort)` (max 50) |
| `context.getObject...(Link.class, ...)`, `context.search(Link.class, qo)` | `idn.getAccountByNativeIdentity(app, id)`, `idn.getAccountAttribute(...)`, `idn.attrSearchGetIdentityName(...)` |
| `context.countObjects(...)` | `idn.countIdentitiesBySearchableIdentityAttribute(...)`, `idn.attrSearchCountAccounts(...)` |
| `QueryOptions`, `Filter.eq/like/...` | searchable-attribute helpers (Equals/StartsWith only); no arbitrary queries |
| `context.saveObject/commitTransaction` | not possible: change the plan or return values; persistent changes via workflows/API |
| `context.runRule`, `<ReferencedRules>` (rule libraries) | inline the code; each ISC rule is reviewed on its own |
| `context.sendEmailNotification` | workflow Send Email, notification templates |
| `Provisioner`, `Identitizer`, `Aggregator`, `IdentityService` | the platform does it: identity processing, aggregation API, workflows |
| JDBC/HTTP/file access in a rule | a connector (connector rules get a connection), workflow HTTP Request, event trigger |
| `System.out`, threads, `sleep` | `log.debug/info`; not allowed |

Application names in `idn` calls are the ISC source name plus ` [source]` (or `application.getName()`).

## Other objects

| IIQ object | ISC equivalent | Level | Notes |
|---|---|---|---|
| Application | Source + connector, account schema, correlation config, Create Account, schedules | adapt | VA connectors for on-prem systems; check the connector catalog; **Logical** applications have no equivalent (model with roles/access profiles) |
| ObjectConfig Identity / identity attributes | identity attributes + identity profile mappings (transforms) | adapt | one identity profile per authoritative source |
| IdentityTrigger (lifecycle events) | lifecycle states; workflows on Identity Created / Identity Attributes Changed | adapt | |
| Bundle — business role | role with membership criteria | adapt | IIQ required/permitted roles and inheritance must be flattened |
| Bundle — IT role / entitlement bundle | access profile (one source) or role | adapt | |
| Policy — SOD / role SOD / entitlement SOD | SOD policy (conflicting access) | adapt | defined on entitlements, access profiles, roles |
| Policy — advanced, activity, account, risk | none | none | search + campaign, workflow |
| CertificationDefinition | campaign (manager, source owner, search, role composition, machine account) + filters | adapt | |
| Workflow (LCM, lifecycle) | access request configuration + ISC workflows | adapt | rebuild from the business steps |
| Form | ISC Forms used from workflows | adapt | no scripted fields |
| EmailTemplate | notification templates (Velocity, different variables) or workflow email | adapt | |
| TaskDefinition — aggregation | source aggregation schedule | direct | |
| TaskDefinition — identity refresh | not needed (automatic, event driven) | direct | |
| TaskDefinition — Run Rule / custom executors | scheduled workflow or external job on the ISC API | none | |
| QuickLink | Request Center; Forms + workflow (external trigger) | none | |
| Custom objects | transform lookup tables, attributes, external store | none | |
| Plugins | external app on the ISC APIs (UI Development Kit) | none | |
| Capabilities, SPRights, Scopes | user levels, governance groups | adapt | different authorization model |
| Audit config and history | ISC audit events/search | none | history does not move |

## Order that avoids rework

1. Clean up IIQ: retire unused applications, rules, roles and custom objects.
2. Sources (connectors, schemas, read-time connector rules), correlation config, first aggregations.
3. Identity profiles and attributes (transforms), then lifecycle states.
4. Provisioning: Create Account policies, AttributeGenerator/BeforeProvisioning rules (submit for review early).
5. Access model: access profiles, roles, membership criteria.
6. Access requests, approvals, workflows, forms, notifications.
7. SOD policies, then certification campaigns.
8. Coexistence: move applications in phases, compare results, then switch off IIQ per application.
