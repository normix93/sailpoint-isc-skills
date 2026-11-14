# Built-in email templates

Summarised from https://documentation.sailpoint.com/saas/help/common/emails/available_templates.html (checked November 2026). Detail pages (default subject + template variables) are at `https://documentation.sailpoint.com/saas/help/common/emails/<page>`.

The UI shows template **names**; the API uses **keys** (e.g. `cloud_manual_work_item_summary`, `approval_request_notification`, `approval_completed_notification`). Map one to the other in a tenant with:

```
GET /notification-template-defaults/v1?filters=medium eq "EMAIL"     # key, name, medium, locale, subject, description
```

Templates marked **v2** use the v2 global variables (`$__recipient`, `$__global`, `$__util`…); all others are v1 (`$user`, `${PRODUCT_NAME}`, `$spTools`).

## Access requests

| Template | Sent when | Page |
|---|---|---|
| Access Request Reviewer | a request waits for this reviewer (also reminders and escalations) | et_ar_reviewer.html |
| Access Request Decision | the requester's request was approved or denied | et_ar_decision.html |
| Access Request Decision for Other | decision on a request someone else made for this user | et_ar_decisionother.html |
| Access Request for Other | someone requested access on this user's behalf | et_ar_forother.html |
| Access Request Assignment | an auto-approved request is assigned to the requester | et_ar_assignment.html |
| Access Request Cancelled | a pending request was cancelled before approval/provisioning | et_ar_cancelled.html |
| Access Request Reassignment | requests reassigned to a reviewer | et_ar_reassign.html |
| Access Request Submitted Email for Requester After Validation | validation finished: which items succeeded/failed | et_ar_validation.html |
| Access Request for Identity with Multiple Accounts Failed | request failed because the user has several accounts on the source | et_ar_failedaccounts.html |
| Access Revoke Request Reviewer | a revoke request to review | et_ar_revoke_reviewer.html |
| Access Revoke Request Submitted for Requester Identity / for Requested-For Identity | a revoke request was submitted | et_ar_revokerequester.html / et_ar_revokerecipient.html |
| Access Revoke Request Decision for Requester / for Requested-For Identity | decision on a revoke request | et_ar_revokedecisionrequestor.html / et_ar_revokedecisionrecipient.html |
| Access Revoke Approval Reassignment | a revoke request reassigned to the user | et_ar_revoke_approval.html |
| Access Sunset Date Reminder | access with an end date is about to expire | et_ar_sunsetreminder.html |
| Access End Date Modified | a certification changed the access end date | et_access_end_date.html |
| Access Profile Owner Approval Notification | a role request grants the owner's access profile | et_ap_approval.html |
| Access Profile Cleanup Notification | entitlement deletions changed access profiles | et_ap_entitlement_change.html |

## Approvals (generic approval framework / workflows)

| Template | Sent when | Page |
|---|---|---|
| Approval Request Assigned | an approval is created for the approver | et_approval_request.html |
| Approval Request Reminder | approver hasn't acted yet | et_approval_reminder.html |
| Approval Request Commented | someone commented | et_approval_comment.html |
| Approval Request Completed | approval completed | et_approval_complete.html |
| Approval Request Escalation Approver / Requester | escalation of an inactive approval | et_approval_request_esc_approver.html / et_approval_request_esc_requester.html |
| Approval Request Timeout | closed for timeout | et_approval_request_timeout.html |

## Accounts and provisioning

| Template | Sent when | Page |
|---|---|---|
| New Account Provisioned | provisioning created an account for the user (enable per source via `connectorAttributes.accountCreateNotification`) | et_newacctprovisioned.html |
| Pending Manual Changes | a manual-provisioning source needs a change (to source owners) | et_pending_changes.html |
| Task Reassignment | a provisioning task was reassigned | et_task_reassign.html |
| Account Selection Notification | account selection required during provisioning | et_acct_select.html |
| Account Request Submitted / Account Request Failed | account request submitted / failed | et_acct_request_submitted.html / et_acct_request_failed.html |
| Account Deletion Request Completed | account deletion request done | et_acct_deletion_request.html |
| Account Correlation Test Complete | correlation test finished | et_acct_corr_stat.html |
| Correlation Recommendations Complete / Create Account Policy Recommendations Complete | AI recommendations ready | et_corr_rec.html / et_create_acct_rec.html |
| Lifecycle State Change | identity's lifecycle state changed (recipients configured in the identity profile LCS) | et_lcs_change.html |
| Remediation Work Item | remediation work item assigned | et_remediation_work_item.html |
| Work Item Forward | work forwarded to another user | et_work_item_forward.html |
| Work Reassignment Created / Updated (**v2**) | reassignment configuration created/changed | et_reassign_config_create.html / et_reassign_config_update.html |
| Pending Task Daily Digest (**v2**, off by default) | daily, if the user has open Task Manager tasks (key `cloud_manual_work_item_summary`) | et_taskmgr_sub.html |

