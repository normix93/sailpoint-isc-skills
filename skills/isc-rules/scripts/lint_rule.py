#!/usr/bin/env python3
"""Lint a SailPoint ISC rule (cloud rule XML, connector-rule JSON, or a bare BeanShell file).

Usage:  python3 lint_rule.py "Rule - IdentityAttribute - Calculate Lifecycle.xml" [--json]
Exit 0 = no errors, 1 = errors, 2 = unreadable input.

Checks SailPoint's forbidden-code list (forbidden_tokens.json, generated from the docs), the rule
type, file naming, CDATA, logging and a few review-guideline smells. It does not run the rule:
use the Rule Development Kit for that, and remember cloud rules still go through SailPoint review.
"""
from __future__ import annotations

import json
import os
import re
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "forbidden_tokens.json"), encoding="utf-8") as fh:
    FORBIDDEN = json.load(fh)["tokens"]

CLOUD_TYPES = {"IdentityAttribute", "AttributeGenerator", "AttributeGeneratorFromTemplate", "Correlation",
               "ManagerCorrelation", "BeforeProvisioning", "Transform", "BuildMap"}
CONNECTOR_TYPES = {"ConnectorBeforeCreate", "ConnectorBeforeModify", "ConnectorBeforeDelete", "ConnectorAfterCreate",
                   "ConnectorAfterModify", "ConnectorAfterDelete", "JDBCBuildMap", "JDBCProvision", "SAPBuildMap",
                   "SapHrOperationProvisioning", "WebServiceBeforeOperationRule", "WebServiceAfterOperationRule",
                   "BuildMap"}
DEPRECATED = {"CertificationExclusion": "use campaign filters", "IdentitySelector": "use role assignment criteria",
              "Integration": "use a BeforeProvisioning rule"}
SENSITIVE = re.compile(r"(password|secret|token|ssn|apikey|api_key)", re.I)


def strip_comments(code: str) -> str:
    code = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), code, flags=re.S)
    return re.sub(r"//[^\n]*", "", code)


def load(path: str):
    raw = open(path, encoding="utf-8").read()
    s = raw.lstrip()
    if s.startswith("{"):
        obj = json.loads(raw)
        return "json", obj.get("type"), obj.get("name"), (obj.get("sourceCode") or {}).get("script", ""), obj
    if s.startswith("<"):
        xml = re.sub(r"<!DOCTYPE[^>]*>", "", raw)
        root = ET.fromstring(xml)
        src = root.find("Source")
        return "xml", root.get("type"), root.get("name"), (src.text if src is not None else "") or "", raw
    return "bsh", None, None, raw, raw


def lint(path: str) -> dict:
    errors, warnings = [], []
    try:
        kind, rtype, name, code, raw = load(path)
    except (OSError, ValueError, ET.ParseError) as e:
        return {"fatal": f"cannot parse {path}: {e}"}
    if kind != "bsh":
        if not rtype:
            errors.append("rule has no type")
        elif rtype in DEPRECATED:
            errors.append(f"rule type '{rtype}' is deprecated in ISC: {DEPRECATED[rtype]}")
        elif rtype not in CLOUD_TYPES | CONNECTOR_TYPES:
            errors.append(f"'{rtype}' is not a supported ISC rule type")
        if not name:
            errors.append("rule has no name")
    if kind == "xml":
        base = os.path.basename(path)
        if rtype and name and base != f"Rule - {rtype} - {name}.xml":
            warnings.append(f"cloud-rule submissions should be named 'Rule - {rtype} - {name}.xml' (is '{base}')")
        if "<![CDATA[" not in raw:
            warnings.append("put the code inside <Source><![CDATA[ ... ]]></Source>")
        if re.search(r"&amp;|&lt;|&gt;", raw.split("<Source>")[-1]):
            errors.append("URL/XML-encoded characters (&amp; &lt; &gt;) in the source: convert them before submitting")
        if rtype in CONNECTOR_TYPES - CLOUD_TYPES:
            warnings.append("connector rules are deployed with POST /connector-rules/v1 (JSON with escaped script), not as XML review submissions")
    if kind == "json" and isinstance(raw, dict):
        if rtype in CLOUD_TYPES - CONNECTOR_TYPES:
            warnings.append("cloud rules can't be created through /connector-rules; submit the XML for SailPoint review")
        sig = raw.get("signature")
        if not isinstance(sig, dict) or "input" not in sig:
            warnings.append("connector rule JSON should include a 'signature' with 'input' (and 'output')")
    clean = strip_comments(code)
    lines = clean.split("\n")
    for tok in FORBIDDEN:
        pat = re.escape(tok[:-1] if tok.endswith("()") else tok)   # ".getObjectByName()" -> ".getObjectByName("
        if re.match(r"^[A-Za-z]", tok):
            pat = r"(?<![A-Za-z0-9_])" + pat
        for n, line in enumerate(lines, 1):
            if re.search(pat, line):
                errors.append(f"line {n}: forbidden code '{tok}'")
                break
    if re.search(r"\blog\.(error)\(", clean) and not re.search(r"catch\s*\(", clean):
        warnings.append("log.error used outside error handling: use log.debug/info for informational messages")
    for n, line in enumerate(lines, 1):
        if re.search(r"\blog\.\w+\(", line) and SENSITIVE.search(line):
            errors.append(f"line {n}: logging something that looks sensitive (password/secret/token) is a rejection reason")
        if re.search(r"(password|secret|apikey)\s*=\s*\"[^\"]+\"", line, re.I):
            errors.append(f"line {n}: hard-coded credential")
    if re.search(r"\bfor\s*\(.*(getLinks|getAccounts|getIdentities|findIdentities)", clean):
        warnings.append("iterating over accounts/identities causes cache bloat; use an idn helper or a projection")
    if "catch" in clean and re.search(r"catch\s*\([^)]*\)\s*\{\s*\}", clean):
        warnings.append("empty catch block swallows errors")
    if rtype in ("Correlation", "ManagerCorrelation") and "identityAttributeName" not in clean:
        warnings.append(f"{rtype} rules return a Map with 'identityAttributeName' and 'identityAttributeValue'")
    if not re.search(r"[;{]", clean):
        warnings.append("rule body is empty (template only)")
    elif rtype in ("IdentityAttribute", "AttributeGenerator", "AttributeGeneratorFromTemplate", "Transform") \
            and not re.search(r"\breturn\b", clean):
        errors.append(f"{rtype} rules must return a value")
    if rtype == "BeforeProvisioning" and re.search(r"\breturn\s+[^;\s]", clean):
        warnings.append("BeforeProvisioning rules have no output: modify 'plan' in place")
    if re.search(r"(?m)^\s*//\s*(TODO|FIXME)", code) or re.search(r"(?s)/\*.*?(;|\bif\b).*?\*/", code):
        warnings.append("remove TODOs and commented-out code before review")
    errors.sort(key=lambda e: int(re.match(r"line (\d+)", e).group(1)) if e.startswith("line ") else 0)
    return {"errors": errors, "warnings": warnings, "type": rtype, "name": name}


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    r = lint(argv[1])
    if "fatal" in r:
        print("ERROR " + r["fatal"])
        return 2
    if "--json" in argv:
        print(json.dumps(r, indent=2))
    else:
        print(f"Rule: {r['name']}  type: {r['type']}")
        for e in r["errors"]:
            print(f"ERROR   {e}")
        for w in r["warnings"]:
            print(f"WARNING {w}")
        print(f"{len(r['errors'])} error(s), {len(r['warnings'])} warning(s)")
    return 1 if r["errors"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
