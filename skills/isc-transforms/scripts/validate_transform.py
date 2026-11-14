#!/usr/bin/env python3
"""Static checks for a SailPoint ISC transform JSON. Standard library only.

Usage:  python3 validate_transform.py transform.json [--json]
Exit 0 = no errors, 1 = errors, 2 = unreadable input.

Checks every nested transform against transform_types.json (generated from SailPoint's
operation docs): known type, required attributes present, unknown attributes, `name` only at
the root, conditional/dateCompare syntax, size limit. It cannot evaluate the transform: preview
it on an identity profile (or a real account create) afterwards.
"""
from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "transform_types.json"), encoding="utf-8") as fh:
    _DATA = json.load(fh)
TYPES = _DATA["types"]
RULE_OPS = _DATA["ruleOperations"]
TYPES.setdefault("rule", {"required": ["name"], "optional": ["input"], "doc": "rule"})
# types whose attributes may legitimately carry extra keys (template variables, rule arguments, generator settings)
OPEN_TYPES = {"static", "rule", "usernameGenerator"}
DATE_OPS = {"lt", "lte", "gt", "gte"}
FIELD_TYPES = {"string", "boolean", "int", "long", "date", "secret", "secured"}


class Report:
    def __init__(self):
        self.errors, self.warnings = [], []

    def err(self, w, m):
        self.errors.append(f"{w}: {m}")

    def warn(self, w, m):
        self.warnings.append(f"{w}: {m}")


def is_transform(v) -> bool:
    return isinstance(v, dict) and "type" in v and isinstance(v.get("type"), str)


def check(node, path: str, rep: Report, root: bool) -> None:
    if not is_transform(node):
        rep.err(path, "not a transform object (needs 'type')")
        return
    t = node["type"]
    if root and not node.get("name"):
        rep.err(path, "root transform needs a 'name'")
    if not root and "name" in node and t != "rule":
        rep.warn(path, "nested transforms don't have a 'name' (only the root does)")
    extra_top = set(node) - {"type", "name", "attributes", "requiresPeriodicRefresh", "id", "internal"}
    if extra_top:
        rep.warn(path, f"unexpected top-level keys {sorted(extra_top)} — attributes go inside 'attributes'")
    attrs = node.get("attributes") or {}
    if not isinstance(attrs, dict):
        rep.err(path, "'attributes' must be an object")
        return
    spec = TYPES.get(t)
    if spec is None:
        close = [k for k in TYPES if k.lower() == t.lower()]
        hint = f" (did you mean '{close[0]}'? types are case-sensitive)" if close else ""
        rep.err(path, f"unknown transform type '{t}'{hint}")
    else:
        required = list(spec["required"])
        allowed = set(spec["required"]) | set(spec["optional"])
        if t == "rule" and attrs.get("operation") in RULE_OPS:
            op = RULE_OPS[attrs["operation"]]
            required += op["required"]
            allowed |= set(op["required"]) | set(op["optional"]) | {"operation"}
        for r in required:
            if r not in attrs:
                rep.err(path, f"'{t}' requires attribute '{r}' (see references/operations/{spec['doc']}.md)")
        if t not in OPEN_TYPES:
            for k in attrs:
                if k not in allowed:
                    rep.warn(path, f"attribute '{k}' is not documented for '{t}'")
    # type-specific syntax
    if t == "conditional":
        expr = str(attrs.get("expression", ""))
        if expr and not re.fullmatch(r"\s*\S.*\s+eq\s+.*\S\s*", expr):
            rep.err(path, "conditional expression must be 'ValueA eq ValueB' — 'eq' is the only operator")
        if re.search(r"==|!=|\bne\b|\bgt\b|\blt\b", expr):
            rep.err(path, "conditional supports only 'eq'; use dateCompare, lookup or nested conditionals")
    if t == "dateCompare":
        op = str(attrs.get("operator", "")).lower()
        if op and op not in DATE_OPS:
            rep.err(path, f"dateCompare operator must be one of lt, lte, gt, gte (got '{attrs.get('operator')}')")
        if not node.get("requiresPeriodicRefresh") and "now" in json.dumps(attrs) and root:
            rep.warn(path, "compares with 'now' but requiresPeriodicRefresh is not true: the value won't update nightly")
    if t == "accountAttribute" and "applicationName" in attrs:
        rep.warn(path, "'applicationName' is the old name; current docs use 'sourceName'")
    if t == "static" and "value" in attrs:
        names = set(re.findall(r"\$\{?([A-Za-z_][A-Za-z0-9_]*)", str(attrs["value"])))
        known = set(attrs) | {"identity", "attributeDefinition", "oldValue", "field", "application", "current"}
        for n in names:
            if n not in known and not n.startswith("__"):
                rep.warn(path, f"static value uses '${n}' but no sibling attribute or context variable has that name")
    if t in ("firstValid", "concat") and isinstance(attrs.get("values"), list) and not attrs["values"]:
        rep.err(path, f"'{t}' values list is empty")
    # recurse
    for k, v in attrs.items():
        if is_transform(v):
            check(v, f"{path}.attributes.{k}", rep, False)
        elif isinstance(v, list):
            for i, item in enumerate(v):
                if is_transform(item):
                    check(item, f"{path}.attributes.{k}[{i}]", rep, False)
        elif isinstance(v, dict) and k not in ("table",):
            for k2, v2 in v.items():
                if is_transform(v2):
                    check(v2, f"{path}.attributes.{k}.{k2}", rep, False)


def validate(obj) -> Report:
    rep = Report()
    size = len(json.dumps(obj).encode())
    if size > 400_000:
        rep.err("transform", f"{size} bytes; uploads are limited to 400 KB")
    if isinstance(obj, dict) and isinstance(obj.get("fields"), list):      # whole provisioning policy
        items, label = obj["fields"], "fields"
    else:
        items, label = (obj if isinstance(obj, list) else [obj]), "transform"
    for i, t in enumerate(items):
        where = f"{label}[{i}]" if len(items) > 1 or label == "fields" else label
        if isinstance(t, dict) and "transform" in t and t.get("type") in FIELD_TYPES:
            # create-profile field: {"name": "userName", "type": "string", "transform": {...}}
            if t.get("transform"):
                check(t["transform"], f"{where}.transform", rep, False)
            continue
        check(t, where, rep, True)
    return rep


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    try:
        with open(argv[1], encoding="utf-8") as fh:
            obj = json.load(fh)
    except (OSError, json.JSONDecodeError) as e:
        print(f"ERROR cannot read {argv[1]}: {e}")
        return 2
    rep = validate(obj)
    if "--json" in argv:
        print(json.dumps({"errors": rep.errors, "warnings": rep.warnings}, indent=2))
    else:
        for e in rep.errors:
            print(f"ERROR   {e}")
        for w in rep.warnings:
            print(f"WARNING {w}")
        print(f"{len(rep.errors)} error(s), {len(rep.warnings)} warning(s)")
    return 1 if rep.errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
