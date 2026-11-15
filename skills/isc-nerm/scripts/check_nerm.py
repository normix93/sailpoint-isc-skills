#!/usr/bin/env python3
"""Static checks for SailPoint Non-Employee Risk Management (NERM) API calls. Standard library only.

Usage:
  python3 check_nerm.py body.json [more.json ...]          check request bodies (shape recognized by wrapper key)
  python3 check_nerm.py --url "GET https://acme.nonemployee.com/api/profiles?after_id=...&offset=10"
  python3 check_nerm.py --scopes nerm:api:profile-reader --request "POST /profiles"
  (--url and --scopes can be combined: --scopes ... --url "...")

Exit 0 = no errors, 1 = errors, 2 = unreadable input.

Bodies recognized: {"profile": ...}, {"profiles": [...]}, {"advanced_search": ...}, {"workflow_session": ...},
{"audit_events": ...}, {"user": ...}, {"users": [...]}. Unwrapped objects are recognized too and reported, because
NERM rejects them. Enums and field names come from nerm_api.json (generated from SailPoint's NERM OpenAPI spec and
the NERM API guide); see ../references/api-gotchas.md for the rules and the known doc/spec differences.
"""
from __future__ import annotations

import difflib
import json
import os
import re
import sys
from urllib.parse import parse_qsl, urlsplit

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "nerm_api.json"), encoding="utf-8") as fh:
    API = json.load(fh)

UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
READ_ONLY = {"id", "uid", "created_at", "updated_at"}
PROFILES_LIMIT_MAX = 500  # api-guide/pagination-metadata-filtering.md
AFTER_ID_OK = {"after_id", "profile_type_id", "limit", "metadata", "updated_after", "exclude_attributes"}
ISC_NELM = re.compile(r"non-employee-(sources|records|requests|approvals)")

# resource types of api-guide/authorization.md, by OpenAPI tag
RESOURCE_OF_TAG = {
    "profiles": "Profiles", "risk scores": "Profiles",
    "profile types": "Profile types",
    "workflows": "Workflows", "workflow actions": "Workflows", "workflow action performer": "Workflows",
    "workflow sessions": "Workflow sessions",
    "users": "Users & roles", "roles": "Users & roles", "delegations": "Users & roles", "user profiles": "Users & roles",
    "user roles": "Users & roles", "user managers": "Users & roles", "role profiles": "Users & roles",
    "forms": "Templates/Configuration", "form attributes": "Templates/Configuration", "pages": "Templates/Configuration",
    "page contents": "Templates/Configuration", "page elements": "Templates/Configuration",
    "page content translations": "Templates/Configuration", "attributes": "Templates/Configuration",
    "attribute options": "Templates/Configuration", "risk levels": "Templates/Configuration",
    "advanced search": "Advanced search",
    "audits": "Audit",
}


class Report:
    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def err(self, where: str, msg: str) -> None:
        self.errors.append(f"{where}: {msg}")

    def warn(self, where: str, msg: str) -> None:
        self.warnings.append(f"{where}: {msg}")


ALIASES = {"leaveofabsence": "On Leave", "onleave": "On Leave"}


def suggest(value, options) -> str:
    opts = [str(o) for o in options]
    alias = ALIASES.get(str(value).lower().replace(" ", "").replace("_", ""))
    if alias in opts and alias != value:
        return f" (did you mean '{alias}'?)"
    low = {o.lower().replace(" ", "").replace("_", ""): o for o in opts}
    key = str(value).lower().replace(" ", "").replace("_", "")
    if key in low:
        return f" (did you mean '{low[key]}'?)"
    m = difflib.get_close_matches(str(value), opts, n=1, cutoff=0.6)
    return f" (did you mean '{m[0]}'?)" if m else ""


def enum(rep: Report, where: str, key: str, value, options) -> None:
    if value is not None and value not in options:
        rep.err(where, f"{key} '{value}' is not valid{suggest(value, options)}; allowed: {', '.join(map(str, options))}")


def unknown_keys(rep: Report, where: str, obj: dict, allowed, what: str) -> None:
    for k in obj:
        if k not in allowed:
            rep.warn(where, f"unknown key '{k}' for {what}{suggest(k, allowed)}")


