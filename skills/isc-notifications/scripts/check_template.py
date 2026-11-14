#!/usr/bin/env python3
"""Check an ISC email template body (and subject) before pasting it into Email Templates.

Usage:
  python3 check_template.py body.html [--subject "text"] [--vars vars.json | --vars name1,name2] [--v2] [--json]

--vars  either the JSON returned by GET /notification-template-variables/v1/{key}/EMAIL
        (globalVariables + templateVariables) or a comma-separated list of template variable names.
        Without it, variable names are not verified (only syntax and HTML are checked).
--v2    the template is a v2 template ($__recipient, $__global …; $user is not available).

Checks: Velocity directive balance (#if/#foreach/#end), unknown variables, $user in v2 templates,
HTML elements/attributes the sanitizer removes, <head>/comments, size (130 KB), the no_send/Stop
subject switch, '<'/'>' spacing in subjects. Standard library only. Exit 1 if errors.
"""
from __future__ import annotations

import json
import re
import sys
from html.parser import HTMLParser

ALLOWED_TAGS = {"a", "img", "p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "blockquote",
                "strong", "strike", "tt", "code", "pre", "big", "small", "br", "span", "em", "s", "u", "sup",
                "sub", "ins", "del", "table", "tr", "td", "th"}
ID_TAGS = {"a", "img", "p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "blockquote",
           "table", "tr", "td", "th"}
ATTRS = {"a": {"href"}, "img": {"src", "alt", "height", "width"}}
V1_GLOBALS = {"user", "PRODUCT_NAME", "spTools", "__global", "__esc", "__dateTool", "__numberTool"}
V2_GLOBALS = {"__global", "__recipient", "__contentJson", "__dateTool", "__numberTool", "__util", "__esc"}
VELOCITY_KEYWORDS = {"foreach", "velocityCount", "velocityHasNext"}


class HtmlCheck(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.problems = []

    def handle_starttag(self, tag, attrs):
        if tag == "head":
            self.problems.append(("error", "<head> is removed before sending"))
        elif tag == "style":
            self.problems.append(("error", "<style> blocks are not allowed: use inline style=\"…\""))
        elif tag == "script":
            self.problems.append(("error", "<script> is not allowed"))
        elif tag not in ALLOWED_TAGS:
            self.problems.append(("warning", f"<{tag}> is not in the sanitizer's allowed list and will be stripped"))
        for name, _ in attrs:
            ok = name == "style" or (name == "id" and tag in ID_TAGS) or name in ATTRS.get(tag, set())
            if not ok:
                self.problems.append(("warning", f"attribute '{name}' on <{tag}> is not allowed and will be stripped"))

    def handle_comment(self, data):
        self.problems.append(("error", "HTML comments (including conditional comments) are not supported"))


def velocity_refs(text: str) -> set[str]:
    refs = set()
    for m in re.finditer(r"\$!?\{?([A-Za-z_][A-Za-z0-9_]*)", text):
        refs.add(m.group(1))
    return refs


def set_vars(text: str) -> set[str]:
    names = set(re.findall(r"#set\s*\(\s*\$([A-Za-z_]\w*)", text))
    names |= set(re.findall(r"#foreach\s*\(\s*\$([A-Za-z_]\w*)\s+in", text))
    return names


def check_directives(text: str) -> list[tuple[str, str]]:
    out = []
    stack = []
    for m in re.finditer(r"#\{?(if|foreach|macro|define|elseif|else|end)\b\}?", text):
        d = m.group(1)
        if d in ("if", "foreach", "macro", "define"):
            stack.append(d)
        elif d in ("elseif", "else"):
            if not stack or stack[-1] != "if":
                out.append(("error", f"#{d} without an open #if"))
        elif d == "end":
            if not stack:
                out.append(("error", "#end without an opening #if/#foreach"))
            else:
                stack.pop()
    for d in stack:
        out.append(("error", f"#{d} is never closed with #end"))
    if re.search(r"#if\s*\([^)]*\b(==|!=)\s*'", text):
        out.append(("info", "string comparison with single quotes works in Velocity, double quotes are clearer"))
    return out


def load_vars(arg: str) -> set[str] | None:
    if not arg:
        return None
    try:
        with open(arg, encoding="utf-8") as fh:
            data = json.load(fh)
        names = set()
        for group in ("globalVariables", "templateVariables"):
            for v in data.get(group, []):
                k = v.get("key", "")
                names.add(re.split(r"[.(]", k)[0])
        return names
    except (OSError, ValueError):
        return {n.strip() for n in arg.split(",") if n.strip()}


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    body = open(argv[1], encoding="utf-8").read()
    subject = argv[argv.index("--subject") + 1] if "--subject" in argv else ""
    known = load_vars(argv[argv.index("--vars") + 1]) if "--vars" in argv else None
    v2 = "--v2" in argv
    findings: list[tuple[str, str]] = []
    size = len(body.encode())
    if size > 130_000:
        findings.append(("error", f"template is {size} bytes; custom templates are limited to 130 KB"))
    hc = HtmlCheck()
    hc.feed(body)
    findings += hc.problems
    findings += check_directives(body + "\n" + subject)
    refs = velocity_refs(body + "\n" + subject)
    local = set_vars(body + "\n" + subject)
    globals_ = V2_GLOBALS if v2 else V1_GLOBALS
    if v2 and "user" in refs:
        findings.append(("error", "$user is only available in v1 templates; use $__recipient in v2"))
    if not v2 and refs & {"__recipient", "__util", "__contentJson"}:
        findings.append(("warning", "$__recipient/$__util/$__contentJson are v2 globals: check this template is v2"))
    if known is not None:
        for r in sorted(refs - local - globals_ - VELOCITY_KEYWORDS):
            if r not in known:
                findings.append(("error", f"${r} is not a variable of this template (renders literally as ${{{r}}})"))
    if re.search(r"(?<=\S)[<>](?=\S)", re.sub(r"<[^>]+>", "", subject)):
        findings.append(("warning", "subject: '<' and '>' only render when surrounded by spaces (4 < 5)"))
    first = subject.strip().split(" ")[0].lower() if subject.strip() else ""
    if first in ("no_send", "stop"):
        findings.append(("warning", "subject starts with no_send/Stop: this template is DISABLED"))
    if re.search(r"<img[^>]+src=\"data:", body):
        findings.append(("warning", "base64 images inflate the message and are blocked by some clients; prefer hosted HTTPS images"))
    if re.search(r"<img[^>]+src=\"http:", body):
        findings.append(("warning", "image over plain http: many clients block it, use https"))
    errors = [m for s, m in findings if s == "error"]
    warnings = [m for s, m in findings if s == "warning"]
    if "--json" in argv:
        print(json.dumps({"errors": errors, "warnings": warnings, "variablesUsed": sorted(refs - local)}, indent=2))
    else:
        print("Variables used: " + (", ".join(sorted(refs - local)) or "none"))
        for e in errors:
            print(f"ERROR   {e}")
        for w in warnings:
            print(f"WARNING {w}")
        print(f"{len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
