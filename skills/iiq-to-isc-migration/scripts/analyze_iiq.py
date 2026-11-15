#!/usr/bin/env python3
"""Analyze an IdentityIQ XML export and produce an IIQ -> ISC migration plan. Standard library only.

Usage:
  python3 analyze_iiq.py export.xml [more.xml | folder ...] [--plan plan.md] [--json]

Input: IIQ XML as exported by the console/Debug pages or the IIQ deployment accelerator — a <sailpoint> file with many
objects, single-object files (<Rule>, <Application>, ...), or a folder of them (searched recursively).

For every object it prints the ISC equivalent and a level (direct / adapt / none, from iiq_mapping.json). For rules
it also detects IIQ APIs that do not exist in ISC (context, SailPointContext, QueryOptions/Filter, sailpoint.api.*,
JDBC/HTTP/file access, rule libraries...) and proposes the ISC replacement; rules that become ISC cloud or connector
rules are passed to ../../isc-cloud-rule-review/scripts/review_rule.py (when installed) with their ISC type, so the
plan shows what SailPoint's review would reject. --plan writes the Markdown plan: inventory, mapping, rules to
rewrite, risks, recommended order.
Exit 0 always for a readable export (it is an analysis), 2 if nothing could be read.
"""
from __future__ import annotations

import collections
import json
import os
import re
import sys
import tempfile
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "iiq_mapping.json"), encoding="utf-8") as fh:
    MAP = json.load(fh)

try:  # sibling skill: SailPoint rule-review checks
    sys.path.insert(0, os.path.join(HERE, "..", "..", "isc-cloud-rule-review", "scripts"))
    import review_rule  # type: ignore
except Exception:  # pragma: no cover - installed alone
    review_rule = None

LEVEL_ORDER = {"direct": 0, "adapt": 1, "none": 2}
# IIQ API usage -> (what it is, ISC replacement)
IIQ_APIS = [
    (r"\bcontext\s*\.\s*getObjectByName\s*\(\s*Identity\.class", "context.getObjectByName(Identity.class, ...)",
     "idn.findIdentitiesBySearchableIdentityAttribute(attr, \"Equals\", value, sortAttr) or idn.getIdentityById(id)"),
    (r"\bcontext\s*\.\s*getObjectById\s*\(\s*Identity\.class", "context.getObjectById(Identity.class, ...)",
     "idn.getIdentityById(id)"),
    (r"\bcontext\s*\.\s*getObject(ByName|ById)?\s*\(\s*Application\.class", "loading an Application",
     "use the 'application' input (where the rule type has it) or the source name 'Name [source]' in idn calls"),
    (r"\bcontext\s*\.\s*getObject(ByName|ById)?\s*\(\s*(Link|Account)\.class", "loading a Link",
     "idn.getAccountByNativeIdentity(appName, nativeIdentity) / idn.getAccountAttribute(...)"),
    (r"\bcontext\s*\.\s*getObject(ByName|ById)?\s*\(\s*ManagedAttribute\.class", "loading a ManagedAttribute",
     "idn.getManagedAttributeDescription(...) / idn.getManagedAttributeDetails(...)"),
    (r"\bcontext\s*\.\s*getObject(ByName|ById)?\s*\(\s*Custom\.class", "reading a Custom object",
     "a transform lookup table, a source/identity attribute, or a value passed in by configuration"),
    (r"\bcontext\s*\.\s*(search|getObjects|countObjects)\s*\(", "context.search/getObjects/countObjects",
     "idn.attrSearchCountAccounts / attrSearchGetIdentityName / countIdentitiesBySearchableIdentityAttribute "
     "(searchable attributes, Equals/StartsWith only)"),
    (r"\bQueryOptions\b|\bFilter\.(eq|like|and|or|in|ignoreCase)\b", "QueryOptions / Filter queries",
     "searchable-attribute idn helpers; no arbitrary queries in ISC rules"),
    (r"\bcontext\s*\.\s*(saveObject|commitTransaction|startTransaction|removeObject|decache|attach)\s*\(",
     "writing to the IIQ database", "not possible in ISC rules: change the plan / return values, or use a workflow"),
    (r"\bcontext\s*\.\s*runRule\s*\(|<ReferencedRules>|\bReferencedRules\b", "rule libraries / runRule",
     "inline the needed methods in the rule (ISC reviews self-contained rules)"),
    (r"\bcontext\s*\.\s*sendEmailNotification\s*\(|\bEmailOptions\b", "sending email from a rule",
     "a workflow Send Email action or a notification template"),
    (r"\bcontext\s*\.\s*getConfiguration\s*\(|\bConfiguration\.class", "reading system configuration",
     "not available in ISC rules"),
    (r"\bcontext\s*\.", "other context.* call", "no context in ISC rules: use idn helpers or rule inputs"),
    (r"\bSailPointContext\b|\bSailPointFactory\b", "SailPointContext / SailPointFactory", "not available in ISC"),
    (r"\bsailpoint\.api\.(Provisioner|Identitizer|Aggregator|IdentityService|Terminator|PasswordPolice|ObjectUtil)\b|"
     r"\bnew\s+(Provisioner|Identitizer|Aggregator|IdentityService|Terminator)\s*\(",
     "IIQ engine classes (Provisioner, Identitizer, Aggregator, ...)",
     "ISC does this itself: identity refresh, provisioning, aggregation APIs or workflows"),
    (r"\b(Hibernate|org\.hibernate|HibernatePersistenceManager)\b", "Hibernate", "not available in ISC"),
    (r"\bDriverManager\b|\bjava\.sql\.(Connection|Statement|PreparedStatement)\b",
     "direct JDBC", "a JDBC source (connector rules get the connection) or move the logic out of ISC"),
    (r"\bHttpURLConnection\b|\bnew\s+URL\s*\(|HttpClient|RestTemplate|\bjava\.net\.",
     "HTTP call", "workflow HTTP Request action, an event trigger to your service, or a Web Services/SaaS connector"),
    (r"\bjava\.io\.(File|FileReader|FileWriter|FileInputStream|FileOutputStream)\b|\bnew\s+File\s*\(",
     "file system access", "not allowed in ISC rules; use a file-based source or an external job"),
    (r"\bWorkflowContext\b|\bwfcontext\b|\bWorkflowLaunch\b|\bWorkflower\b", "workflow engine API",
     "ISC workflows (actions, inline variables) instead of BeanShell"),
    (r"\bSystem\.(out|err)\.", "System.out/err", "log.debug/info"),
    (r"\bThread\b|\bRunnable\b|\.sleep\s*\(", "threads / sleep", "not allowed in ISC rules"),
]
APP_REF_TAGS = set(MAP["applicationRuleRefs"]) - {"buildMapRule", "mergeMapsRule", "preIterativeRule",
                                                  "postIterativeRule", "jdbcProvisionRule"}


