#!/usr/bin/env python3
"""Pre-submission review of a SailPoint ISC rule against SailPoint's rule guidelines. Standard library only.

Usage:
  python3 review_rule.py "Rule - IdentityAttribute - Calculate Lifecycle.xml" [more files]
  python3 review_rule.py rule.xml --report review.md     # also write a Markdown report to attach to the ticket
  python3 review_rule.py rule.xml --json                 # machine-readable findings
  python3 review_rule.py --codes                         # list every check with the guideline it comes from

Exit 0 = no ERROR (nothing SailPoint's review is documented to reject), 1 = at least one ERROR, 2 = unreadable.

Accepts a cloud-rule XML (what you attach to the review ticket), a connector-rule JSON (POST /connector-rules/v1 body)
or a bare BeanShell file (give --type). ERROR = breaks a documented rule (forbidden code, wrong type, required
standard); WARNING = review-guideline or best-practice issue that slows the review or is a likely rejection. It does
not run the rule and cannot prove it works: SailPoint's review does not check that either, so test it first.

Data: rule_catalog.json (rule types, inputs/outputs, IdnRuleUtil methods; generated from developer.sailpoint.com) and
../../isc-rules/scripts/forbidden_tokens.json (SailPoint's code-restriction list) when isc-rules is installed next to it.
"""
from __future__ import annotations

import json
import os
import re
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "rule_catalog.json"), encoding="utf-8") as fh:
    CAT = json.load(fh)
_FT = os.path.join(HERE, "..", "..", "isc-rules", "scripts", "forbidden_tokens.json")
if os.path.exists(_FT):
    with open(_FT, encoding="utf-8") as fh:
        FORBIDDEN = json.load(fh)["tokens"]
else:  # pragma: no cover - installed without isc-rules: keep the most important ones
    FORBIDDEN = ["context.", ".getObjectById()", ".getObjectByName()", ".getObject()", ".search()", ".countObjects()",
                 ".toXml()", "System.out.", "System.err.", "Thread", "Runnable", ".sleep()", "SailpointFactory",
                 "Runtime.", "ProcessBuilder", "exec(", "Logger.getLogger", "Log4j", ".printStackTrace", "public static"]

