# Velocity in ISC email templates

Sources: SailPoint "Using Email Templates" and "Available Email Templates" pages, Notifications API spec, Apache Velocity user guide.

## Syntax essentials

| Need | Velocity |
|---|---|
| value | `${approverName}` or `$approverName` |
| property of an object/map | `${user.workPhone}`, `${accountAttributes.mail}`, `${identity.displayName}` |
| print nothing when null | `$!{reviewerComment}` |
| condition | `#if($approved) … #elseif($x == "y") … #else … #end` |
| null / empty check | `#if($var)`, `#if($list && $list.size() > 0)` |
| loop | `#foreach($i in $accessibleItems) ${i} #end` (`$foreach.count`, `$foreach.hasNext`) |
| local variable | `#set($name = "x")` |
| comment (not rendered) | `## line comment`, `#* block *#` |
| inline else in a word | `#if($approved)approved#{else}denied#end` |
| string compare | `#if($requestedObjectType == "ROLE")` |

Avoid HTML comments (`<!-- -->`), they're stripped by the sanitizer.

## Global variables

**v1 templates** (most):
- `$user` — recipient identity (name, alias, manager, phone, email…). Only in v1.
- `${PRODUCT_NAME}` — product name (brand-customizable).
- the ISC home URL variable (listed in the editor's `${` overlay).
- `$spTools.formatDate(...)` — date formatting helper.

**v2 templates** (Non-Employee, Campaign Template Pre-Generation, Pending Task Daily Digest, Work Reassignment, User Invitation):
- `$__global.productName`, `$__global.emailFromAddress`, `$__global.standardLogoURL`
- `$__recipient` — `name`, `id`, `email`, `phone`
- `$__contentJson` — the whole triggering event as JSON (great for discovery)
- `$__dateTool` — e.g. `$__dateTool.format('yyyy-MM-dd', $__dateTool.date)`
- `$__numberTool` — number formatting
- `$__esc` — `$__esc.html($value)`, `$__esc.url($value)`
- `$__util` — `getUser()`, `getObjectByJsonPath()`, `getIdentityDetailsByID()`, `getMultipleIdentitiesDetailsByID()`

Exact names for a template: `GET /notification-template-variables/v1/{key}/{medium}` → `globalVariables[]` and `templateVariables[]` (key, type, description, example).

## Discovering variables

1. API variables endpoint (best).
2. Type `${` in the editor → overlay with globals and some template-specific variables.
3. Put `<pre>$__contentJson</pre>` (v2) or the template's object variables in a copy, trigger the real process in a sandbox with Email Settings → Test Address.

Test emails from the editor render **only globals**; template variables are null and conditional sections are dropped — test with a real event.

## HTML rules (sanitizer)

- Elements: `a`, `img`, `p`, `div`, `h1`–`h6`, `ul`, `ol`, `li`, `blockquote`, `strong`, `strike`, `tt`, `code`, `pre`, `big`, `small`, `br`, `span`, `em`, `s`, `u`, `sup`, `sub`, `ins`, `del`, `table`, `tr`, `td`, `th`.
- Attributes: `style` (all), `id` (basic/block/table), `src`, `alt`, `height`, `width` (img), `href` (a).
- No `<head>`, no comments, no `<style>` blocks (use inline `style=`), no attachments.
- Images: external HTTPS URL; base64 only small, compressed (bounces, some clients block it).
- Size ≤ 130 KB.

## From / Reply-To / disabling

- From: global or per brand, must be a verified address/domain (`/verified-from-addresses/v1`, `/verified-domains/v1`); not per template.
- Reply-To: per template, accepts Velocity conditions.
- Disable a template: subject starting with `no_send` or `Stop`.
