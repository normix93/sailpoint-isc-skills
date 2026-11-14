# Workflow trigger input fields

Field paths of the sample input for each workflow trigger, taken from the "JSON Input Sample" panels of https://documentation.sailpoint.com/saas/help/workflows/workflow-triggers.html (checked 14 November 2026). In a workflow, prefix them with `$.trigger.` (e.g. `$.trigger.account.nativeIdentity`); in a trigger filter, start from `$` (e.g. `$[?(@.source.name == "AD")]`). `[]` = array item. Samples show typical fields, not a contract: confirm on a real execution (Execution history → step input).

| Trigger | Fields (two levels) |
|---|---|
| Access Request Decision | accessRequestId · requestedBy.{id,name,type} · requestedFor.{id,name,type} · requestedItemsStatus[].{id,name,type,description,operation,comment,clientMetadata,approvalInfo} |
| Access Request Submitted (workflow approval) | accessRequestId, accountActivityId, requestId, workflowId, workflowExecutionId, parentWorkflowExecutionId, tenantId, org, pod · requestedItem.{id,name,description,type,operation,addDate,removeDate,reauthRequired,comment,assignmentContext,requestedAccounts} (one item per execution) · requestedBy.{id,name,type} · requestedFor.{id,name,type} · sod.{violated,details} · ipaddress, countryRaisedfrom, requestedAt |
| Account Aggregation Completed / Accounts Collected for Aggregation | source.{id,name,type} · status · started · completed · errors · warnings · stats.{scanned,unchanged,changed,added,removed} |
| Account Created / Account Deleted | event.{type,cause} · source.{id,name,alias,owner,governanceGroup} · account.{id,name,nativeIdentity,uuid,correlated,isMachine,origin,attributes} · identity.{id,name,alias,email} |
| Account Updated | as Account Created + accountChangeTypes · singleValueAttributeChanges[].{name,oldValue,newValue} · multiValueAttributeChanges[].{name,addedValues,removedValues} · entitlementChanges[].{attributeName,added,removed} |
| Dataset Account Created / Updated / Deleted | event, source (as above) · account.{id,name,nativeIdentity,uuid,correlated,isMachine,origin,hasEntitlements,datasetId,resourceId,resourceType,attributes}; Updated adds the change arrays. No identity |
| Native Change Account Created / Updated / Deleted | eventType · identity.{id,name,alias,type,email,manager} · source.{id,name,alias,type,owner,governanceGroup} · account.{id,name,type,uuid,correlated,nativeIdentity} · accountChangeTypes · singleValueAttributeChanges[] · multiValueAttributeChanges[] · entitlementChanges[] |
| Identity Created / Identity Deleted | identity.{id,name,type} · attributes.{firstname,lastname,email,department,displayName,created,employeeNumber,uid,inactive,phone,identificationNumber,isManager,manager,…custom} |
| Identity Attributes Changed | identity.{id,name,type} · changes[].{attribute,oldValue,newValue} |
| Identity Lifecycle State Changed | identity.{id,name,type} · oldLifecycleState · newLifecycleState |
| Identity Lifecycle State Change Processed | identity.{id,name,email,authoritativeSource} · manager.{id,name,email} · previousState.name · newState.name · changeDetails.{isManual,actor,process} |
| Campaign Activated / Generated / Ended | campaign.{id,name,description,created,modified,deadline,type,campaignOwner,status} |
| Certification Signed Off | certification.{id,name,created,modified,campaignRef,completed,hasErrors,errorMessage,decisionsMade,decisionsTotal,due,signed,reviewer,campaignOwner,reassignment,phase,entitiesCompleted,entitiesTotal} |
| Form Submitted | submittedAt, tenantId, formInstanceId, formDefinitionId, name, createdBy, submittedBy, formData.{<your form's keys>} |
| Interactive Trigger | interactiveProcessId · launchedAt · launchedBy.{id,type} · workflowId · config |
| Machine Identity Created / Deleted | eventType · machineIdentity.{id,name,created,modified,businessApplication,description,attributes,subtype,owners,sourceId,uuid,nativeIdentity,manuallyEdited,manuallyCreated,datasetId,source,userEntitlements,existsOnSource} |
| Machine Identity Updated | as above + machineIdentityChangeTypes · userEntitlementChanges · ownerChanges · singleValueAttributeChanges[] |
| Outlier Detected | score · outlierType · identity.{id,displayName,type} · _meta |
| Provisioning Completed | trackingNumber · action · requester.{id,name,type} · recipient.{id,name,type} · errors · warnings · sources · accountRequests[].{source,accountId,accountOperation,provisioningResult,provisioningTarget,ticketId,attributeRequests} |
| Scheduled Search | searchName · query · fileName · ownerName · ownerEmail · searchResults.{Identity,Account,Entitlement} · signedS3Url |
| Source Created / Updated / Deleted | id · name · type · connector · created/modified/deleted · actor.{id,name,type} |
| VA Cluster Status Change Event | created · type · application.{id,name,attributes} · healthCheckResult.{status,resultType,message} · previousHealthCheckResult.{…} |
| Risk Signal Created / Updated | risk.{id,name,description,type,severity_tier,status,source_detected_at} · owners.primaryOwner · target_entity.{type,id,name}; Updated adds changes[].{attribute,oldValue,newValue} |
| Intel Response Actions (/ NHI) | requestId · actionType · identityType · identityId · accountIds (human only) · context.{source,externalAlertId,reason,operator} |
| DAS Activity Alert | appId, appName, timestamp, userName, objectName, objectType, path, actionType, ipAddress, alertRuleNames, alertRuleSeverities, identityId, identityEmail, identityDepartment, … |
| CAEP events (credential change, device compliance, risk level, session revoked, token claims) | pk · correlatedID · identityAttributes.{…} · accountAttributes.{…} (some) · ssfEvent.{iss,jti,iat,aud,txn,sub_id,events} — filter on `$.ssfEvent.events["https://schemas.openid.net/secevent/caep/event-type/<type>"]` |
| ServiceNow Access Request Cancelled (Service Catalog) | id, requestCreated, requestedFor, requestedBy, cancelledBy, requestType, cancelComment, accessRequestItems[].{id,name,type,clientMetadata,…} |
| ServiceNow Approval Request Created / Updated (Service Catalog) | type, action, name, actor, status, trackingId, attributes.{accessRequestId, accessItemName, approvers, assignedTo, clientMetadata, status, approvedBy (updated), …} |

Notes
- **Access Request Submitted runs once per requested item** (`requestedItem`, singular) — unlike the Decision trigger, which lists all items in `requestedItemsStatus[]`.
- The new account triggers (`ACCOUNT_CREATED_V2`…) carry `event.type`/`event.cause` and an `account` + `source` + `identity` block; older event-trigger payloads (Account Correlated, Account Attributes Changed) differ — see the `isc-event-triggers` skill.
- Scheduled triggers have no input; External trigger input is whatever the caller sends in `input`.