def mapping(kind: str, key: str) -> dict:
    table = MAP["ruleTypes"] if kind == "rule" else MAP["objects"]
    return table.get(key) or table["_default"]


def files_of(paths):
    for p in paths:
        if os.path.isdir(p):
            for root, _, names in os.walk(p):
                for n in sorted(names):
                    if n.lower().endswith(".xml"):
                        yield os.path.join(root, n)
        else:
            yield p


def parse(path: str):
    raw = open(path, encoding="utf-8", errors="replace").read()
    xml = re.sub(r"<!DOCTYPE[^>]*>", "", raw)
    root = ET.fromstring(xml.encode("utf-8"))
    objs = list(root) if root.tag == "sailpoint" else [root]
    for el in objs:
        if el.tag in ("ImportAction",):
            objs.extend(list(el))
            continue
        yield el


def rule_findings(code: str) -> list[tuple[str, str]]:
    clean = re.sub(r"/\*.*?\*/", "", code, flags=re.S)
    clean = re.sub(r"//[^\n]*", "", clean)
    out, seen = [], set()
    for pat, what, repl in IIQ_APIS:
        if re.search(pat, clean):
            if what == "other context.* call" and any(w.startswith("context.") or "context" in w for w, _ in out):
                continue
            if what not in seen:
                seen.add(what)
                out.append((what, repl))
    return out


def review_as_isc(el: ET.Element, isc_type: str, name: str) -> list[str]:
    """Run the ISC rule reviewer on the IIQ rule source with the ISC type: list of ERROR codes and messages."""
    if review_rule is None:
        return []
    src = el.find("Source")
    code = src.text if src is not None and src.text else ""
    xml = ("<?xml version='1.0' encoding='UTF-8'?>\n<!DOCTYPE Rule PUBLIC \"sailpoint.dtd\" \"sailpoint.dtd\">\n"
           f"<Rule language=\"beanshell\" name=\"{name}\" type=\"{isc_type}\">\n  <Description>migrated</Description>\n"
           f"  <Source><![CDATA[\n{code}\n  ]]></Source>\n</Rule>\n")
    d = tempfile.mkdtemp()
    f = os.path.join(d, f"Rule - {isc_type} - {name}.xml")
    with open(f, "w", encoding="utf-8") as fh:
        fh.write(xml)
    r = review_rule.review(f)
    return [f"{x.code} {x.msg}" for x in r["findings"]
            if (x.level == "ERROR" or x.code in ("R081", "R082")) and x.code not in ("R006",)]


