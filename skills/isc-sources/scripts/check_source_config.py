#!/usr/bin/env python3
"""Static checks for SailPoint ISC source configuration JSON. Standard library only.

Usage:  python3 check_source_config.py file.json [more.json ...]
Exit 0 = no errors, 1 = errors, 2 = unreadable input.

Recognizes, by shape:
  * a provisioning policy (create profile etc.)  {"name", "usageType", "fields": [...]}, or a list of them
  * a source object                              {"name", "owner", "connector", ...}  (GET /sources/v1/{id})
  * a source correlation config                  {"attributeAssignments": [...]}
  * a native change detection config             {"enabled", "operations", ...}
  * an aggregation schedule                      {"type", "cronExpression"}

Enums and field names come from source_api.json (generated from SailPoint's OpenAPI spec). Field transforms are
checked with ../isc-transforms/scripts/validate_transform.py when that skill is installed next to this one.
"""
from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "source_api.json"), encoding="utf-8") as fh:
    API = json.load(fh)

try:  # reuse the transform validator from the sibling skill
    sys.path.insert(0, os.path.join(HERE, "..", "..", "isc-transforms", "scripts"))
    import validate_transform as vt  # type: ignore
except Exception:  # pragma: no cover - skill installed alone
    vt = None

SECRET_KEY = re.compile(r"pass(word)?|secret|token|private.?key|credential", re.I)
NCD_OPERATIONS = {"ACCOUNT_CREATED", "ACCOUNT_UPDATED", "ACCOUNT_DELETED"}


class Report:
    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def err(self, where: str, msg: str) -> None:
        self.errors.append(f"{where}: {msg}")

    def warn(self, where: str, msg: str) -> None:
        self.warnings.append(f"{where}: {msg}")


def velocity_names(text: str) -> set[str]:
    return set(re.findall(r"\$!?\{?([A-Za-z_][A-Za-z0-9_]*)", text or ""))


def check_policy(p: dict, where: str, rep: Report) -> None:
    for k in p:
        if k not in API["policyKeys"]:
            rep.warn(where, f"unknown key '{k}' (provisioning policy keys: {', '.join(API['policyKeys'])})")
    if not p.get("name"):
        rep.err(where, "'name' is required")
    ut = p.get("usageType")
    if ut is None:
        rep.warn(where, "no 'usageType' (CREATE for the create profile, UPDATE, ENABLE, DISABLE, ...)")
    elif ut in API.get("usageTypesV2", []):
        if not p.get("subtypeId"):
            rep.warn(where, f"usageType '{ut}' exists only in the v2 (experimental) API and needs a subtypeId")
    elif ut not in API["usageTypes"]:
        close = [u for u in API["usageTypes"] if u.lower() == str(ut).lower()]
        rep.err(where, f"usageType '{ut}' is not valid" + (f" (did you mean '{close[0]}'? values are upper case)"
                                                             if close else f"; one of {', '.join(API['usageTypes'])}"))
    fields = p.get("fields")
    if fields is None:
        rep.warn(where, "no 'fields'")
        return
    if not isinstance(fields, list):
        rep.err(where, "'fields' must be a list")
        return
    names = [f.get("name") for f in fields if isinstance(f, dict)]
    seen: set[str] = set()
    for i, f in enumerate(fields):
        fw = f"{where}.fields[{i}]" + (f" ({f.get('name')})" if isinstance(f, dict) and f.get("name") else "")
        if not isinstance(f, dict):
            rep.err(fw, "field must be an object")
            continue
        for k in f:
            if k not in API["fieldKeys"]:
                rep.warn(fw, f"unknown field key '{k}' (allowed: {', '.join(API['fieldKeys'])})")
        n = f.get("name")
        if not n:
            rep.err(fw, "field needs a 'name' (the account attribute, case-sensitive)")
        elif n in seen:
            rep.err(fw, f"duplicate field '{n}'")
        if f.get("type") not in (None, "") and f["type"] not in API["fieldTypes"]:
            rep.err(fw, f"type '{f['type']}' is not valid; one of {', '.join(API['fieldTypes'])}")
        t = f.get("transform")
        if t is None and f.get("isRequired"):
            rep.warn(fw, "required field without a transform: it only gets a value if a rule or the requester sets it")
        if isinstance(t, dict):
            if vt is not None:
                sub = vt.Report()
                vt.check(t, f"{fw}.transform", sub, False)
                rep.errors += sub.errors
                # static values may reference other fields of the policy: handled below
                rep.warnings += [w for w in sub.warnings if "static value uses" not in w]
            for node in iter_transforms(t):
                if node.get("type") == "static":
                    for ref in velocity_names(str((node.get("attributes") or {}).get("value", ""))):
                        if ref in seen:
                            continue
                        if ref in names:
                            rep.err(fw, f"static value uses '${ref}', but field '{ref}' comes later: fields are "
                                        "computed in list order, move it above")
                        elif ref not in (node.get("attributes") or {}) and ref not in ("identity", "field", "application"):
                            rep.warn(fw, f"static value uses '${ref}', which is neither an earlier field nor a sibling "
                                         "attribute of the static transform")
            gen = (t.get("attributes") or {}) if t.get("type") == "usernameGenerator" else {}
            for pattern in gen.get("patterns", []) if isinstance(gen.get("patterns"), list) else []:
                for ref in velocity_names(str(pattern)):
                    if ref in names and ref not in gen:
                        rep.warn(fw, f"usernameGenerator pattern uses '${ref}': define it as an attribute of the "
                                     "generator (patterns cannot read other create-profile fields)")
        if n:
            seen.add(n)
    if p.get("usageType") == "CREATE" and not any(
            isinstance(f, dict) and f.get("name") in ("sAMAccountName", "distinguishedName", "userName", "username",
                                                      "uid", "id", "name", "email", "login", "accountId") for f in fields):
        rep.warn(where, "CREATE policy without an obvious account identifier field: check the source's account "
                        "schema identity attribute is generated here")