## Certifications

| Template | Sent when | Page |
|---|---|---|
| Certification Campaign Started | campaign started (reviewers) | et_certs_started.html |
| Certification Due | 1 week after start, then every 7 days until sign-off/end | et_certs_certdue_reminder.html |
| Certification Reassignment / Certification Subjects and Items Reassignment | reassignment to a reviewer | et_certs_reassignment.html / et_certs_items_reassign.html |
| Campaign Template Pre-Generation Notification (**v2**) | one week before scheduled generation | et_certs_scheduleremind.html |
| Certification (Legacy), Certification Due (Legacy), Certification Reassignment (Legacy) | legacy campaigns | et_certs_certcreated.html, et_certs_certdue.html, et_certs_reassign.html |

## Policies and risk

SoD Policy Violation Notification (et_sod_violation_notify.html) · SoD Policy Scheduled Evaluation (et_sod_sub_notify.html) · Policy Version Changed (et_policy_change.html) · Privileged Entitlement Recommendation Available for Review (et_privilege_rec_rev.html) · Non-Human Identity Risk Shared (et_nhi_risk_shared.html) · Identity Errors — ≥ 5 % identities in error (et_identityerrors.html).

## Search

Subscription Notification — scheduled search results to subscribers (et_search_sub_notify.html).

## Passwords, login, users

Account Password Reset (et_helpdesk_pwreset.html) · Password Reset Code (et_pw_resetcode.html) · Onboarding Password Reset — first password (et_set_password.html) · Password Expiration (et_pw_expiration.html) · User Password Changed (et_user_pw_changed.html) · Application Password Changed (et_app_pw_changed.html) · Forgot User Name (et_forgot_username.html) · Unlock User Code / User Locked Out / User Unlocked (et_unlock_user_code.html, et_user_lockedout.html, et_user_unlocked.html) · Preference Update — auth settings changed (et_preferenceupdate.html) · User Invitation (**v2**, et_user_invitations.html).

## Non-employees (all **v2**)

Non-Employee Request Created (et_ne_acctrequest.html) · Non-Employee Account Review (et_ne_acctreview.html) · Non-Employee Account Request Result (et_ne_acctreqdecision.html) · Non-Employee End Date Reminder — 7 days before (et_ne_enddateremind.html) · Non-Employee Account Upload Succeeded / Failed (et_ne_upload_succeed.html, et_ne_upload_fail.html).

## Just-in-time access

Activation Ready, Extended, Failed, Expiration in 15 min, Deactivated, Deactivation Failed, Deprovisioning Failed — each also in a "for Other" variant (pages `et_jit_*.html`).

## Machine identities

Machine Account Creation Request Completed (et_machine_acct_request.html) · Machine Identity Request Completed / Failed (et_mi_completed.html, et_mi_failed.html) · New Machine Account Assigned (et_machine_acct_assigned.html).

## Sources, apps, VA, platform

Source Health (et_source_health.html) · Application Health (et_app_health.html) · Application Discovery (et_app_disc.html) · Virtual Appliance Health (et_va_health.html) · VA Error State Active / Resolved (et_va_error_active.html, et_va_error_resolved.html) · VA Out of Date (et_va_outofdate.html) · VA Pinned Component Expiration / VA Unpinned Notification (et_va_pin_expiration.html, et_va_unpinned.html) · Source Collaboration (access request, changes required, comment, reassigned, review, collaborator notification, remove assignee level: `et_sourcecollab_*.html`) · Agentic Fabric Source Assignment for Onboarding (et_saf_source_assigned.html) · GenAI Entitlement Description Regeneration Complete (et_genai_ent_desc_regen.html).

## Data Access Security

Alert Rule, Campaign Assigned / Reminder / Revocation Successful / Failed, Report Created / Shared, Data Owner Identified, Data Owner Election tasks (pages `et_das_*.html`).
