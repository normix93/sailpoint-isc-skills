# Demo: three questions, with and without the skills

Verbatim answers from the evaluation run (`evals/runs/`). Same model, no web access in either case.

## Which endpoint gives me the status of access requests, what can I filter on and how do I paginate?

**With the skills**

Use GET /access-request-status/v1 (scope idn:access-request-status:read; any user can see their own requests, ORG_ADMIN needed for others'). The filters parameter accepts only accessRequestId (eq, ne, gt, ge, lt, le, sw), accountActivityItemId (eq, in, ne, gt, ge, le, sw) and created (eq, ne, gt, ge, lt, le), e.g. filters=created ge 2026-01-01T00:00:00Z; sorters: created, modified, accountActivityItemId, name. Who/what is selected with separate query params: requested-for, requested-by, regarding-identity (mutually exclusive with the first two; 'me' = caller), assigned-to, and request-state=EXECUTING. Paginate with limit (default and max 250) and offset (starting at 0), with a stable sorters (e.g. -created), looping until a page returns fewer than limit items; count=true puts the total in X-Total-Count. For an org-wide admin view with a status filter there is the experimental GET /access-request-administration/v1 (header X-SailPoint-Experimental: true).

**Without**

Use GET /v3/access-request-status (also /beta/access-request-status). Query params: requested-for, requested-by, regarding-identity (all identity IDs, or 'me'), assigned-to, count, plus filters and sorters. Supported filters include accessRequestId (eq, in, ge, gt, le, lt, ne, sw), status (eq, in, ne), created (eq, in, ge, gt, le, lt, ne, sw) and requestedFor.id; sorters: created, modified, accountActivityItemId, name. Paginate with limit (max 250) and offset; add count=true to get the X-Total-Count header and loop offset += limit until you have them all. Note: at least one of requested-for/requested-by/regarding-identity is typically required or it defaults to the caller's own requests unless you are an admin.

## Which workflow trigger should I use to do something when an employee changes department?

**With the skills**

Use the Identity Attributes Changed trigger (idn:identity-attributes-changed), which fires when identity attributes change during refresh; the payload has identity plus changes[] with attribute, oldValue, newValue. Filter it to department changes with $.changes[?(@.attribute == "department")] (optionally && @.newValue == "Finance" for a specific target). Then read $.trigger.identity.id and the old/new values in later steps (e.g. Get Identity, Manage Access). The filter is Jayway JSONPath; test it with the trigger's sample payload.

**Without**

Use the Identity Attributes Changed trigger (idn:identity-attributes-changed). It fires when an identity's attributes change after aggregation/identity refresh, and the payload contains identity plus a changes array with attribute, oldValue and newValue. Add a trigger filter such as $.changes[?(@.attribute == "department")] so the workflow only runs on department changes. The attribute must be an identity attribute mapped in the identity profile.

## Which email is sent when an access request is denied, to whom, and which variables can I use?

**With the skills**

The Access Request Decision template (et_ar_decision.html) goes to the requester when the request is approved or denied; Access Request Decision for Other goes to the requested-for user when someone else made the request (revoke requests have their own Revoke Request Decision templates). Variables include approved (Boolean), reviewerComment (denial comment), rejecterName, approverName, requestedObjectName/requestedObjectType, accessProfileName, requesterName, requestedForIdentityName, accessibleItems, removeDate, sourceInformation, plus v1 globals ($user, ${PRODUCT_NAME}, $spTools.formatDate). Default subject: Your access request for ${accessProfileName} has been #if($approved)approved#{else}denied#end. The authoritative list for your tenant is GET /notification-template-variables/v1/{key}/EMAIL.

**Without**

The 'Access Request Denied' / 'Access Request Decision - Denied' template (key ACCESS_REQUEST_DENIED or REQUESTED_ACCESS_DENIED) goes to the requester/recipient (requestedFor and requester if different). Variables include $requesterName, $requestedForName or $recipientName, $requestedObjects/$requestedObjectName, $approverName/$reviewerName, $comments/$deniedComment, plus global ones like $__global.productName and $__util helpers. I'm not fully sure of exact variable names; check the template defaults in Admin > Global > Notification Templates or via GET /beta/notification-template-defaults.
