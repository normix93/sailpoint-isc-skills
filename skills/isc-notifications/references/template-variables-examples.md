# Template variables — common templates

From the template detail pages on documentation.sailpoint.com (checked November 2026). All of these are v1 templates, so v1 globals (`$user`, `${PRODUCT_NAME}`, `$spTools`) are also available. The tenant's own list is always `GET /notification-template-variables/v1/{key}/EMAIL`.

## Access Request Decision — to the requester
Default subject: `Your access request for ${accessProfileName} has been #if($approved)approved#{else}denied#end`

| Variable | Type | Meaning |
|---|---|---|
| accessibleItems | List | items the user gets if approved |
| accessProfileName | String | requested access profile |
| activationRequired | Boolean | entitlement must be activated before each use (JIT) |
| approved | Boolean | approved or not |
| approverName | String | approver display name |
| rejecterName | User | reviewer who denied |
| removeDate | String | date access will be removed |
| requestedForIdentityName | String | target user |
| requestedObjectName / requestedObjectType | String | requested item and its type |
| requesterName | String | who submitted |
| reviewerComment | String | denial comment |
| roleRequestEnabled | Boolean | role requests enabled |
| sourceInformation | List of maps | `sourceAccountName`, `sourceAccountId`, `sourceName` (multi-account requests only) |
| accessRequestMetadata | Map | dimension attributes; matched ones under `matchedRolesInformation` |

## Access Request Reviewer — to each reviewer (also reminders/escalations)
Default subject: `New access request for ${requestedForIdentityName} ready for review`

accessibleItems (List) · removeDate · requestedForIdentityName · requestedObjectName · requestedObjectType · requesterComments (justification) · requesterName · roleRequestEnabled · sourceInformation (List) · matchedRolesInformation (Map, dimension roles) · requestContextInformation (Map, dimension roles).

## New Account Provisioned — to the user
Default subject: `${source} - A New Account Has Been Created For ${username}`

| Variable | Type | Meaning |
|---|---|---|
| accountAccess | List | entitlements on the new account |
| accountAttributes | Map | account attributes, e.g. `${accountAttributes.firstName}` (no `password`) |
| accountIdAttribute | String | attribute used as account ID |
| accountUserName | String | account unique identifier |
| identity | Attributes | identity attributes, e.g. `${identity.displayName}` |
| source | String | source name |
| username | String | ISC username |

Enable per source with a PATCH on the source's `connectorAttributes.accountCreateNotification`.

## Pending Manual Changes — to source owners
Default subject: `Changes requested to $identityDisplayName need manual interaction`

approvalSet (ApprovalSet: requested changes) · identityDisplayName · identityName · item (Workitem) · launcher (who requested).

## Certification Campaign Started — to each certifier when the campaign starts
Default subject: `Please Review Your Employees' Access` (page et_certs_started.html, checked 14 Nov 2026)

| Variable | Type | Meaning |
|---|---|---|
| campaign.id / .name / .description | UUID / String | the campaign |
| campaign.type, campaign.reviewerType | enum | campaign type, reviewer type |
| campaign.activationDate, campaign.deadlineDate | String (ISO 8601) | activation and due date |
| certification.id / .name | UUID / String | this reviewer's certification (link: `$identityNowUrl/ui/d/certifications-review/certification/gov_${certification.id}`) |
| certification.reviewerName, .reviewerType | String | the reviewer |
| certification.totalItems, .totalSubjects | Number | items and identities to review |
| certification.signDate | String | sign-off date |
| recipientId | String | recipient ID |
| requesterName | String | who activated the campaign |

The default body uses `$__recipient.name` and `$__dateTool.toDate("yyyy-MM-dd'T'HH:mm:ss.SSSXXX", $campaign.deadlineDate)` although the page says "version 1 global variables": trust the default body and the variables endpoint over the v1/v2 label. Later reminders use *Certification Due*.

## Lifecycle State Change
Default subject: `Lifecycle state change for ${identityName}`

identityName · identity (Attributes) · oldState · newState.

## Account Selection Notification
Default subject: `Account selection required for $identityDisplayName` — variable identityDisplayName.

## Approval Request Assigned (generic approvals)
Example variables from the API spec: `approvalName` (String), `requester` (object: `identityID`, `type`, `name`, `email`). Read the full list from the variables endpoint for key `approval_request_notification`.