def iter_transforms(node):
    if isinstance(node, dict):
        if isinstance(node.get("type"), str):
            yield node
        for v in node.values():
            yield from iter_transforms(v)
    elif isinstance(node, list):
        for v in node:
            yield from iter_transforms(v)


def check_source(s: dict, where: str, rep: Report) -> None:
    for k in API["sourceRequired"]:
        if not s.get(k):
            rep.err(where, f"'{k}' is required")
    for k in s:
        if k not in API["sourceKeys"]:
            rep.warn(where, f"unknown key '{k}' for a source object")
    owner = s.get("owner")
    if isinstance(owner, dict) and owner.get("type") not in (None, "IDENTITY"):
        rep.err(where, "owner.type must be IDENTITY")
    feats = s.get("features") or []
    for f in feats:
        if f not in API["features"]:
            rep.err(where, f"unknown feature '{f}'")
    if feats:
        rep.warn(where, "'features' is set: SailPoint advises not to change it for SailPoint-supported connectors")
    dt = s.get("deleteThreshold")
    if dt is not None and not (isinstance(dt, int) and 0 <= dt <= 100):
        rep.err(where, f"deleteThreshold must be an integer 0-100 (a percentage), got {dt!r}")
    st = s.get("status")
    if st is not None and st not in API["sourceStatuses"]:
        rep.err(where, f"unknown status '{st}'")
    acc = s.get("accountCorrelationConfig")
    if isinstance(acc, dict) and acc.get("type") not in (None, "ACCOUNT_CORRELATION_CONFIG"):
        rep.err(where, "accountCorrelationConfig.type must be ACCOUNT_CORRELATION_CONFIG")
    if s.get("accountCorrelationConfig") and s.get("accountCorrelationRule"):
        rep.warn(where, "both accountCorrelationConfig and accountCorrelationRule are set: the rule is for complex cases only")
    for key, val in (s.get("connectorAttributes") or {}).items():
        if SECRET_KEY.search(key) and isinstance(val, str) and val and not val.startswith(("2:", "1:", "$")) \
                and "encrypted" not in key.lower():
            rep.warn(where, f"connectorAttributes.{key} looks like a plain-text secret: never commit it; "
                            "ISC encrypts it when set through the UI or API")


