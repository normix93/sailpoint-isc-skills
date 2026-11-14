# Notifications API

Generated details for every endpoint: `isc-api` skill → `references/endpoints/notification-templates.md`, `notification-template-defaults.md`, `notification-template-variables.md`, `notification-template-context.md`, `notification-preferences.md`, `send-test-notification.md`, `verified-from-addresses.md`, `verified-domains.md`, `mail-from-attributes.md`. Schemas: `notification-api-schemas.md`. Most calls need ORG_ADMIN and `idn:notification-*` scopes.

| Goal | Call |
|---|---|
| List built-in templates (key, name, medium, locale, default subject/body) | `GET /notification-template-defaults/v1` — filters `key` (eq, in, sw), `medium` (eq, sw), `locale` (eq, sw) |
| List the tenant's customized templates | `GET /notification-templates/v1` — same filters; sorters `key`, `name`, `medium` |
| Read one customized template | `GET /notification-templates/v1/{id}` |
| Variables for a template | `GET /notification-template-variables/v1/{key}/{medium}` (medium `EMAIL`, `SLACK`, `TEAMS`) |
| Customize a template | `POST /notification-templates/v1` with the full template object (copy the default, change `subject`/`body`/`replyTo`/`slackTemplate`/`teamsTemplate`). You can't add new keys. `header`/`footer` are deprecated and must be null |
| Revert customizations | `POST /notification-templates/v1/bulk-delete` with `[{"key": "...", "medium": "EMAIL", "locale": "en"}]` |
| Send a test | `POST /send-test-notification/v1` `{"key", "medium", "locale", "context": {…sample variables…}, "recipientEmailList": [...]}` — lets you supply template variables, unlike the UI test |
| Tenant global context (branding, product URL) | `GET /notification-template-context/v1` |
| Enable/disable mediums, CC/BCC for a key | `GET/PUT /notification-preferences/v1/{key}` (≤ 5 CC and ≤ 5 BCC, needs EMAIL enabled; refused on templates with secrets). Empty `mediums` = notification disabled for the tenant |
| Verified senders | `/verified-from-addresses/v1`, `/verified-domains/v1`; custom MAIL FROM domain: `/mail-from-attributes/v1` |

## Promote a customized template from sandbox to production

1. Sandbox: `GET /notification-templates/v1?filters=key eq "<key>"`.
2. Remove `id`, `created`, `modified`.
3. Production: `POST /notification-templates/v1` with that body.
4. `POST /send-test-notification/v1` with a sample `context`.
(Or include notification templates in an sp-config export/import if your tenant supports that object type — check `GET /sp-config/v1/config-objects`.)