def check_attributes(rep: Report, where: str, attrs) -> None:
    if attrs is None:
        return
    if not isinstance(attrs, dict):
        rep.err(where, "'attributes' must be an object keyed by attribute uid")
        return
    for k in attrs:
        if " " in k or (k[:1].isupper() and k != k.upper()):
            rep.warn(where, f"attribute key '{k}' looks like a label; attributes are keyed by the attribute uid "
                            "(e.g. 'personal_first_name')")


# --------------------------------------------------------------------------- bodies

def check_profile(p, where: str, rep: Report, mode: str) -> None:
    """mode: create | patch | bulk_patch"""
    if not isinstance(p, dict):
        rep.err(where, "a profile must be an object")
        return
    allowed = set(API["profileKeys"]) | ({"id"} if mode == "bulk_patch" else set())
    for k in p:
        if k in READ_ONLY and not (k == "id" and mode == "bulk_patch"):
            rep.warn(where, f"'{k}' is read-only; it is ignored or rejected in requests")
        elif k not in allowed:
            rep.warn(where, f"unknown profile key '{k}'{suggest(k, allowed)}")
    if mode == "create":
        for r in API["profileRequired"]:
            if r not in p:
                rep.err(where, f"'{r}' is required to create a profile")
    if mode == "bulk_patch" and "id" not in p:
        rep.err(where, "each profile in a bulk PATCH /profiles needs its 'id'")
    enum(rep, where, "status", p.get("status"), API["profileStatuses"])
    enum(rep, where, "id_proofing_status", p.get("id_proofing_status"), API["idProofingStatuses"])
    pt = p.get("profile_type_id")
    if pt is not None and not (isinstance(pt, str) and UUID.match(pt)):
        rep.err(where, f"profile_type_id '{pt}' is not a UUID; use the profile type id, not its name")
    if "archived" in p and not isinstance(p["archived"], bool):
        rep.err(where, "'archived' must be a boolean")
    check_attributes(rep, where, p.get("attributes"))


def rule_variant(rule: dict) -> str | None:
    t = rule.get("type")
    if t in ("ProfileStatusRule", "ProfileTypeRule", "RiskRule"):
        return t
    if t == "ProfileAttributeRule":
        cot = rule.get("condition_object_type")
        for name in ("ProfileAttributeRuleString", "ProfileAttributeRuleDate", "ProfileAttributeRuleId"):
            if cot in API["ruleTypes"][name]["objectTypes"]:
                return name
        return "ProfileAttributeRule"
    return None


def check_rule(r, where: str, rep: Report) -> None:
    if not isinstance(r, dict):
        rep.err(where, "a condition rule must be an object")
        return
    types = sorted({v["type"] for v in API["ruleTypes"].values()})
    if "type" not in r:
        rep.err(where, f"'type' is required; one of {', '.join(types)}")
        return
    enum(rep, where, "type", r["type"], types)
    var = rule_variant(r)
    if var is None:
        return
    op = r.get("comparison_operator")
    if r.get("_destroy") is not None and not isinstance(r.get("_destroy"), bool):
        rep.err(where, "'_destroy' must be a boolean")
    if var == "ProfileAttributeRule":
        cot, ot = r.get("condition_object_type"), r.get("object_type")
        all_ot = sorted({o for n in ("ProfileAttributeRuleString", "ProfileAttributeRuleDate", "ProfileAttributeRuleId")
                         for o in API["ruleTypes"][n]["objectTypes"]})
        if cot is not None:
            enum(rep, where, "condition_object_type", cot, all_ot)
        elif ot == "NeAttribute":
            rep.warn(where, "uses \"object_type\": \"NeAttribute\" as in the API guide examples; the OpenAPI spec uses "
                            "\"condition_object_type\" with the attribute's type (e.g. TextFieldAttribute) — "
                            "if the tenant rejects one form, use the other")
        else:
            rep.err(where, f"ProfileAttributeRule needs 'condition_object_type' (one of {', '.join(all_ot)})")
        if not r.get("condition_object_id"):
            rep.err(where, "ProfileAttributeRule needs 'condition_object_id' (the attribute id)")
        ops = sorted({o for n in ("ProfileAttributeRuleString", "ProfileAttributeRuleDate", "ProfileAttributeRuleId")
                      for o in API["ruleTypes"][n]["operators"]})
        if op is None:
            rep.err(where, "'comparison_operator' is required")
        else:
            enum(rep, where, "comparison_operator", op, ops)
        if "value" not in r:
            rep.err(where, "'value' is required")
        return
    spec = API["ruleTypes"][var]
    for k in spec["required"]:
        if k not in r:
            rep.err(where, f"'{k}' is required for {var}")
    unknown_keys(rep, where, r, set(spec["keys"]) | {"_destroy", "object_type"}, var)
    if op is None:
        if var in ("ProfileStatusRule", "ProfileTypeRule", "ProfileAttributeRuleDate"):
            rep.err(where, "'comparison_operator' is required")
    else:
        enum(rep, where, "comparison_operator", op, spec["operators"])
    v = r.get("value")
    if var == "ProfileStatusRule" and v is not None:
        if v in API["profileStatuses"] and v not in spec["values"]:
            rep.warn(where, f"status '{v}': the spec and guide list {', '.join(spec['values'])} for this rule while "
                            f"profiles use {', '.join(API['profileStatuses'])}; check which the tenant accepts")
        elif v not in spec["values"]:
            enum(rep, where, "value", v, spec["values"])
    if var == "ProfileTypeRule" and isinstance(v, str) and not UUID.match(v):
        rep.err(where, f"value '{v}' must be the profile type id (UUID), not its name")
    if var == "RiskRule":
        enum(rep, where, "secondary_value", r.get("secondary_value"), ["OverallRisk"])