G = CAT["guidelinesPage"]
C = CAT["cloudRulesPage"]
U = CAT["idnRuleUtilPage"]
CHECKS = {
    # code: (level, title, source)
    "R001": ("ERROR", "file is not a readable rule (XML/JSON/BeanShell)", G),
    "R002": ("WARNING", "missing XML declaration or sailpoint.dtd DOCTYPE of SailPoint's template", C),
    "R003": ("ERROR", "rule has no type", f"{G}#rule-guidelines (annotate the rule with the correct type)"),
    "R004": ("ERROR", "type is not a supported ISC rule type", f"{G}#rule-guidelines (Supported Rules)"),
    "R005": ("ERROR", "type is deprecated in ISC", f"{G}#deprecated-rules"),
    "R006": ("WARNING", "connector rule submitted as a cloud-rule XML", f"{G}#rule-execution; connector rules use /connector-rules/v1"),
    "R007": ("ERROR", "rule has no name", C),
    "R008": ("ERROR", "language is not beanshell", f"{G}#java-beanshell"),
    "R010": ("WARNING", "file name is not 'Rule - {type} - {name}.xml'", f"{C}#review-guidelines (Rule File Naming)"),
    "R011": ("WARNING", "missing or empty <Description>", f"{C}#review-guidelines (Documentation)"),
    "R012": ("ERROR", "no rule source code", C),
    "R013": ("WARNING", "source is not wrapped in CDATA", C),
    "R014": ("ERROR", "URL/XML-encoded characters (&amp; &lt; &gt;) in the code", f"{C}#review-guidelines (Standards)"),
    "R015": ("ERROR", "file is not UTF-8", f"{C}#review-guidelines (Standards)"),
    "R020": ("ERROR", "forbidden code fragment (blocked by the platform)", f"{G}#rule-code-restrictions"),
    "R021": ("ERROR", "uses the IIQ context; rewrite with IdnRuleUtil (idn.) helpers", f"{G}#rule-code-restrictions"),
    "R030": ("WARNING", "log.error used for non-error messages", f"{G}#rule-guidelines (Logging)"),
    "R031": ("ERROR", "logs sensitive data", f"{G}#rule-guidelines (Logging, Security)"),
    "R032": ("ERROR", "declares its own logger", f"{G}#rule-guidelines (Logging)"),
    "R033": ("WARNING", "logs a whole object (full serialization)", f"{G}#rule-guidelines (Logging)"),
    "R040": ("ERROR", "opens a connection or calls an external service", f"{G}#rule-guidelines (Execution)"),
    "R041": ("ERROR", "touches the file system", f"{G}#rule-guidelines (Execution)"),
    "R042": ("ERROR", "waits or sleeps", f"{G}#rule-guidelines (Performance)"),
    "R050": ("WARNING", "empty catch block swallows errors", f"{G}#rule-guidelines (Error Handling)"),
    "R051": ("WARNING", "value used without a null check", f"{G}#rule-guidelines (Error Handling)"),
    "R052": ("WARNING", "unreachable code after return/throw", f"{G}#rule-guidelines (Execution: no dead code)"),
    "R060": ("ERROR", "iterates over accounts or identities", f"{G}#rule-guidelines (Performance)"),
    "R061": ("WARNING", "IdnRuleUtil lookup inside a loop", f"{G}#rule-guidelines (Performance)"),
    "R070": ("ERROR", "calls an IdnRuleUtil method that does not exist", U),
    "R071": ("ERROR", "IdnRuleUtil method called with the wrong number of arguments", U),
    "R072": ("ERROR", "IdnRuleUtil search operation other than Equals/StartsWith", U),
    "R073": ("WARNING", "uniqueness check in an IdentityAttribute rule", f"{CAT['ruleTypes'].get('IdentityAttribute', {}).get('page', C)}"),
    "R074": ("WARNING", "uses a variable that is not in this rule type's inputs", "rule type page, Input table"),
    "R080": ("ERROR", "rule type must return a value and the code never returns", "rule type page, Output table"),
    "R081": ("WARNING", "BeforeProvisioning rules have no output (modify plan in place)", "BeforeProvisioning page"),
    "R082": ("WARNING", "Correlation/ManagerCorrelation must return a Map with identityAttributeName/Value", "Correlation pages, Output"),
    "R090": ("ERROR", "commented-out code or TODO/FIXME left in", f"{C}#review-guidelines (Standards)"),
    "R091": ("WARNING", "code is not indented", f"{C}#review-guidelines (Rule Quality)"),
    "R092": ("WARNING", "very long rule (more scrutiny, slower review)", f"{C}#review-expectations"),
    "R093": ("ERROR", "hard-coded password, key or test value", f"{G}#rule-guidelines (Security)"),
    "R094": ("WARNING", "connector-rule JSON without signature input/output", f"{G.rsplit('/', 1)[0]}/rules/connector-rules"),
    "R095": ("WARNING", "rule name looks like a versioned copy", f"{C}#review-guidelines (Updating Existing Rules and Versioning)"),
}
CLOUD = {t for t, v in CAT["ruleTypes"].items() if v["execution"] == "cloud"}
CONNECTOR = {t for t, v in CAT["ruleTypes"].items() if v["execution"] == "connector"}
CONNECTOR |= {"ConnectorBeforeModify", "ConnectorBeforeDelete", "ConnectorAfterCreate", "ConnectorAfterModify",
              "ConnectorAfterDelete"}  # the before/after operation page documents all six with one template
RETURNING = {"IdentityAttribute", "AttributeGenerator", "AttributeGeneratorFromTemplate", "Transform", "Correlation",
             "ManagerCorrelation"}
SENSITIVE = re.compile(r"\b\w*(password|passwd|pwd|secret|token|ssn|apikey|api_key|privatekey)\w*\b", re.I)
JAVA_WORDS = set("""abstract assert boolean break byte case catch char class const continue default do double else enum
extends final finally float for goto if implements import instanceof int interface long native new package private
protected public return short static strictfp super switch synchronized this throw throws transient try void volatile
while true false null var String Object Map HashMap List ArrayList Set HashSet Date SimpleDateFormat Integer Long
Boolean Exception GeneralException Iterator StringBuilder Math Arrays Collections Util""".split())


