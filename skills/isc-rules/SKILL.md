---
name: isc-rules
description: SailPoint Identity Security Cloud (ISC/IdentityNow) rules reference — cloud rules (IdentityAttribute, Correlation, ManagerCorrelation, BeforeProvisioning, AttributeGenerator, Transform, BuildMap) and connector rules (AD/Entra before/after operation, JDBC, SAP, Web Services). Use when someone asks which rule type fits a need, a rule's inputs/outputs, writing or reviewing BeanShell rule code, IdnRuleUtil methods, forbidden code, the cloud rule review process, connector rule APIs, or how to attach a rule to a source.
---

# SailPoint ISC rules

Rules are BeanShell (Java-like) scripts for logic the product can't do with configuration or transforms. Two families:

| | Cloud rules | Connector rules |
|---|---|---|
| Runs in | SailPoint multi-tenant cloud | the Virtual Appliance (CCG) |
| Data access | read-only via `idn` (`IdnRuleUtil`) | the source connection (JDBC connection, SAP destination, REST client…) |
| Deployment | **SailPoint review**: submit via support ticket (rule XML + RDK/validator output + tenant); ~24 h SLA; then promotable sandbox → prod with sp-config | self-service through `/connector-rules/v1` (built-in code checks) |
| Logs | visible only to SailPoint | `ccg.log` on the VA |

**Prefer configuration first**: transforms (`isc-transforms` skill), identity profile mappings, provisioning policies, workflows. SailPoint reviewers reject rules that duplicate product features, and supports the platform, not your rule code.

## How to answer

1. **Pick the rule type** from the tables below; justify why a transform/workflow isn't enough.
2. Open the page in `references/cloud/` or `references/connector/` for **inputs, output, template, example**. State the signature exactly as documented.
3. Write the code: null checks, `log.debug/info/warn/error` only, no forbidden calls (list below), no iteration over all identities/accounts, return the documented output type.
4. Explain deployment: cloud → XML file named `Rule - {type} - {name}.xml`, validate with the RDK, submit for review; connector → `POST /connector-rules/v1` (validate first with `/connector-rules/v1/validate`).
5. Explain **attachment** (where the rule is referenced): identity profile, account create profile, source fields — JSON Patch examples in `references/connector-rules-process.md`.

## Cloud rule types

| Type (`type=`) | Use it to | Inputs → output | Attached in |
|---|---|---|---|
| `IdentityAttribute` | compute an identity attribute ("complex data source") | `identity`, `oldValue`, `idn`, `log` → attribute value | identity profile mapping (Complex Data Source / via transform) |
| `AttributeGenerator` | generate an account attribute at creation (username, email, temp password, unique values) | `identity`, `application`, `field`, `idn`, `log` → value | account create profile (provisioning policy) field |
| `AttributeGeneratorFromTemplate` | same, driven by a template like `${firstname}.${lastname}${uniqueCounter}` with `cloudMaxUniqueChecks`, `cloudMaxSize` | as above | create profile field |
| `Correlation` | correlate an account to an identity with complex logic (runs before configured correlation) | `account` (ResourceObject), `application`, `idn`, `log` → `Map` with `identityAttributeName`, `identityAttributeValue` | source `accountCorrelationRule` |
| `ManagerCorrelation` | find the manager identity (multiple accounts, lookups, type changes) | `link`, `managerAttributeValue`, `idn`, `log` → `Map` with `identityAttributeName`, `identityAttributeValue` | source `managerCorrelationRule` |
| `BeforeProvisioning` | modify the provisioning plan before it goes out (disable + remove groups on terminate, move OU, add/remove attributes) — not for creating new attributes | `plan`, `application`, `integration`, `idn`, `log` → none (mutate `plan`) | source `beforeProvisioningRule` |
| `Transform` | custom logic called from a `rule` transform with parameters | transform attributes as variables → value | transform of type `rule` |
| `BuildMap` | reshape rows of a **Delimited File** source during aggregation | `cols`, `record`, `application`, `schema` → `Map` | source `connectorAttributes.buildMapRule` |

## Connector rule types

| Type | Source | Use it to |
|---|---|---|
| `ConnectorBeforeCreate` / `AfterCreate` / `BeforeModify` / `AfterModify` / `BeforeDelete` / `AfterDelete` | Active Directory, Entra ID (via IQService) | run PowerShell around account operations (home folders, mailbox, extra calls). Keep the rule thin: launch a PowerShell script that does the work |
| `JDBCBuildMap` | JDBC and JDBC-derived | reshape each `ResultSet` row; extra queries via `connection`; `state` map shared across rows |
| `JDBCProvision` | JDBC | perform provisioning with SQL from the `plan`; return a `ProvisioningResult` |
| `SAPBuildMap` | SAP, SAP HR | add attributes during aggregation via JCo/BAPI |
| `SapHrOperationProvisioning` | SAP HR | write custom SAP HR attributes during provisioning |
| `WebServiceBeforeOperationRule` | Web Services | change the request (headers, body, URL, paging) before an HTTP call; return the endpoint or a map with `updatedEndPoint`/`connectorStateMap` |
| `WebServiceAfterOperationRule` | Web Services | parse complex responses after a call; return a map with updated `data` (accounts/groups) and connector state |