def check_advanced_search(a, where: str, rep: Report) -> None:
    if not isinstance(a, dict):
        rep.err(where, "advanced_search must be an object")
        return
    for wrong in ("condition_rules", "conditions", "rules", "filters"):
        if wrong in a:
            rep.err(where, f"'{wrong}' is not a key here; use 'condition_rules_attributes'")
    rules = a.get("condition_rules_attributes")
    if rules is None:
        rep.err(where, "'condition_rules_attributes' (array of rules) is required")
        return
    if not isinstance(rules, list):
        rep.err(where, "'condition_rules_attributes' must be an array")
        return
    if not rules:
        rep.warn(where, "no rules: the search returns every profile you can see")
    for i, r in enumerate(rules):
        check_rule(r, f"{where}.condition_rules_attributes[{i}]", rep)


def check_workflow_session(w, where: str, rep: Report) -> None:
    ws = API["workflowSession"]
    if not isinstance(w, dict):
        rep.err(where, "workflow_session must be an object")
        return
    for k in ws["required"]:
        if k not in w:
            rep.err(where, f"'{k}' is required to create a workflow session")
    enum(rep, where, "requester_type", w.get("requester_type"), ws["requesterTypes"])
    for k in w:
        if k == "status":
            rep.warn(where, "'status' is set by NERM; to start the session call POST/PATCH with ?run=true")
        elif k not in ws["keys"]:
            rep.warn(where, f"unknown key '{k}'{suggest(k, ws['keys'])}")
    if "profile_id" in w and "profile_ids" in w:
        rep.warn(where, "both profile_id (update workflows) and profile_ids (batch workflows) are set")
    if "profile_ids" in w and not isinstance(w["profile_ids"], list):
        rep.err(where, "'profile_ids' must be an array of profile ids")
    for k in ("workflow_id", "requester_id", "profile_id"):
        if isinstance(w.get(k), str) and not UUID.match(w[k]):
            rep.err(where, f"{k} '{w[k]}' is not a UUID")
    check_attributes(rep, where, w.get("attributes"))