class Finding:
    def __init__(self, code: str, msg: str, line: int | None = None):
        self.code, self.msg, self.line = code, msg, line
        self.level = CHECKS[code][0]

    def text(self) -> str:
        where = f"line {self.line}: " if self.line else ""
        return f"{self.level:7} {self.code} {where}{self.msg}"

    def as_dict(self) -> dict:
        return {"code": self.code, "level": self.level, "line": self.line, "message": self.msg,
                "guideline": CHECKS[self.code][2]}


def strip_comments(code: str) -> str:
    code = re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), code, flags=re.S)
    return re.sub(r"//[^\n]*", "", code)


def strip_strings(code: str) -> str:
    return re.sub(r'"(?:\\.|[^"\\\n])*"', lambda m: '"' + " " * (len(m.group(0)) - 2) + '"', code)


def load(path: str, forced_type: str | None):
    raw_bytes = open(path, "rb").read()
    out = {"findings": [], "kind": "bsh", "type": forced_type, "name": None, "code": "", "code_line": 1,
           "raw": "", "description": None, "language": None}
    try:
        raw = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        out["findings"].append(Finding("R015", "not valid UTF-8; save the file as UTF-8"))
        raw = raw_bytes.decode("latin-1")
    raw = raw.lstrip("﻿")
    out["raw"] = raw
    s = raw.lstrip()
    if s.startswith("{"):
        obj = json.loads(raw)
        out.update(kind="json", type=obj.get("type") or forced_type, name=obj.get("name"),
                   code=(obj.get("sourceCode") or {}).get("script", "") or "", obj=obj,
                   description=obj.get("description"))
        return out
    if s.startswith("<"):
        decl = re.match(r"\s*<\?xml[^>]*encoding=['\"]([^'\"]+)['\"]", raw)
        if decl and decl.group(1).upper().replace("_", "-") not in ("UTF-8", "UTF8"):
            out["findings"].append(Finding("R015", f"XML declares encoding {decl.group(1)}; use UTF-8"))
        if not re.match(r"\s*<\?xml", raw) or not re.search(r"<!DOCTYPE\s+Rule\s+PUBLIC\s+\"sailpoint\.dtd\"", raw):
            out["findings"].append(Finding("R002", "start with <?xml version='1.0' encoding='UTF-8'?> and "
                                                   "<!DOCTYPE Rule PUBLIC \"sailpoint.dtd\" \"sailpoint.dtd\">"))
        xml = re.sub(r"<!DOCTYPE[^>]*>", "", raw)
        root = ET.fromstring(xml.encode("utf-8"))
        if root.tag != "Rule":
            raise ValueError(f"root element is <{root.tag}>, expected <Rule>")
        src = root.find("Source")
        desc = root.find("Description")
        code = (src.text if src is not None else "") or ""
        m = re.search(r"<Source>\s*(<!\[CDATA\[)?", raw)
        code_line = raw[: m.end()].count("\n") + 1 if m else 1
        if m and code.startswith("\n"):
            code = code[1:]
            code_line += 1
        out.update(kind="xml", type=root.get("type") or forced_type, name=root.get("name"), code=code,
                   code_line=code_line, description=(desc.text or "").strip() if desc is not None else None,
                   language=root.get("language"), cdata=bool(m and m.group(1)), source_raw=raw[m.end():] if m else "")
        return out
    out["code"] = raw
    return out


def idn_calls(clean: str):
    """Yield (line, method, argcount, args) for idn.method(...) calls; nested parentheses handled."""
    for m in re.finditer(r"\bidn\s*\.\s*(\w+)\s*\(", clean):
        i, depth, args, cur = m.end(), 1, [], ""
        while i < len(clean) and depth:
            ch = clean[i]
            if ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth -= 1
                if depth == 0:
                    break
            if ch == "," and depth == 1:
                args.append(cur)
                cur = ""
            else:
                cur += ch
            i += 1
        if cur.strip():
            args.append(cur)
        yield clean[: m.start()].count("\n") + 1, m.group(1), len(args), [a.strip() for a in args]