def analyze(paths) -> dict:
    items, rules_by_name, errors = [], {}, []
    for f in files_of(paths):
        try:
            for el in parse(f):
                items.append((f, el))
                if el.tag == "Rule" and el.get("name"):
                    rules_by_name[el.get("name")] = el
        except (OSError, ET.ParseError) as e:
            errors.append(f"{f}: {e}")
    out = []
    used_by: dict[str, list[str]] = collections.defaultdict(list)
    for f, el in items:
        if el.tag == "Application":
            for child in el:
                if child.tag in APP_REF_TAGS:
                    ref = child.find("Reference")
                    if ref is not None and ref.get("name"):
                        used_by[ref.get("name")].append(f"{el.get('name')} ({child.tag})")
            for entry in el.iter("entry"):
                k, v = entry.get("key"), entry.get("value")
                if k in MAP["applicationRuleRefs"] and v:
                    used_by[v].append(f"{el.get('name')} ({k})")
    for f, el in items:
        tag, name = el.tag, el.get("name") or el.get("displayName") or "(unnamed)"
        rec = {"file": os.path.basename(f), "class": tag, "name": name}
        if tag == "Rule":
            rtype = el.get("type") or "(no type)"
            m = mapping("rule", rtype)
            src = el.find("Source")
            code = (src.text or "") if src is not None else ""
            refs = [r.get("name") for r in el.iter("Reference") if el.find("ReferencedRules") is not None]
            finds = rule_findings(code + ("\n<ReferencedRules>" if el.find("ReferencedRules") is not None else ""))
            rec.update(type=rtype, level=m["level"], isc=m["isc"], why=m["why"], iscRuleType=m.get("iscRuleType"),
                       iiqApis=[{"api": a, "replace": r} for a, r in finds], usedBy=used_by.get(name, []),
                       lines=len(code.strip().split("\n")) if code.strip() else 0, libraries=refs)
            if m.get("iscRuleType") and code.strip():
                rec["reviewErrors"] = review_as_isc(el, m["iscRuleType"], name)
            if m["level"] == "direct" and (finds or rec.get("reviewErrors")):
                rec["level"] = "adapt"
                rec["why"] = (m["why"] + " Code changes needed: IIQ-only APIs or review blockers found.").strip()
        else:
            m = mapping("object", tag)
            rec.update(level=m["level"], isc=m["isc"], why=m["why"])
            if tag == "Application":
                atype = el.get("type") or ""
                rec["type"] = atype
                rec["iscConnector"] = MAP["applicationTypes"].get(atype, MAP["applicationTypes"]["_default"])
                rec["authoritative"] = el.get("authoritative") == "true"
                rec["rules"] = sorted({f"{c.tag}: {c.find('Reference').get('name')}" for c in el
                                       if c.tag in APP_REF_TAGS and c.find("Reference") is not None} |
                                      {f"{e.get('key')}: {e.get('value')}" for e in el.iter("entry")
                                       if e.get("key") in MAP["applicationRuleRefs"] and e.get("value")})
                if rec["iscConnector"].startswith("No logical"):
                    rec["level"], rec["isc"] = "none", rec["iscConnector"]
            elif tag == "Bundle":
                rec["type"] = el.get("type") or ""
                rec["isc"] = ("Access profile (one source) or role" if rec["type"] in ("it", "entitlement")
                              else "Role with membership criteria" if rec["type"] == "business" else m["isc"])
                if el.find(".//IdentitySelector") is not None and el.find(".//RuleRef") is not None:
                    rec["note"] = "assignment by rule: rewrite as membership criteria"
            elif tag == "Policy":
                rec["type"] = el.get("type") or ""
                if rec["type"] and rec["type"] not in ("SOD", "EntitlementSOD", "RoleSOD"):
                    rec["level"] = "none"
                    rec["isc"] = "No equivalent for this policy type: redesign (search + campaign, workflow)"
            elif tag == "Workflow":
                rec["type"] = el.get("type") or ""
                scripts = len(el.findall(".//Script")) + len(el.findall(".//Source"))
                rec["note"] = f"{len(el.findall('Step'))} steps, {scripts} scripts"
            elif tag == "TaskDefinition":
                ex = el.get("executor") or ""
                rec["type"] = ex.rsplit(".", 1)[-1]
                if "RuleExecutor" in ex or "Custom" in ex:
                    rec["level"], rec["isc"] = "none", "Scheduled workflow or an external job using the ISC API"
                elif "ResourceIdentityScan" in ex or "Aggregation" in ex:
                    rec["level"], rec["isc"] = "direct", "Source aggregation schedule"
                elif "IdentityRefresh" in ex:
                    rec["level"], rec["isc"] = "direct", "Not needed: ISC refreshes identities automatically"
        out.append(rec)
    return {"objects": out, "errors": errors}