## IdnRuleUtil (`idn`) — read-only helpers in cloud rules

Common methods (full list with signatures in `references/rule-utility.md`): `accountExistsByNativeIdentity`, `attrSearchCountAccounts`, `attrSearchGetIdentityName`, `getAccountAttribute`, `getFirstAccountNativeIdentity`, `getIdentityById`, `findIdentitiesBySearchableIdentityAttribute`, `countIdentitiesBySearchableIdentityAttribute`, `getManagedAttributeDetails`, `isUniqueLDAPValue`… Search-based account lookups need the attribute promoted with `/accounts/v1/search-attribute-config` first.

## Forbidden in any rule (blocked)

`context.` and object-store calls (`getObject*`, `search(`, `countObjects`, `update(`, transactions, `lock*`, `decache`…), `System.out/err`, `printStackTrace`, own loggers (`Logger.getLogger`, `Log4j`), threads (`Thread`, `Runnable`, `sleep`, `wait`, `notify`), `Runtime.`, `ProcessBuilder`, `exec(`, `System.exit`, sockets, file system and BeanShell shell commands (`cd(`, `cat(`, `rm(`, `source(`, `addClassPath`, `run(`…), `.toXml()`, `encrypt`/`decrypt`, `sendEmailNotification`, `runRule`/`runScript`, `SailpointFactory`, `XMLObjectFactory`, `public static`. Full list: `references/rules-overview.md`.

Plus the guidelines: no sensitive data in logs or code, proper try/catch/finally, null checks, no dead code, no sleeps, no iterating over large object lists, comments for non-obvious logic, UTF-8, `&amp;`/`&lt;`/`&gt;` converted.

## Templates

Cloud rule XML:
```xml
<?xml version='1.0' encoding='UTF-8'?>
<!DOCTYPE Rule PUBLIC "sailpoint.dtd" "sailpoint.dtd">
<Rule name="Calculate Lifecycle" type="IdentityAttribute">
  <Description>Lifecycle state from start/end dates.</Description>
  <Source><![CDATA[
    import sailpoint.object.Identity;
    if (identity == null) return oldValue;
    String start = identity.getStringAttribute("startDate");
    // …
    return "active";
  ]]></Source>
</Rule>
```

Connector rule (API object): `name`, `type`, `signature` (`input[]`, `output`), `sourceCode.script` (escaped string), `attributes`. Create with `POST /connector-rules/v1`; list/get/update/delete `/connector-rules/v1[/{id}]`; validate `POST /connector-rules/v1/validate`. Attach to a source with JSON Patch on the source (e.g. `/connectorAttributes/jdbcProvisionRule`, `/connectorAttributes/connectionParameters/{index}/beforeRule`, `/connectorAttributes/nativeRules` list for AD/Entra) — see `references/connector-rules-process.md`.

Local testing: SailPoint Rule Development Kit (Java 17 + Maven) https://github.com/sailpoint-oss/rule-development-kit — mocks the classes so logic can be unit-tested before review.

## Lint before delivering

```bash
python3 scripts/lint_rule.py "Rule - BeforeProvisioning - AD Move OU.xml"   # XML, connector-rule JSON or plain BeanShell
```
Flags SailPoint's forbidden code (`scripts/forbidden_tokens.json`, generated from the docs), unsupported/deprecated types, naming, CDATA, encoded characters, sensitive logging, hard-coded credentials, wrong return for the rule type. A clean lint is not a review pass: cloud rules still go to SailPoint.

## Reference map

| File | Contents |
|---|---|
| `references/rules-overview.md` | execution model, guidelines, full forbidden-code list, deprecated rules, sandbox→prod promotion |
| `references/cloud-rules-process.md` | review submission, naming, versioning (`-TEMP` pattern), expectations |
| `references/connector-rules-process.md` | connector rule API, object model, attach-to-source PATCH examples for every type |
| `references/cloud/*.md` | one page per cloud rule: inputs, output, template, examples |
| `references/connector/*.md` | one page per connector rule |
| `references/rule-utility.md` | IdnRuleUtil methods, searchable account attributes setup, examples |
| `references/your-first-rule.md` | end-to-end tutorial (username generator) |

API details: `isc-api` skill → `endpoints/connector-rules.md`, `endpoints/sources.md`, `endpoints/sp-config.md`. Not affiliated with SailPoint; docs: https://developer.sailpoint.com/docs/extensibility/rules