def loop_spans(clean: str) -> list[tuple[int, int]]:
    spans = []
    for m in re.finditer(r"\b(for|while)\s*\(", clean):
        j = clean.find("{", m.end())
        if j < 0:
            continue
        depth, k = 0, j
        while k < len(clean):
            if clean[k] == "{":
                depth += 1
            elif clean[k] == "}":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        spans.append((j, k))  # the body only: the loop header is evaluated once
    return spans


def review(path: str, forced_type: str | None = None) -> dict:
    try:
        d = load(path, forced_type)
    except (OSError, ValueError, ET.ParseError) as e:
        return {"file": path, "findings": [Finding("R001", f"cannot parse: {e}")], "type": None, "name": None}
    F = d["findings"]
    rtype, name, code, kind = d["type"], d["name"], d["code"], d["kind"]
    off = d["code_line"] - 1

    def add(code_, msg, line=None):
        F.append(Finding(code_, msg, (line + off) if line else None))

    # ---- object level
    if not rtype:
        add("R003", "set type=\"...\" on <Rule> (or 'type' in the connector-rule JSON); with a bare file pass --type")
    elif rtype in CAT["deprecated"]:
        add("R005", f"'{rtype}' is deprecated: {re.sub(r'\[([^]]+)\]\([^)]*\)', r'\1', CAT['deprecated'][rtype])}")
    elif rtype not in CLOUD | CONNECTOR:
        add("R004", f"'{rtype}' is not a supported ISC rule type; cloud: {', '.join(sorted(CLOUD))}; "
                    f"connector: {', '.join(sorted(CONNECTOR))}")
    if kind in ("xml", "json") and not name:
        add("R007", "give the rule a name")
    if name and re.search(r"(?i)([ _-](v\d+|new|old|copy|backup|final|\d{8}))$", name):
        add("R095", f"name '{name}': keep one rule per use case and update it in place (use '<name>-TEMP' only for "
                    "a planned change window)")
    if kind == "xml":
        if d["language"] and d["language"].lower() != "beanshell":
            add("R008", f"language=\"{d['language']}\": ISC rules are BeanShell")
        base = os.path.basename(path)
        if rtype and name and base != f"Rule - {rtype} - {name}.xml":
            add("R010", f"name the file 'Rule - {rtype} - {name}.xml' (is '{base}')")
        if not d["description"]:
            add("R011", "describe what the rule does and why a rule is needed instead of a transform/feature")
        if not d.get("cdata"):
            add("R013", "put the code in <Source><![CDATA[ ... ]]></Source>")
        if re.search(r"&(amp|lt|gt|quot);", d.get("source_raw", "")) and d.get("cdata"):
            add("R014", "replace &amp; &lt; &gt; with & < > inside CDATA")
        if rtype in CONNECTOR - CLOUD:
            add("R006", f"{rtype} is a connector rule: deploy it with POST /connector-rules/v1 (JSON, script escaped); "
                        "it is not submitted as a cloud-rule ticket")
    if kind == "json":
        sig = d["obj"].get("signature")
        if not isinstance(sig, dict) or "input" not in sig:
            add("R094", "include 'signature' with 'input' (and 'output') as in the rule type's page")
    if not code.strip() or not re.search(r"[;{]", strip_comments(code)):
        add("R012", "the rule has no code (template only)")
        return finish(path, d, F)

    clean = strip_comments(code)
    nostr = strip_strings(clean)
    lines = clean.split("\n")
    nlines = nostr.split("\n")

    # ---- forbidden code
    hits: dict[int, list[str]] = {}
    for tok in FORBIDDEN:
        core = tok[:-1] if tok.endswith("()") else tok
        pat = re.escape(core)
        if re.match(r"^[A-Za-z]", core):
            pat = r"(?<![A-Za-z0-9_.])" + pat
        for n, line in enumerate(nlines, 1):
            if re.search(pat, line):
                if tok not in hits.setdefault(n, []):
                    hits[n].append(tok)
                break
    for n, toks in sorted(hits.items()):
        for tok in toks:
            if any(tok != other and tok.rstrip("()").strip(".") in other for other in toks):
                continue  # report 'Thread.sleep()' once, not also 'Thread' and '.sleep()'
            if tok == "context.":
                add("R021", "context.* is not available in ISC; use the idn helper methods "
                            "(getAccountByNativeIdentity, findIdentitiesBySearchableIdentityAttribute, ...)", n)
            else:
                add("R020", f"'{tok}' is on SailPoint's code-restriction list", n)

    # ---- logging
    for n, line in enumerate(lines, 1):
        lm = re.search(r"\blog\.(debug|info|warn|error|trace|fatal)\s*\((.*)", line)
        if lm:
            arg = strip_strings(lm.group(2))
            if SENSITIVE.search(arg) or re.search(r"(?i)\"[^\"]*(password|secret|token)[^\"]*\"\s*\+", lm.group(2)):
                add("R031", "do not log passwords, secrets, tokens or personal data", n)
            if re.match(r"\s*(identity|plan|account|link|application|record|object)\s*\)", arg) or \
                    re.search(r"\+\s*(identity|plan|account|link|application)\s*\)", arg):
                add("R033", "log the fields you need, not the whole object", n)
    if re.search(r"\blog\.error\s*\(", clean):
        for n, line in enumerate(lines, 1):
            if re.search(r"\blog\.error\s*\(", line):
                before = "\n".join(lines[max(0, n - 6): n]) + "\n" + line
                before = re.sub(r"log\.error", "", before)
                if not re.search(r"(?i)\bcatch\s*\(|\bthrow\b|error|fail|exception|invalid|missing", before):
                    add("R030", "log.error is for unexpected errors; use debug/info/warn for normal messages", n)
    for n, line in enumerate(nlines, 1):
        if re.search(r"\b(LogFactory\.getLog|LoggerFactory\.getLogger|Logger\.getLogger|new\s+\w*Logger)\s*\(", line):
            add("R032", "use the provided 'log' variable", n)

    # ---- execution
    ext = re.compile(r"\b(new\s+(URL|Socket|ServerSocket|HttpGet|HttpPost|HttpClient)\b|HttpURLConnection|HttpClient|"
                     r"OkHttp|RestTemplate|DriverManager|InitialContext|java\.net\.|javax\.net\.|java\.sql\.Driver|"
                     r"javax\.mail|Transport\.send)")
    fs = re.compile(r"\b(java\.io\.(File|Print|Buffered)\w*|new\s+File(Reader|Writer|InputStream|OutputStream)?\s*\(|Files\.\w+\(|"
                    r"Paths\.get\(|RandomAccessFile|PrintWriter\s*\(\s*\"|createTempFile)")
    for n, line in enumerate(nlines, 1):
        if re.match(r"\s*import\b", line):
            continue
        if ext.search(line):
            add("R040", "no connections or call-outs outside the provided context"
                        + (" (connector rules must use the supplied connection)" if rtype in CONNECTOR else ""), n)
        if fs.search(line):
            add("R041", "no reading/writing files or temp files", n)
        if re.search(r"\.wait\s*\(|TimeUnit\.\w+\.sleep|\bsleep\s*\(", line) and "'.sleep()'" not in line:
            if not any(f.code == "R020" and f.line == n + off for f in F):
                add("R042", "no wait/sleep in rules", n)

    # ---- error handling
    for m in re.finditer(r"catch\s*\([^)]*\)\s*\{\s*\}", clean):
        add("R050", "handle or rethrow the exception (at least log it at the right level)", clean[: m.start()].count("\n") + 1)
    for n, line in enumerate(nlines, 1):
        if re.search(r"\.(getAttribute|getStringAttribute|getManager|getLink|getApplication|getFirstAccountNativeIdentity|"
                     r"getAccountByNativeIdentity|getAccountByDisplayName)\s*\([^()]*\)\s*\.\s*(?!equals\b|toString\b)\w+\s*\(", line) \
                or re.search(r"\b(parse|valueOf)\s*\(\s*\w+\.getAttribute\s*\(", line):
            prev = "\n".join(nlines[max(0, n - 4): n])
            if "null" not in prev and "!= null" not in line:
                add("R051", "the value can be null: check it before calling methods on it", n)
    for n in range(len(nlines) - 1):
        prev = next((nlines[k] for k in range(n - 1, -1, -1) if nlines[k].strip()), "")
        if re.match(r"\s*(\}\s*)?(if|else|for|while)\b.*\)?\s*$", prev) and not prev.rstrip().endswith((";", "{", "}")):
            continue  # braceless if/else body
        if re.match(r"\s*(return\b[^;]*|throw\b[^;]*);\s*$", nlines[n]):
            depth_line = nlines[n]
            for k in range(n + 1, len(nlines)):
                nxt = nlines[k].strip()
                if not nxt:
                    continue
                if nxt.startswith("}") or nxt.startswith("case ") or nxt.startswith("default"):
                    break
                indent_now = len(depth_line) - len(depth_line.lstrip())
                indent_next = len(nlines[k]) - len(nlines[k].lstrip())
                if indent_next >= indent_now and not nxt.startswith("]]>"):
                    add("R052", "this statement can never run", k + 1)
                break

    # ---- performance
    spans = loop_spans(nostr)
    for m in re.finditer(r"\b(for|while)\s*\(([^)]*)\)", nostr):
        head = m.group(2)
        if re.search(r"getLinks\s*\(|getAccounts\s*\(|getIdentities\s*\(|findIdentitiesBySearchableIdentityAttribute|"
                     r"getObjects\s*\(|\.search\s*\(", head):
            add("R060", "do not iterate over accounts/identities (cache bloat); use a single idn lookup or a "
                        "searchable-attribute query", nostr[: m.start()].count("\n") + 1)
    for ln, meth, argc, args in idn_calls(nostr):
        pos = sum(len(x) + 1 for x in nlines[: ln - 1])
        uniqueness = rtype in ("AttributeGenerator", "AttributeGeneratorFromTemplate") and \
            meth in ("accountExistsByNativeIdentity", "accountExistsByDisplayName", "isUniqueLDAPValue",
                     "attrSearchCountAccounts")  # the documented way to iterate to a unique value
        if any(a <= pos <= b for a, b in spans) and not uniqueness and meth not in (
                "getAccountAttribute", "getRawAccountAttribute", "getAccountAttributeBool", "getAccountAttributeInt"):
            add("R061", f"idn.{meth} inside a loop: one lookup per iteration; reduce or bound the loop", ln)

    # ---- IdnRuleUtil
    methods = CAT["idnMethods"]
    for ln, meth, argc, args in idn_calls(clean):
        if meth not in methods:
            close = [m for m in methods if m.lower() == meth.lower()] or \
                    __import__("difflib").get_close_matches(meth, list(methods), n=1, cutoff=0.6)
            add("R070", f"idn.{meth}() is not an IdnRuleUtil method" + (f" (did you mean {close[0]}?)" if close else ""), ln)
            continue
        counts = sorted({len(s["params"]) for s in methods[meth]})
        if argc not in counts:
            sig = " | ".join(f"{meth}({', '.join(s['params'])})" for s in methods[meth])
            add("R071", f"idn.{meth} takes {' or '.join(map(str, counts))} argument(s): {sig}", ln)
            continue
        params = next(s["params"] for s in methods[meth] if len(s["params"]) == argc)
        for p, a in zip(params, args):
            pname = p.split()[-1]
            if pname == "operation":
                lit = re.fullmatch(r'"([^"]*)"', a)
                if lit and lit.group(1) not in ("Equals", "StartsWith"):
                    add("R072", f"operation \"{lit.group(1)}\" is not supported; use \"Equals\" or \"StartsWith\"", ln)
            if pname in ("applicationName",):
                lit = re.fullmatch(r'"([^"]*)"', a)
                if lit and not lit.group(1).endswith(" [source]"):
                    add("R071", f"applicationName \"{lit.group(1)}\": ISC application names are '<source name> "
                                "[source]' (or use application.getName())", ln)
    if rtype == "IdentityAttribute" and re.search(r"idn\.(accountExistsBy\w+|isUniqueLDAPValue|attrSearchCountAccounts|"
                                                  r"countIdentitiesBySearchableIdentityAttribute)\s*\(", clean):
        add("R073", "SailPoint strongly discourages uniqueness checks in IdentityAttribute rules (re-run on every "
                    "refresh, multi-threaded); do it in an AttributeGenerator rule on the target source")

    # ---- inputs (cloud rules have a fixed set of variables)
    info = CAT["ruleTypes"].get(rtype)
    # Transform rules also receive the attributes of the calling transform as variables, so they are not checked.
    if info and info["execution"] == "cloud" and rtype != "Transform":
        declared = set(re.findall(r"\b(?:[A-Z][\w.<>,\[\] ]*|int|long|boolean|double|float|char|byte|short|var)\s+"
                                  r"([a-z_]\w*)\s*(?:=|;|:|\))", nostr))
        declared |= set(re.findall(r"\b([a-z_]\w*)\s*=[^=]", nostr))
        declared |= set(re.findall(r"catch\s*\(\s*\w[\w.]*\s+(\w+)\s*\)", nostr))
        declared |= set(re.findall(r"\bfor\s*\(\s*[\w.<>]+\s+(\w+)\s*:", nostr))
        declared |= set(re.findall(r"\b\w[\w.<>]*\s+\w+\s*\(([^)]*)\)\s*\{", nostr)
                        and [x.split()[-1] for grp in re.findall(r"\b\w[\w.<>]*\s+\w+\s*\(([^)]*)\)\s*\{", nostr)
                             for x in grp.split(",") if x.strip()])
        known = set(info["inputs"]) | declared | JAVA_WORDS | {"log", "idn"}
        flagged = set()
        for n, line in enumerate(nlines, 1):
            if re.match(r"\s*import\b", line):
                continue
            for m in re.finditer(r"(?<![\w.])([a-z]\w*)\s*\.\s*\w+\s*\(", line):
                v = m.group(1)
                if v not in known and v not in flagged and v != "context":
                    flagged.add(v)
                    add("R074", f"'{v}' is not an input of {rtype} rules (inputs: {', '.join(info['inputs'])}) and "
                                "is not declared in the rule", n)

    # ---- outputs
    has_return = re.search(r"\breturn\b\s*[^;\s]", nostr)
    if rtype in RETURNING and not has_return:
        add("R080", f"{rtype} rules must return {', '.join(info['outputs']) if info else 'a value'}")
    if rtype == "BeforeProvisioning" and re.search(r"\breturn\s+[^;\s]", nostr):
        add("R081", "returned values are ignored; change 'plan' in place")
    if rtype in ("Correlation", "ManagerCorrelation") and has_return and "identityAttributeName" not in clean:
        add("R082", "return a Map with keys identityAttributeName and identityAttributeValue (or null for no match)")

    # ---- standards
    raw_lines = code.split("\n")
    for n, line in enumerate(raw_lines, 1):
        s = line.strip()
        if re.match(r"//\s*(TODO|FIXME|XXX)\b", s, re.I):
            add("R090", "remove TODO/FIXME before submitting", n)
        elif re.match(r"//\s*(if|for|while|return|else)\b.*[;{)]\s*$", s) or \
                re.match(r"//\s*[\w.<>\[\]]+(\s+\w+)?\s*(=|\()[^;]*;\s*$", s):
            add("R090", "remove commented-out code", n)
    for m in re.finditer(r"/\*(?!\*)(.*?)\*/", code, re.S):
        body = m.group(1)
        if re.search(r";\s*$", body, re.M) and re.search(r"\b(if|for|return|log\.|idn\.|=)\b|=", body):
            add("R090", "remove commented-out code", code[: m.start()].count("\n") + 1)
    if re.search(r"\{", clean):
        body_lines = [l for l in raw_lines if l.strip() and not l.strip().startswith(("import", "]]>"))]
        inner = [l for l in body_lines if l != l.lstrip()]
        if len(body_lines) > 8 and not inner:
            add("R091", "indent blocks consistently so reviewers can read the rule")
    if len(raw_lines) > 400:
        add("R092", f"{len(raw_lines)} lines: split logic, move reusable parts to transforms, document the parts")
    for n, line in enumerate(nlines, 1):
        orig = lines[n - 1]
        if re.search(r"(?i)\b(password|passwd|pwd|secret|apikey|api_key|token|privatekey)\w*\s*=\s*\"[^\"]+\"", orig) or \
                re.search(r"(?i)\.(setPassword|setSecret)\s*\(\s*\"", orig):
            add("R093", "no credentials or test values in rule code", n)
    return finish(path, d, F)