def check_correlation(c: dict, where: str, rep: Report) -> None:
    for i, a in enumerate(c.get("attributeAssignments") or []):
        aw = f"{where}.attributeAssignments[{i}]"
        if a.get("operation") not in (None, "EQ"):
            rep.err(aw, f"operation '{a.get('operation')}' not supported: correlation only does EQ")
        if a.get("matchMode") not in (None, "ANYWHERE", "START", "END"):
            rep.err(aw, f"matchMode must be ANYWHERE, START or END")
        if not a.get("property") or not a.get("value"):
            rep.err(aw, "needs 'property' and 'value'")


def check_ncd(c: dict, where: str, rep: Report) -> None:
    ops = c.get("operations") or []
    for o in ops:
        if o not in NCD_OPERATIONS:
            rep.err(where, f"unknown operation '{o}' (ACCOUNT_CREATED, ACCOUNT_UPDATED, ACCOUNT_DELETED)")
    if c.get("enabled") and not ops:
        rep.err(where, "enabled without operations: no Native Change triggers will fire")
    if c.get("enabled") and not (c.get("allEntitlements") or c.get("allNonEntitlementAttributes")
                                 or c.get("selectedEntitlements") or c.get("selectedNonEntitlementAttributes")):
        rep.err(where, "enabled without any attribute selected: no Native Change triggers will fire")


def check_schedule(c: dict, where: str, rep: Report) -> None:
    if c.get("type") not in API["scheduleTypes"]:
        rep.err(where, f"schedule type must be one of {', '.join(API['scheduleTypes'])}")
    parts = str(c.get("cronExpression", "")).split()
    if len(parts) not in (6, 7):
        rep.err(where, "cronExpression must be a Quartz cron (6 or 7 fields, seconds first), e.g. '0 0 5,13,21 * * ?'")
    elif parts[3] != "?" and parts[5] != "?":
        rep.err(where, "Quartz cron needs '?' in day-of-month or day-of-week")


def check(obj, rep: Report) -> None:
    items = obj if isinstance(obj, list) else [obj]
    for i, o in enumerate(items):
        w = f"[{i}]" if isinstance(obj, list) else "root"
        if not isinstance(o, dict):
            rep.err(w, "expected a JSON object")
        elif "fields" in o or "usageType" in o:
            check_policy(o, f"{w} policy '{o.get('name', '?')}'", rep)
        elif "connector" in o or "connectorAttributes" in o:
            check_source(o, f"{w} source '{o.get('name', '?')}'", rep)
        elif "attributeAssignments" in o:
            check_correlation(o, f"{w} correlation", rep)
        elif "operations" in o and "enabled" in o:
            check_ncd(o, f"{w} native change detection", rep)
        elif "cronExpression" in o:
            check_schedule(o, f"{w} schedule", rep)
        else:
            rep.warn(w, "not recognized (policy, source, correlation config, NCD config or schedule)")
    if isinstance(obj, list):
        uts = [o.get("usageType") for o in obj if isinstance(o, dict) and o.get("usageType")]
        dup = {u for u in uts if uts.count(u) > 1}
        if dup and not any(isinstance(o, dict) and o.get("subtypeId") for o in obj):
            rep.warn("list", f"several policies with usageType {sorted(dup)}: the v1 API keys policies by usageType "
                             "(one each); only the v2 API (experimental, subtypes) allows more")


def main(argv) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    failed = False
    for path in argv[1:]:
        try:
            with open(path, encoding="utf-8") as fh:
                obj = json.load(fh)
        except (OSError, json.JSONDecodeError) as e:
            print(f"{path}: cannot read JSON: {e}")
            return 2
        rep = Report()
        check(obj, rep)
        for e in rep.errors:
            print(f"  ERROR   {e}")
        for w in rep.warnings:
            print(f"  WARNING {w}")
        print(f"{path}: {'FAIL' if rep.errors else 'OK'} ({len(rep.errors)} error(s), {len(rep.warnings)} warning(s))")
        failed |= bool(rep.errors)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
