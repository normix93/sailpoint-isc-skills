#!/usr/bin/env python3
"""Static checks for a SailPoint ISC workflow JSON (export / API body). Standard library only.

Usage:  python3 validate_workflow.py workflow.json [--json]
Exit code 0 = no errors (warnings allowed), 1 = errors found, 2 = unreadable input.

It checks structure, not behaviour: a clean result means the definition is well formed and the
references resolve, not that the actions will succeed in a tenant. Test there before enabling.
"""
from __future__ import annotations

import json
import re
import sys

# Action IDs seen in SailPoint's public examples and spec. Unknown IDs are only a warning:
# the tenant's list is GET /workflow-library/v1/actions.
KNOWN_ACTIONS = {
    "sp:get-identity", "sp:get-identities", "sp:get-accounts", "sp:manage-account", "sp:access:get",
    "sp:access:manage", "sp:http", "sp:send-email", "sp:forms", "sp:interactive-form",
    "sp:interactive-message", "sp:sleep", "sp:snow", "sp:create-campaign", "sp:loop:iterator",
    "sp:operator-success",
}
KNOWN_EVENT_TRIGGERS = {
    "idn:access-request-pre-approval", "idn:access-request-post-approval", "idn:access-request-dynamic-approver",
    "idn:account-aggregation-completed", "idn:aggregation-accounts-collected", "idn:account-attributes-changed",
    "idn:account-correlated", "idn:identity-created", "idn:identity-attributes-changed", "idn:post-provisioning",
    "idn:campaign-activated", "idn:campaign-generated", "idn:campaign-ended", "idn:certification-signed-off",
    "idn:saved-search-complete", "idn:source-created", "idn:source-updated", "idn:source-deleted",
    "idn:va-cluster-status-change", "sp:form-submitted", "idn:interactive-process-launched",
}
END_TYPES = {"success", "failure"}
STEP_TYPES = {"action", "choice", "success", "failure", "mutation"}
INLINE = re.compile(r"\{\{(.*?)\}\}")
STEP_REF = re.compile(r"\$\.([A-Za-z_][A-Za-z0-9_]*)")
RESERVED_ROOTS = {"trigger", "loop", "now", "error"}
SECRET_KEYS = re.compile(r"(secret|password|token|apikey|api_key)$", re.I)


def technical_name(step_name: str) -> str:
    """'HTTP Request' -> 'hTTPRequest', 'Get Identity 1' -> 'getIdentity1' (lowerCamelCase of the words)."""
    words = re.findall(r"[A-Za-z0-9]+", step_name)
    if not words:
        return step_name
    first = words[0][0].lower() + words[0][1:]
    return first + "".join(w[0].upper() + w[1:] for w in words[1:])


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def err(self, where: str, msg: str) -> None:
        self.errors.append(f"{where}: {msg}")

    def warn(self, where: str, msg: str) -> None:
        self.warnings.append(f"{where}: {msg}")