def check_audit(a, where: str, rep: Report) -> None:
    q = API["auditQuery"]
    if not isinstance(a, dict):
        rep.err(where, "audit_events must be an object")
        return
    unknown_keys(rep, where, a, q, "an audit query")
    lim = a.get("limit")
    if lim is not None and (not isinstance(lim, int) or lim < 1 or lim > q["limit"]["maximum"]):
        rep.err(where, f"limit must be an integer 1-{q['limit']['maximum']}")
    enum(rep, where, "order", a.get("order"), q["order"]["enum"])
    f = a.get("filters")
    if f is None:
        return
    if not isinstance(f, dict):
        rep.err(where, "'filters' must be an object")
        return
    unknown_keys(rep, f"{where}.filters", f, API["auditFilterKeys"], "audit filters")
    enum(rep, f"{where}.filters", "subject_type", f.get("subject_type"), API["auditSubjectTypes"])
    enum(rep, f"{where}.filters", "type", f.get("type"), API["auditTypes"])
    ca = f.get("created_at")
    if ca is not None:
        if not isinstance(ca, dict):
            rep.err(f"{where}.filters", "created_at must be an object with gt, lt or eq")
        else:
            for k in ca:
                if k not in ("gt", "lt", "eq"):
                    rep.err(f"{where}.filters.created_at", f"'{k}' is not an operator; use gt, lt or eq")


def check_user(u, where: str, rep: Report) -> None:
    us = API["user"]
    if not isinstance(u, dict):
        rep.err(where, "a user must be an object")
        return
    for k in us["required"]:
        if k not in u:
            rep.err(where, f"'{k}' is required to create a user")
    unknown_keys(rep, where, u, set(us["keys"]) | {"id", "uid"}, "a user")
    enum(rep, where, "type", u.get("type"), us["types"])
    enum(rep, where, "status", u.get("status"), us["statuses"])
    if u.get("type") == "NeprofileUser" and "password" in u:
        rep.warn(where, "password is for portal users (NeaccessUser); lifecycle users sign in through the IdP/ISC")


SHAPES = {
    "profile": lambda v, w, r, mode: check_profile(v, w, r, "patch" if mode == "patch" else "create"),
    "advanced_search": lambda v, w, r, mode: check_advanced_search(v, w, r),
    "workflow_session": lambda v, w, r, mode: check_workflow_session(v, w, r),
    "audit_events": lambda v, w, r, mode: check_audit(v, w, r),
    "user": lambda v, w, r, mode: check_user(v, w, r),
}


def check_body(obj, rep: Report, mode: str = "create") -> None:
    where = "body"
    if isinstance(obj, list):
        rep.err(where, "NERM bodies are objects wrapped in a key, e.g. {\"profiles\": [ ... ]}, not a bare array")
        return
    if not isinstance(obj, dict):
        rep.err(where, "body must be a JSON object")
        return
    if any(k in obj for k in ("sourceId", "accountName")) and "firstName" in obj:
        rep.err(where, "this is an ISC Non-Employee Lifecycle Management record (POST /non-employee-records on "
                       "{tenant}.api.identitynow.com), not a NERM profile")
        return
    if len(obj) == 1:
        key, val = next(iter(obj.items()))
        if key in SHAPES:
            SHAPES[key](val, key, rep, mode)
            return
        if key in ("profiles", "users"):
            if not isinstance(val, list):
                rep.err(key, f"'{key}' must be an array")
                return
            if not val:
                rep.warn(key, "empty array")
            for i, item in enumerate(val):
                if key == "profiles":
                    check_profile(item, f"profiles[{i}]", rep, "bulk_patch" if mode == "patch" else "create")
                else:
                    check_user(item, f"users[{i}]", rep)
            return
    # unwrapped
    hint = None
    if "condition_rules_attributes" in obj:
        hint = "advanced_search"
    elif "workflow_id" in obj and "requester_id" in obj:
        hint = "workflow_session"
    elif "profile_type_id" in obj or ("status" in obj and "attributes" in obj):
        hint = "profile"
    elif "login" in obj and "email" in obj:
        hint = "user"
    elif "filters" in obj and "sort_by" in obj:
        hint = "audit_events"
    if hint:
        rep.err(where, f"body must be wrapped: {{\"{hint}\": {{...}}}} — NERM rejects the bare object")
        SHAPES[hint](obj, hint, rep, mode)
    else:
        rep.err(where, f"unrecognized body; expected one of the wrapper keys: "
                       f"{', '.join(list(SHAPES) + ['profiles', 'users'])}")


# --------------------------------------------------------------------------- URLs and scopes