ORDER = [
    ("1. Sources", lambda r: r["class"] == "Application" or r.get("type") in (
        "BuildMap", "JDBCBuildMap", "SAPBuildMap", "MergeMaps", "PreIterate", "PostIterate", "ResourceIdentityScan"),
     "connector, schema, read-time connector rules, correlation config, then aggregate"),
    ("2. Identity profiles and attributes", lambda r: r["class"] in ("ObjectConfig", "IdentityConfig")
     or r.get("type") in ("IdentityAttribute", "IdentityCreation", "ResourceObjectCustomization"),
     "authoritative sources, attribute mappings, transforms"),
    ("3. Correlation", lambda r: r.get("type") in ("Correlation", "ManagerCorrelation"), "config first, rules only if needed"),
    ("4. Lifecycle", lambda r: r["class"] == "IdentityTrigger" or r.get("type") in ("IdentityAttributeTarget",),
     "lifecycle states, attribute sync"),
    ("5. Provisioning", lambda r: r.get("type") in ("FieldValue", "BeforeProvisioning", "AfterProvisioning", "Integration")
     or (r["class"] == "Rule" and (r.get("iscRuleType") or "") not in ("", "Correlation", "ManagerCorrelation",
                                                                         "IdentityAttribute")),
     "create profiles, generators, BeforeProvisioning, connector rules"),
    ("6. Access model", lambda r: r["class"] in ("Bundle",) or r.get("type") == "IdentitySelector",
     "access profiles, roles, membership criteria"),
    ("7. Requests, workflows, forms, notifications", lambda r: r["class"] in ("Workflow", "Form", "EmailTemplate", "QuickLink")
     or r.get("type") in ("Workflow", "Approver", "AllowedValues", "Validation"), "access request config, workflows, forms"),
    ("8. Policies", lambda r: r["class"] == "Policy" or r.get("type") in ("Policy", "Violation"), "SOD policies"),
    ("9. Certifications", lambda r: r["class"] == "CertificationDefinition" or r.get("type") in ("CertificationExclusion", "Certifier"),
     "campaigns and filters"),
    ("10. Tasks and the rest", lambda r: True, "schedules, custom objects, plugins: redesign"),
]


