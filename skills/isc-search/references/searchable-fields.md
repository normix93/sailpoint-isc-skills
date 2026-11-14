# Searchable fields

Summarised from https://documentation.sailpoint.com/saas/help/search/searchable-fields.html and the query-syntax page (checked November 2026). Field names are case-sensitive. Dates are ISO 8601; escape `:` in times with `\`. Identity fields are searchable only on correlated accounts; a manager must be correlated to a valid identity.

Levels: **first** `field:value` · **second** `object.field:value` · **nested** `@object(field:value)`.

## identities

- First: `name`, `displayName`, `firstName`, `lastName`, `id`, `email`, `created`, `modified`, `phone`, `status`, `synced`, `isManager` (bool), `employeeNumber`, `processingState` (`ERROR` on aggregation error), `appCount`, `accountCount`, `accessCount`, `entitlementCount`, `roleCount`, `accessProfileCount` (int), `tags`.
- Second:
  - `manager.name`, `manager.displayName`, `manager.id`
  - `source.id`, `source.name` (authoritative source)
  - `identityProfile.name`, `identityProfile.id`
  - `owns.sources.name|id`, `owns.accessProfiles.name|id`, `owns.entitlements.name|id`, `owns.roles.name|id`, `owns.governanceGroups.name|id`, `owns.apps.name|id`, `owns.fallbackApprover` (bool)
  - `attributes.<technicalName>` — e.g. `uid`, `firstname`, `lastname`, `displayName`, `email`, `personalEmail`, `phone`, `workPhone`, `identificationNumber`, `cloudAuthoritativeSource`, `cloudLifecycleState`, `identityState` (`ACTIVE`, `INACTIVE_LONG_TERM`, `INACTIVE_SHORT_TERM`), `startDate`, `endDate`, `nextProcessing` (dates), plus any custom identity attribute by technical name.
- Nested:
  - `@accounts`: `id`, `name`, `accountId`, `disabled`, `locked`, `privileged`, `manuallyCorrelated` (bool), `passwordLastSet`, `created` (date), `entitlementAttributes.<attr>` (e.g. `memberOf` on AD), `source.name`, `source.id`, `source.type`
  - `@access`: `id`, `type` (`ENTITLEMENT`, `ACCESS_PROFILE`, `ROLE`), `displayName`, `name`, `description`, `privileged`, `attribute`, `value`, `disabled` (roles), `source.name`, `source.id`, `owner.id`, `owner.name`, `owner.displayName`
  - `@apps`: `id`, `name`, `source.name`, `source.id`, `account.id`, `account.accountId`

## entitlements

- First: `id`, `displayName`, `name`, `description`, `privileged`, `requestable` (bool), `attribute`, `value`, `modified`, `synced`, `tags`.
- Second: `source.name|id`, `segments.name|id`, `owner.name|id` (primary), `owners.name|id|email|type (IDENTITY, GOVERNANCE_GROUP)|direct|primary`, `privilegeLevel.direct|inherited|effective|setBy|setByType` (values HIGH, MEDIUM, LOW, NONE).
- Nested: `@accessModelMetadata`: `key`, `name`, `type` (custom, governance), `description`, `value`, `valueName`.

## accessprofiles

- First: `id`, `name`, `description`, `created`, `modified`, `synced`, `requestable`, `entitlementCount`, `tags`.
- Second: `owner.name|id|type|email`, `owners.*` (as entitlements), `source.name|id`, `segments.name|id`.
- Nested: `@entitlements`: `attribute`, `description`, `id`, `name`, `value` · `@apps`: `id`, `name`, `description`, `owner.*`.

## roles

- First: `id`, `name`, `description`, `created`, `modified`, `synced`, `enabled`, `requestable`, `accessProfileCount`, `entitlementCount`, `dimensional`, `dimensionCount`, `dimensionSchemaAttributeCount`, `tags`.
- Second: `accessProfiles.id|name`, `owner.id|name|type|email`, `owners.*`, `segments.name|id`.
- Nested: `@entitlements` (`attribute`, `schema`, `description`, `id`, `name`, `value`, `hasPermissions`), `@accessModelMetadata`, `@dimensions` (`id`, `name`, `description`; `dimensions.accessProfiles`, `dimensions.entitlements`), `@dimensionSchemaAttributes` (`name`, `displayName`, `derived`).

## events (audit)

- First: `created`, `name` (e.g. "Create Source Passed"), `operation` (CREATE…), `status` (PASSED, FAILED…), `technicalName` (`OBJECT_OPERATION_STATUS`, e.g. `SOURCE_CREATE_PASSED`), `details`, `type` (e.g. `SOURCE_MANAGEMENT`, `WORKFLOW`, `CERTIFICATION`, `AUTH`), `id`, `ipAddress`, `objects`, `action` (searchable event name / legacy name), `trackingNumber`.
- Second: `actor.name`, `target.name`; `attributes.*` (e.g. `sourceName`, `errors`, `provisioningResult`, `<field>_before` / `<field>_after`).
- Retention: one year plus the current month. Event names: `audit-events-reference.md`.

## accountactivities

- First: `action` (Access Request, Account Attribute Update, Account State Update, Certification, Cloud Automated …, Identity Attribute Update, Identity Refresh, Lifecycle State Refresh, Lifecycle State Change, Password Change), `status`, `id`, `trackingNumber`, `created`, `modified`, `sources`, `stage`, `errors`, `warnings`.
- Second: `requester.id|name`, `recipient.id|name` (examples sometimes use `target.`).
- Nested: `@originalRequests` / `@accountRequests` (`accountId`, `op`, `source.id|name|displayName|type`, `provisioningTarget.*`, `attributeRequests.op|name|value`; accountRequests also `result.status|errors|warnings|ticketId`), `@expansionItems` (`accountId`, `cause` Role/AttributeSync/AttributeAssignment/ProvisioningPolicy, `name`, `source.*`, `attributeRequest.*`), `@approvals` (`workItemId`, `created`, `modified`, `result` Finished/Rejected, `comments.*`, `owner.name|id`).
- Completed account actions are kept 7 days.

## workflow history (UI category)

- First: `id` (`<executionId>-<eventId>`), `workflowExecutionId`, `eventId`, `workflowName`, `workflowId`, `status` (Completed, Failed, Canceled, TimedOut, Terminated — case-sensitive), `workflowTest` (bool), `requestId`, `created`, `type` (ActivityTaskCompleted/Failed/Scheduled/Started/TimedOut, ChildWorkflowExecution*, WorkflowExecutionCanceled/Completed/Failed/Started, WorkflowTaskFailed).
- Second: `owner.name|id`, `attributes.attempts|displayName|error|input|lastKnownError|result|stepName|task|trigger`.
- Kept 90 days.

## cloud resources (CIEM)

`cloudSourceType`, `cloudSourceNativeId`, `cloudSubSourceNativeId`, `resourceId`, `resourceName`, `resourceType`, `service`, `source`, `attributes.*`; nested `@identities` (`accessLevel` R/W/A, `accountId`, `accountName`, `accountSourceType`, `correlated`, `department`, `displayName`, `email`, `region`).
