---
name: isc-notifications
description: SailPoint Identity Security Cloud (ISC/IdentityNow) email and notification templates reference. Use when someone asks which email ISC sends in a situation, who receives it, how to edit or disable a template, which Velocity variables a template exposes, how to add conditions/loops/dates to a template, how to change From/Reply-To, CC/BCC, Slack/Teams mediums, or how to manage templates through the API.
---

# SailPoint ISC notifications and email templates

ISC sends system emails from **built-in templates** (Admin > Global > Email Templates). You can't create new template types, only customize the existing ones (per key, medium and locale). For custom emails on your own events, use a workflow with **Send Email** (`isc-workflows` skill).

## How to answer

**"Which email is sent when X happens, and to whom?"**
1. Find the template in `references/templates-catalog.md` (grouped by area, with trigger condition and detail-page link).
2. If several could apply (e.g. *Access Request Decision* vs *Decision for Other*, *Reviewer* vs *Reassignment*), explain the difference.
3. Give the recipient and the process setting that controls it, if any (some notifications are toggled in the process configuration, e.g. lifecycle state change, certification reminders).

**"How do I edit it / what variables can I use?"**
1. UI path: Admin > Global > Email Templates > *template* > Edit (WYSIWYG or Source).
2. Variables: template-specific ones from the detail page (examples for common templates in `references/template-variables-examples.md`) **plus** global ones (`references/velocity-and-variables.md`). The authoritative list for a tenant is the API: `GET /notification-template-variables/v1/{key}/{medium}` (returns `globalVariables` and `templateVariables` with type, description, example), or type `${` in the editor, or put `$__contentJson` in a test.
3. Give a ready-to-paste snippet in Velocity (conditions, loops, dates) that uses only listed variables.
4. Remind the test limits: test emails render only global variables; conditional blocks are skipped.

**API work** (bulk changes, sandbox→prod, CI): `references/notifications-api.md`.

## Core facts

- Syntax: Apache Velocity. `${approverName}`, `${user.workPhone}`, `#if($approved)…#else…#end`, `#foreach($i in $accessibleItems)…#end`.
- Two template generations:
  - **v1** (most templates): globals `$user` (recipient identity), `${PRODUCT_NAME}`, the product URL, `$spTools.formatDate(...)`.
  - **v2** (Non-Employee templates, Campaign Template Pre-Generation, Pending Task Daily Digest, Work Reassignment, User Invitation): `$__global.productName`, `$__global.emailFromAddress`, `$__recipient` (name, id, email, phone), `$__contentJson`, `$__dateTool`, `$__numberTool`, `$__util` (`getUser()`, `getObjectByJsonPath()`, `getIdentityDetailsByID()`, `getMultipleIdentitiesDetailsByID()`), `$__esc`.
  - `$user` works only in v1 templates. The v1/v2 label isn't always consistent (e.g. *Certification Campaign Started* is listed as v1 but its default body uses `$__recipient` and `$__dateTool`): check the default body and the variables endpoint.
- HTML is sanitized: allowed `a`, `img`, `p`, `div`, `h1`–`h6`, lists, `blockquote`, `strong`, `em`, `u`, `s`, `code`, `pre`, `br`, `span`, `sup`/`sub`, `table`/`tr`/`td`/`th`…; attribute `style` everywhere, `href` on links, `src`/`alt`/`width`/`height` on images. No `<head>`, no comments, no attachments; images by external URL (or small base64). Custom template max **130 KB**.
- **From** is set globally or per brand (verified sender/domain), not per template; **Reply-To** is per template and accepts `#if/#else`.
- **Disable** one template: make `no_send` or `Stop` the first word of the subject (case-insensitive). This overrides process settings — warn about password reset, certifications, non-employee flows.
- **Redirect** everything to a test address: Email Templates > Settings > Test Address (great for sandboxes; remember to switch back to *Intended Recipients*).
- A customized template stops receiving SailPoint's default text updates (support can reset that).
- Mediums: `EMAIL`, `SLACK`, `TEAMS` (Slack/Teams need the integration). Per-key preferences (enabled mediums, CC/BCC up to 5 each) via `/notification-preferences/v1/{key}`; CC/BCC is refused on templates carrying secrets (reset codes…).
- All notifications are on by default except *Pending Task Daily Digest*. No per-user customization.

## Snippets

```velocity
## approved/denied subject
Your request for ${requestedObjectName} was #if($approved)approved#{else}denied#end

## list of items with a fallback
#if($accessibleItems && $accessibleItems.size() > 0)
<ul>#foreach($item in $accessibleItems)<li>${item}</li>#end</ul>
#else
<p>No items.</p>
#end

## null-safe value
#if($reviewerComment)<p>Comment: ${reviewerComment}</p>#end

## v2 template: date and recipient
Hello ${__recipient.name}, today is $__dateTool.format('dd/MM/yyyy', $__dateTool.date)

## show everything the template receives (debug only)
<pre>$__contentJson</pre>
```

Check that each variable exists for that template before using it; unknown variables render literally (`${foo}`) unless written as quiet references (`$!{foo}`).

## Check before delivering

```bash
python3 scripts/check_template.py body.html --subject '…' --vars accessibleItems,approved,requesterName   # or --vars vars.json from the variables endpoint; --v2 for v2 templates
```
Finds unbalanced `#if/#foreach/#end`, variables the template doesn't have, `$user` in v2 templates, HTML the sanitizer strips, `<head>`/comments, size over 130 KB, subjects that disable the template.

## Reference map

| File | Contents |
|---|---|
| `references/templates-catalog.md` | every built-in template: when it's sent, detail page |
| `references/template-variables-examples.md` | variables of common templates (access request, reviewer, new account, manual changes, lifecycle) |
| `references/velocity-and-variables.md` | Velocity syntax, global variables v1/v2, tools, escaping, HTML rules |
| `references/notifications-api.md` | endpoints and flows: list keys, read variables, customize, test, preferences, senders |
| `references/notification-api-schemas.md` | generated schemas (template, variables, preferences, test request) |

Not affiliated with SailPoint. Official docs: https://documentation.sailpoint.com/saas/help/common/emails/using_email_templates.html