def plan_md(result: dict) -> str:
    objs = result["objects"]
    lv = collections.Counter(o["level"] for o in objs)
    cls = collections.Counter(o["class"] for o in objs)
    out = ["# IIQ → ISC migration plan", "",
           "Generated by `analyze_iiq.py` (iiq-to-isc-migration skill) from the IdentityIQ export. Levels: **direct** = "
           "same concept with small changes; **adapt** = an ISC equivalent exists but must be rebuilt; **none** = no "
           "equivalent, redesign. Review every line: the analysis is static and does not see your data.", "",
           "## Inventory", "", "| IIQ class | Objects |", "|---|---|"]
    out += [f"| {c} | {n} |" for c, n in sorted(cls.items())]
    out += ["", f"Totals: {len(objs)} objects — direct {lv['direct']}, adapt {lv['adapt']}, none {lv['none']}.", ""]
    out += ["## Mapping", "", "| IIQ object | Class / type | Level | ISC equivalent | Notes |", "|---|---|---|---|---|"]
    for o in sorted(objs, key=lambda o: (o["class"], LEVEL_ORDER[o["level"]], o["name"])):
        notes = []
        if o.get("iscConnector"):
            notes.append(f"connector: {o['iscConnector']}")
        if o.get("authoritative"):
            notes.append("authoritative")
        if o.get("usedBy"):
            notes.append("used by " + ", ".join(o["usedBy"]))
        if o.get("note"):
            notes.append(o["note"])
        if o.get("why"):
            notes.append(o["why"])
        t = f"{o['class']}" + (f" / {o['type']}" if o.get("type") else "")
        out.append(f"| {o['name']} | {t} | {o['level']} | {o['isc']} | {'; '.join(notes).replace('|', '/')} |")
    rules = [o for o in objs if o["class"] == "Rule" and (o.get("iiqApis") or o.get("reviewErrors"))]
    if rules:
        out += ["", "## Rules to rewrite by hand", ""]
        for o in rules:
            out += [f"### {o['name']} ({o['type']} → {o.get('iscRuleType') or o['isc']})", ""]
            for a in o.get("iiqApis", []):
                out.append(f"- uses **{a['api']}** → {a['replace']}")
            if o.get("reviewErrors"):
                out.append("- as an ISC rule, SailPoint's review would reject it for:")
                out += [f"  - {e}" for e in o["reviewErrors"]]
            out.append("")
    none_items = [o for o in objs if o["level"] == "none"]
    out += ["## Risks", ""]
    if none_items:
        out.append(f"- {len(none_items)} object(s) have no ISC equivalent and need a redesign: "
                   + ", ".join(f"{o['name']} ({o['class']}{'/' + o['type'] if o.get('type') else ''})" for o in none_items[:20])
                   + (" …" if len(none_items) > 20 else "") + ".")
    if any(o.get("iscRuleType") and o["class"] == "Rule" and LEVEL_ORDER[o["level"]] <= 1 and
           (MAP["ruleTypes"].get(o.get("type"), {}).get("iscRuleType") in
            {t for t, v in (review_rule.CAT["ruleTypes"].items() if review_rule else []) if v["execution"] == "cloud"})
           for o in objs):
        out.append("- Every ISC cloud rule needs SailPoint's review (Expert Services hours, ~1 business day each): "
                   "prefer transforms and configuration; plan review time before go-live.")
    if any(o.get("libraries") for o in objs):
        out.append("- Rules depend on rule libraries; inline the needed methods (each ISC rule is reviewed on its own).")
    if any(o["class"] == "Workflow" for o in objs):
        out.append("- Workflows are rebuilt, not converted: list the business steps and approvals first.")
    out.append("- ISC refreshes and provisions on events, not on IIQ task schedules: re-test timing-dependent logic.")
    out.append("- Clean up first: retire unused applications, rules and custom objects before migrating them.")
    out += ["", "## Recommended order", ""]
    done = set()
    for title, pred, what in ORDER:
        group = [o for o in objs if id(o) not in done and pred(o)]
        for o in group:
            done.add(id(o))
        if group:
            out.append(f"**{title}** — {what}: " + ", ".join(o["name"] for o in group))
            out.append("")
    if result["errors"]:
        out += ["## Files not read", ""] + [f"- {e}" for e in result["errors"]]
    return "\n".join(out) + "\n"


def main(argv) -> int:
    paths, plan, as_json = [], None, False
    it = iter(argv)
    for a in it:
        if a == "--plan":
            plan = next(it, None)
        elif a == "--json":
            as_json = True
        elif a in ("-h", "--help"):
            print(__doc__)
            return 0
        else:
            paths.append(a)
    if not paths:
        print(__doc__)
        return 2
    res = analyze(paths)
    if not res["objects"]:
        for e in res["errors"]:
            print(f"ERROR {e}")
        print("no IIQ objects found")
        return 2
    if plan:
        with open(plan, "w", encoding="utf-8") as fh:
            fh.write(plan_md(res))
    if as_json:
        print(json.dumps(res, indent=2))
    else:
        for o in res["objects"]:
            t = f"{o['class']}" + (f"/{o['type']}" if o.get("type") else "")
            print(f"{o['level']:6} {t:40} {o['name']}  ->  {o['isc']}")
            for a in o.get("iiqApis", []):
                print(f"         uses {a['api']} -> {a['replace']}")
            for e in o.get("reviewErrors", []):
                print(f"         ISC review would reject: {e}")
        lv = collections.Counter(o["level"] for o in res["objects"])
        print(f"{len(res['objects'])} objects: direct {lv['direct']}, adapt {lv['adapt']}, none {lv['none']}")
        for e in res["errors"]:
            print(f"ERROR {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