def finish(path, d, F) -> dict:
    uniq, seen = [], set()
    for f in F:
        k = (f.code, f.line, f.msg)
        if k not in seen:
            seen.add(k)
            uniq.append(f)
    uniq.sort(key=lambda f: (f.level != "ERROR", f.line or 0, f.code))
    return {"file": path, "type": d["type"], "name": d["name"], "findings": uniq,
            "execution": CAT["ruleTypes"].get(d["type"] or "", {}).get("execution")
            or ("connector" if d["type"] in CONNECTOR else None)}


def report_md(results: list[dict]) -> str:
    out = ["# Rule review report", "",
           "Pre-submission check against SailPoint's published rule guidelines "
           f"({G}). Produced by `review_rule.py` (isc-cloud-rule-review). It checks the code statically; it does "
           "not run the rule.", ""]
    for r in results:
        errs = [f for f in r["findings"] if f.level == "ERROR"]
        warns = [f for f in r["findings"] if f.level == "WARNING"]
        verdict = "**Ready to submit**" if not errs and not warns else (
            "**Fix before submitting** (would be rejected)" if errs else "**Can be submitted**; review the warnings")
        out += [f"## {r['name'] or os.path.basename(r['file'])}", "",
                f"- File: `{os.path.basename(r['file'])}`",
                f"- Type: `{r['type']}`" + (f" ({r['execution']} rule)" if r.get("execution") else ""),
                f"- Result: {verdict} — {len(errs)} error(s), {len(warns)} warning(s)", ""]
        if r["findings"]:
            out += ["| Level | Check | Line | Finding | Guideline |", "|---|---|---|---|---|"]
            for f in r["findings"]:
                out.append(f"| {f.level} | {f.code} | {f.line or ''} | {f.msg.replace('|', '/')} | {CHECKS[f.code][2]} |")
            out.append("")
        if r.get("execution") == "cloud" and not errs:
            out += ["Attach to the support ticket: this rule file, this report (validator output), the tenant name "
                    "(e.g. `acme-sb.identitynow.com`) and approval for Expert Services hours.", ""]
    return "\n".join(out) + "\n"