def match_endpoint(method: str, path: str):
    """Return (key, info) of the spec endpoint matching method+path, or (None, candidates)."""
    segs = [s for s in path.strip("/").split("/") if s]
    best = []
    for key, info in API["endpoints"].items():
        m, p = key.split(" ", 1)
        ps = [s for s in p.strip("/").split("/") if s]
        if len(ps) != len(segs):
            continue
        if all(a == b or (a.startswith("{") and a.endswith("}")) for a, b in zip(ps, segs)):
            best.append((m, key, info))
    for m, key, info in best:
        if m == method:
            return key, info
    return None, sorted({k for _, k, _ in best})


def check_url(spec: str, rep: Report) -> tuple[str, str] | None:
    where = "url"
    parts = spec.strip().split(None, 1)
    if len(parts) != 2:
        rep.err(where, "give it as \"METHOD URL\", e.g. \"GET https://acme.nonemployee.com/api/profiles\"")
        return None
    method, url = parts[0].upper(), parts[1]
    u = urlsplit(url if "://" in url else "https://tenant.nonemployee.com" + (url if url.startswith("/") else "/" + url))
    host, path = u.hostname or "", u.path
    if ISC_NELM.search(path):
        rep.err(where, "non-employee-sources/records/requests/approvals are ISC Non-Employee Lifecycle Management "
                       "endpoints ({tenant}.api.identitynow.com), not NERM; NERM uses /api/profiles, /api/profile_types, ...")
        return None
    if host.endswith("identitynow.com") or host.endswith("sailpoint.com"):
        rep.err(where, f"host '{host}' is ISC; the NERM API is https://{{tenant}}.nonemployee.com/api/...")
    elif host and not host.endswith("nonemployee.com"):
        rep.warn(where, f"host '{host}' is not a *.nonemployee.com tenant")
    if not path.startswith("/api/"):
        rep.err(where, "NERM paths start with /api/ (e.g. /api/profiles)")
        return None
    rest = path[len("/api"):]
    if rest.startswith("/v1/"):
        rep.warn(where, "the v1 spec's base URL is /api with no /v1 segment (/api/profiles); the guide's curl "
                        "examples show /api/v1/... — drop /v1 if the call 404s")
        rest = rest[len("/v1"):]
    key, info = match_endpoint(method, rest)
    if key is None:
        if info:
            rep.err(where, f"{method} is not defined for {rest}; defined: {', '.join(info)}")
        else:
            norm = "/".join("{id}" if UUID.match(s) or s.isdigit() else s for s in rest.split("/"))
            close = difflib.get_close_matches(norm, sorted({k.split(' ', 1)[1] for k in API["endpoints"]}), n=3, cutoff=0.5)
            rep.err(where, f"no NERM endpoint {rest}" + (f"; closest: {', '.join(close)}" if close else ""))
        return None
    params = dict(parse_qsl(u.query, keep_blank_values=True))
    q = info["query"]
    for name, val in params.items():
        if name == "filters":
            rep.err(where, "NERM has no ISC-style filters= expression; filter with plain query parameters "
                           "(?status=Active) or POST /advanced_search/run")
        elif name == "count":
            rep.warn(where, "count=true is an ISC parameter; NERM returns totals with metadata=true (_metadata.total)")
        elif name == "sorters":
            rep.warn(where, "sorters is an ISC parameter; NERM sorts with order=<field>")
        elif name not in q:
            rep.warn(where, f"query parameter '{name}' is not defined for {key}"
                            + (f"; defined: {', '.join(sorted(q))}" if q else ""))
        elif "enum" in q[name]:
            enum(rep, where, name, val, q[name]["enum"])
        elif q[name].get("type") == "integer":
            if not re.fullmatch(r"\d+", val):
                rep.err(where, f"{name} must be an integer")
            elif name == "limit" and int(val) < 1:
                rep.err(where, "limit must be at least 1")
    if key == "GET /profiles":
        if "limit" in params and params["limit"].isdigit() and int(params["limit"]) > PROFILES_LIMIT_MAX:
            rep.err(where, f"limit {params['limit']} exceeds the maximum of {PROFILES_LIMIT_MAX} for /profiles")
        if "after_id" in params:
            if "offset" in params:
                rep.err(where, "after_id cannot be combined with offset (keyset paging sorts by id)")
            extra = sorted(set(params) - AFTER_ID_OK - {"offset"})
            if extra:
                rep.err(where, f"with after_id only profile_type_id, limit and updated_after filters apply; "
                               f"{', '.join(extra)} would be ignored or rejected with 400")
            if params["after_id"] and not UUID.match(params["after_id"]):
                rep.err(where, "after_id must be a profile id (UUID)")
    if key in ("POST /workflow_sessions", "PATCH /workflow_sessions/{id}") and params.get("run") != "true":
        rep.warn(where, "without ?run=true the workflow session is saved but not started")
    return method, key