def walk_strings(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk_strings(v, f"{path}.{k}" if path else k)
            if isinstance(k, str):
                yield f"{path}.{k}" if path else k, k, v
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_strings(v, f"{path}[{i}]")


def check_values(where: str, attrs, known_names: set[str], rep: Report) -> None:
    """JSONPath keys, inline variables, step references, secrets."""
    for path, key, value in walk_strings(attrs):
        if key.endswith(".$"):
            if value in ("", None):
                rep.warn(where, f"'{path}' is empty; remove the key or give it a JSONPath")
            elif not isinstance(value, str) or not value.strip().startswith("$"):
                rep.err(where, f"'{path}' ends with '.$' so its value must be a JSONPath starting with '$' (got {value!r})")
            else:
                check_refs(where, path, value, known_names, rep)
        elif isinstance(value, str):
            if value.strip().startswith("$.") and not INLINE.search(value) and key not in ("body", "query", "message"):
                rep.warn(where, f"'{path}' looks like a JSONPath but the key has no '.$' suffix, so it is sent as literal text")
            for expr in INLINE.findall(value):
                e = expr.strip()
                if not e.startswith("$"):
                    rep.err(where, f"inline variable '{{{{{expr}}}}}' in '{path}' must start with '$'")
                elif "{{" in e or "}}" in e:
                    rep.err(where, f"nested braces in '{path}'")
                else:
                    check_refs(where, path, e, known_names, rep)
            if value.count("{{") != value.count("}}"):
                rep.err(where, f"unbalanced '{{{{ }}}}' in '{path}'")
        if SECRET_KEYS.search(key.replace(".$", "")) and isinstance(value, str) and value and not value.startswith("$") \
                and "%%" not in value and value not in ("<client secret>", "xxx"):
            rep.warn(where, f"'{path}' contains what looks like a secret; use sensitive headers / Parameter Storage and never share it in exported JSON")


def check_refs(where: str, path: str, expr: str, known_names: set[str], rep: Report) -> None:
    for root in STEP_REF.findall(expr):
        if root in RESERVED_ROOTS or root in known_names:
            continue
        if root[0].isupper() or " " in root:
            rep.err(where, f"'{path}' references '$.{root}': use the step's technical name (lowerCamelCase), not its display name")
        else:
            rep.warn(where, f"'{path}' references '$.{root}', which is not the technical name of any step in this workflow "
                            f"(known: {', '.join(sorted(known_names)) or 'none'})")


def check_steps(steps: dict, start: str | None, scope: str, rep: Report, known_names: set[str], in_loop: bool) -> None:
    if not isinstance(steps, dict) or not steps:
        rep.err(scope, "'steps' must be a non-empty object")
        return
    if start not in steps:
        rep.err(scope, f"start step '{start}' is not defined in steps")
    edges: dict[str, list[str]] = {}
    has_action = False
    for name, s in steps.items():
        where = f"{scope} > step '{name}'"
        if not isinstance(s, dict):
            rep.err(where, "step must be an object")
            continue
        stype = str(s.get("type", "")).lower()
        if stype not in STEP_TYPES:
            rep.err(where, f"unknown type '{s.get('type')}' (expected action, choice, Mutation, success, failure)")
        targets: list[str] = []
        if stype == "action":
            has_action = True
            aid = s.get("actionId")
            if not aid:
                rep.err(where, "action step without 'actionId'")
            elif aid not in KNOWN_ACTIONS:
                rep.warn(where, f"actionId '{aid}' not in the known list — confirm it with GET /workflow-library/v1/actions")
            if aid == "sp:loop:iterator":
                attrs = s.get("attributes", {})
                if "input.$" not in attrs and "input" not in attrs:
                    rep.err(where, "loop without 'input.$' (the array to iterate)")
                inner = attrs.get("steps", {})
                inner_names = known_names | {technical_name(n) for n in inner}
                check_steps(inner, attrs.get("start"), f"{where} (loop body)", rep, inner_names, True)
                for k in ("context.$",):
                    if k not in attrs:
                        rep.warn(where, "loop has no 'context.$': steps inside can only read $.loop.loopInput")
        if stype in END_TYPES:
            if s.get("nextStep"):
                rep.err(where, "end step must not have 'nextStep'")
            if stype == "failure" and not s.get("failureName"):
                rep.warn(where, "failure step without 'failureName' (required in the UI)")
        elif stype == "choice":
            cl = s.get("choiceList")
            if not isinstance(cl, list) or not cl:
                rep.err(where, "choice step needs a non-empty 'choiceList'")
                cl = []
            for i, c in enumerate(cl):
                if not c.get("nextStep"):
                    rep.err(where, f"choiceList[{i}] has no 'nextStep'")
                else:
                    targets.append(c["nextStep"])
                if not c.get("comparator"):
                    rep.err(where, f"choiceList[{i}] has no 'comparator'")
            if not s.get("defaultStep"):
                rep.err(where, "choice step needs 'defaultStep'")
            else:
                targets.append(s["defaultStep"])
        elif stype in ("action", "mutation"):
            if not s.get("nextStep"):
                rep.err(where, "missing 'nextStep' (every step except end steps must point to the next one)")
            else:
                targets.append(s["nextStep"])
        for t in targets:
            if t not in steps:
                rep.err(where, f"points to '{t}', which is not a step in this {'loop body' if in_loop else 'workflow'}")
        edges[name] = [t for t in targets if t in steps]
        check_values(where, {k: v for k, v in s.items() if k not in ("steps",)} if stype != "action" or s.get("actionId") != "sp:loop:iterator"
                     else {k: v for k, v in s.get("attributes", {}).items() if k != "steps"}, known_names, rep)
    if not in_loop and not has_action:
        rep.err(scope, "a workflow needs at least one action")
    # reachability and termination
    seen, stack = set(), [start] if start in steps else []
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        stack.extend(edges.get(n, []))
    for n in steps:
        if n not in seen:
            rep.warn(f"{scope} > step '{n}'", "unreachable from the start step")
    ends = {n for n, s in steps.items() if isinstance(s, dict) and str(s.get("type", "")).lower() in END_TYPES}
    if not ends:
        rep.err(scope, "no success/failure end step")
    can_end = set(ends)
    changed = True
    while changed:
        changed = False
        for n, outs in edges.items():
            if n not in can_end and any(o in can_end for o in outs):
                can_end.add(n)
                changed = True
    for n in seen:
        if n not in can_end:
            rep.err(f"{scope} > step '{n}'", "no path from this step reaches a success/failure step (loop or dead end)")


def check_trigger(trig, rep: Report) -> None:
    if not isinstance(trig, dict):
        rep.err("trigger", "missing trigger object")
        return
    ttype = trig.get("type")
    attrs = trig.get("attributes") or {}
    if ttype not in ("EVENT", "SCHEDULED", "EXTERNAL"):
        rep.err("trigger", f"type must be EVENT, SCHEDULED or EXTERNAL (got {ttype!r})")
    if ttype == "EVENT":
        tid = attrs.get("id")
        if not tid:
            rep.err("trigger", "EVENT trigger without attributes.id")
        elif tid not in KNOWN_EVENT_TRIGGERS:
            rep.warn("trigger", f"trigger id '{tid}' not in the known list — confirm with GET /workflow-library/v1/triggers")
        flt = attrs.get("filter.$")
        if flt:
            if not flt.strip().startswith("$"):
                rep.err("trigger", "filter.$ must be a JSONPath starting with '$'")
            if flt.count("(") != flt.count(")") or flt.count("[") != flt.count("]"):
                rep.err("trigger", "unbalanced brackets in filter.$")
            fd = attrs.get("filterDefinition") or {}
            if len(fd.get("conditions", [])) > 5:
                rep.err("trigger", "basic-mode filterDefinition allows at most 5 conditions")
            if re.search(r"\bAND\b|\bOR\b", flt):
                rep.err("trigger", "filters use && and ||, not AND/OR")
        mode = trig.get("mode")
        if mode == "basic" and not attrs.get("filterDefinition"):
            rep.err("trigger", "mode 'basic' requires attributes.filterDefinition")
        if mode == "advanced" and attrs.get("filterDefinition"):
            rep.err("trigger", "mode 'advanced' must not include filterDefinition")
        if tid == "sp:form-submitted" and not (attrs.get("formDefinitionId") or flt):
            rep.err("trigger", "sp:form-submitted needs formDefinitionId or filter.$")
    if ttype == "SCHEDULED":
        freq = attrs.get("frequency")
        if freq not in ("daily", "weekly", "monthly", "yearly", "cronSchedule"):
            rep.err("trigger", f"scheduled frequency must be daily, weekly, monthly, yearly or cronSchedule (got {freq!r})")
        cron = attrs.get("cronString")
        if freq == "cronSchedule" and not cron:
            rep.err("trigger", "cronSchedule needs cronString")
        if cron:
            parts = cron.split()
            if len(parts) != 5:
                rep.err("trigger", f"cronString must have 5 fields (got {len(parts)})")
            elif parts[0] not in ("0", "*") and freq == "cronSchedule":
                rep.warn("trigger", "cron schedules support hours only; a non-zero minute field is not honoured")
        if not attrs.get("timeZone"):
            rep.warn("trigger", "no timeZone set for the scheduled trigger")


def validate(wf) -> Report:
    rep = Report()
    if isinstance(wf, list):
        wf = wf[0] if wf else {}
    if not isinstance(wf, dict):
        rep.err("workflow", "top level must be a JSON object")
        return rep
    if "formElements" in wf or "formInput" in wf or "formConditions" in wf:
        rep.err("workflow", "this looks like a form definition, not a workflow (forms are managed under /form-definitions)")
        return rep
    if not wf.get("name"):
        rep.warn("workflow", "no 'name' (required when creating through the API)")
    if wf.get("enabled") is True:
        rep.warn("workflow", "'enabled' is true: workflows must be created disabled; enable after testing")
    size = len(json.dumps(wf).encode())
    if size > 400_000:
        rep.err("workflow", f"definition is {size} bytes; the maximum is 400 KB")
    check_trigger(wf.get("trigger"), rep)
    d = wf.get("definition") or {}
    steps = d.get("steps", {})
    names = {technical_name(n) for n in steps} if isinstance(steps, dict) else set()
    check_steps(steps, d.get("start"), "definition", rep, names, False)
    for path, key, value in walk_strings(wf):
        if isinstance(value, str) and re.search(r"/(beta|v3|v20\d\d)/", value) and "identitynow" in value:
            rep.warn(path, "calls a legacy API path; prefer the per-service path (see the isc-api skill versioning map)")
    return rep


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    try:
        with open(argv[1], encoding="utf-8") as fh:
            wf = json.load(fh)
    except (OSError, json.JSONDecodeError) as e:
        print(f"ERROR cannot read {argv[1]}: {e}")
        return 2
    rep = validate(wf)
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