def main(argv) -> int:
    if "--codes" in argv:
        for code, (lvl, title, src) in CHECKS.items():
            print(f"{code} {lvl:7} {title}  [{src}]")
        return 0
    files, report, as_json, forced = [], None, False, None
    it = iter(argv)
    for a in it:
        if a == "--report":
            report = next(it, None)
        elif a == "--json":
            as_json = True
        elif a == "--type":
            forced = next(it, None)
        elif a in ("-h", "--help"):
            print(__doc__)
            return 0
        else:
            files.append(a)
    if not files:
        print(__doc__)
        return 2
    results = [review(f, forced) for f in files]
    if report:
        with open(report, "w", encoding="utf-8") as fh:
            fh.write(report_md(results))
    if as_json:
        print(json.dumps([{**{k: v for k, v in r.items() if k != "findings"},
                           "findings": [f.as_dict() for f in r["findings"]]} for r in results], indent=2))
    else:
        for r in results:
            print(f"Rule: {r['name']}  type: {r['type']}  ({os.path.basename(r['file'])})")
            for f in r["findings"]:
                print(f.text())
            e = sum(f.level == "ERROR" for f in r["findings"])
            print(f"{e} error(s), {len(r['findings']) - e} warning(s)")
    if any(f.code == "R001" for r in results for f in r["findings"]):
        return 2
    return 1 if any(f.level == "ERROR" for r in results for f in r["findings"]) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