def access_level(method: str, key: str, resource: str) -> str:
    if resource == "Workflow sessions" and method in ("POST", "PUT", "PATCH"):
        return "X"
    if (resource == "Advanced search" and key.endswith("/run")) or key.endswith("/query"):
        return "R"
    return {"GET": "R", "DELETE": "D"}.get(method, "W")


def check_scopes(scopes: list[str], method: str, key: str, rep: Report) -> None:
    where = "scopes"
    known = API["scopes"]
    for s in scopes:
        if s not in known:
            rep.err(where, f"unknown NERM scope '{s}'{suggest(s, known)}")
    scopes = [s for s in scopes if s in known]
    if not scopes:
        rep.err(where, "the token must carry at least one nerm: scope")
        return
    if "nerm:general:manage" in scopes:
        return
    tag = API["endpoints"][key]["tag"]
    resource = RESOURCE_OF_TAG.get(tag)
    if resource is None:
        rep.warn(where, f"{key} (tag '{tag}') is not in the guide's resource table; it may need nerm:general:manage "
                        "(system configuration)")
        return
    level = access_level(method, key, resource)
    if key.endswith("/query"):
        rep.warn(where, f"{key} is a search sent as POST; the guide maps access by HTTP method (POST = write) but "
                        "the only read access to audit events is this query, so it is treated as read here")
    granting = [s for s in known if level in known[s].get(resource, [])]
    ok = [s for s in scopes if level in known[s].get(resource, [])]
    if ok and "nerm:api:integration-partner" in ok and len(ok) == 1 and key not in ("POST /profile", "POST /profiles"):
        ok = []  # integration-partner may only create profiles
    if not ok:
        need = {"R": "read", "W": "write", "D": "delete", "X": "execute"}[level]
        rep.err(where, f"{key} needs {need} on '{resource}'; none of {', '.join(scopes)} grants it "
                       f"(NERM answers 403). Scopes that do: {', '.join(granting)}")


def main(argv) -> int:
    files, url, scopes, request, mode = [], None, None, None, "create"
    it = iter(argv)
    for a in it:
        if a == "--url":
            url = next(it, None)
        elif a == "--scopes":
            scopes = [s.strip() for s in (next(it, "") or "").split(",") if s.strip()]
        elif a == "--request":
            request = next(it, None)
        elif a == "--patch":
            mode = "patch"
        elif a in ("-h", "--help"):
            print(__doc__)
            return 0
        else:
            files.append(a)
    if not (files or url or scopes):
        print(__doc__)
        return 2
    rep = Report()
    target = None
    if url:
        target = check_url(url, rep)
    if scopes is not None:
        if target is None and request:
            m, _, p = request.partition(" ")
            key, info = match_endpoint(m.upper(), re.sub(r"^/api(/v1)?", "", p.split("?")[0]))
            target = (m.upper(), key) if key else None
            if key is None:
                rep.err("request", f"no NERM endpoint {request}")
        if target:
            check_scopes(scopes, target[0], target[1], rep)
        elif not url:
            rep.err("scopes", "give the call with --request \"METHOD /path\" or --url")
    for f in files:
        try:
            with open(f, encoding="utf-8") as fh:
                obj = json.load(fh)
        except (OSError, ValueError) as e:
            print(f"{f}: cannot read JSON: {e}")
            return 2
        if url and target and target[0] in ("PATCH", "PUT"):
            mode = "patch"
        check_body(obj, rep, mode)
    for e in rep.errors:
        print(f"ERROR   {e}")
    for w in rep.warnings:
        print(f"WARNING {w}")
    print(f"{len(rep.errors)} error(s), {len(rep.warnings)} warning(s)")
    return 1 if rep.errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
