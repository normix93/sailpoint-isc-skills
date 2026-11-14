#!/usr/bin/env python3
"""Check a `filters` / `sorters` expression against what a SailPoint ISC endpoint accepts.

Usage:
  python3 check_filter.py "GET /access-request-status/v1" --filters 'created ge 2026-01-01T00:00:00Z and accessRequestId eq "abc"'
  python3 check_filter.py "GET /accounts/v1" --sorters '-created,name'
  python3 check_filter.py "GET /accounts/v1"                       # just list what the endpoint supports
  python3 check_filter.py --find access-request                      # list endpoints whose path contains the text

Data: endpoint_params.json, generated from SailPoint's OpenAPI specs by tools/build_references.py.
Standard library only. Exit 0 = valid, 1 = problems found, 2 = unknown endpoint / bad usage.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "endpoint_params.json"), encoding="utf-8") as fh:
    ENDPOINTS = json.load(fh)["endpoints"]

OPERATORS = {"eq", "ne", "gt", "ge", "lt", "le", "in", "sw", "co", "ca", "pr", "isnull"}
UNARY = {"pr", "isnull"}
LOGIC = {"and", "or", "not"}
TOKEN = re.compile(r'\s*(\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+)')


def tokenize(expr: str) -> list[str]:
    pos, out = 0, []
    while pos < len(expr):
        m = TOKEN.match(expr, pos)
        if not m:
            raise ValueError(f"cannot parse near: {expr[pos:pos + 20]!r}")
        if m.group(1):
            out.append(m.group(1))
        pos = m.end()
    return out


def check_filters(expr: str, allowed: dict[str, list[str]]) -> list[str]:
    problems = []
    if expr.count('"') % 2:
        problems.append('unbalanced double quotes (escape quotes inside values as \\")')
    try:
        toks = tokenize(expr)
    except ValueError as e:
        return [str(e)]
    depth = 0
    i = 0
    while i < len(toks):
        t = toks[i]
        tl = t.lower()
        if t == "(":
            depth += 1
            i += 1
            continue
        if t == ")":
            depth -= 1
            if depth < 0:
                problems.append("unbalanced parentheses")
            i += 1
            continue
        if tl in LOGIC:
            if t != tl:
                problems.append(f"logical operator '{t}' must be lowercase ('{tl}')")
            i += 1
            continue
        # unary prefix form "pr field"
        if tl in UNARY and i + 1 < len(toks):
            field, op = toks[i + 1], tl
            i += 2
        else:
            field = t
            if i + 1 >= len(toks):
                problems.append(f"incomplete comparison after '{field}'")
                break
            op = toks[i + 1]
            if op.lower() in UNARY:
                i += 2
            else:
                if op.lower() == "in":
                    # value is a parenthesised list
                    j = i + 2
                    if j >= len(toks) or toks[j] != "(":
                        problems.append(f"'in' needs a list: {field} in (\"a\",\"b\")")
                        i = j
                        continue
                    while j < len(toks) and toks[j] != ")":
                        j += 1
                    i = j + 1
                else:
                    if i + 2 >= len(toks):
                        problems.append(f"missing value after '{field} {op}'")
                        break
                    val = toks[i + 2]
                    i += 3
                    if not (val.startswith('"') or re.fullmatch(r"-?\d+(\.\d+)?|true|false|null|\d{4}-\d\d-\d\d(T[\d:.]+(Z|[+-]\d\d:?\d\d)?)?", val)):
                        problems.append(f"value {val!r} for '{field}' should be in double quotes (strings) or an unquoted number/boolean/ISO-8601 date")
                    if val.startswith("'"):
                        problems.append("use double quotes, not single quotes, around string values")
        opl = op.lower()
        if op != opl and opl in OPERATORS:
            problems.append(f"operator '{op}' must be lowercase ('{opl}')")
        if opl not in OPERATORS:
            problems.append(f"'{op}' is not a filter operator (valid: {', '.join(sorted(OPERATORS))})")
            continue
        if field not in allowed:
            close = [f for f in allowed if f.lower() == field.lower()]
            hint = f" (did you mean '{close[0]}'? field names are case-sensitive)" if close else ""
            problems.append(f"field '{field}' is not filterable on this endpoint{hint}. Filterable: {', '.join(allowed) or 'none'}")
        elif opl not in [o.lower() for o in allowed[field]]:
            problems.append(f"operator '{opl}' is not allowed on '{field}' (allowed: {', '.join(allowed[field])})")
    if depth > 0:
        problems.append("unbalanced parentheses")
    return problems


def check_sorters(expr: str, allowed: list[str]) -> list[str]:
    problems = []
    for part in [p.strip() for p in expr.split(",") if p.strip()]:
        f = part.lstrip("+-")
        if f not in allowed:
            problems.append(f"'{f}' is not sortable here. Sortable: {', '.join(allowed) or 'none documented'}")
    return problems


def describe(key: str, info: dict) -> str:
    lines = [key + ("  [EXPERIMENTAL: send X-SailPoint-Experimental: true]" if info.get("experimental") else "")]
    if "limitMax" in info:
        lines.append(f"  limit: max {info['limitMax']}  (paginate with offset; add sorters for stable pages)")
    if info.get("filters"):
        lines.append("  filters:")
        lines += [f"    {f}: {', '.join(ops)}" for f, ops in info["filters"].items()]
    elif "filters" in info.get("query", []):
        lines.append("  filters: accepted, but fields not documented in the spec")
    else:
        lines.append("  filters: not supported")
    if info.get("sorters"):
        lines.append(f"  sorters: {', '.join(info['sorters'])}")
    other = [q for q in info.get("query", []) if q not in ("filters", "sorters", "limit", "offset", "count")]
    if other:
        lines.append(f"  other query params: {', '.join(other)}")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    args = argv[1:]
    if not args:
        print(__doc__)
        return 2
    if args[0] == "--find":
        needle = args[1] if len(args) > 1 else ""
        for k in sorted(ENDPOINTS):
            if needle in k:
                print(k)
        return 0
    key = re.sub(r"\s+", " ", args[0].strip())
    if " " not in key:
        key = "GET " + key
    method, path = key.split(" ", 1)
    key = f"{method.upper()} {path}"
    info = ENDPOINTS.get(key)
    if info is None:
        legacy = re.match(r"/(v3|beta|v20\d\d)/([\w-]+)(.*)", path)
        hint = ""
        if legacy:
            cands = [k for k in ENDPOINTS if k.startswith(f"{method.upper()} /{legacy.group(2)}/")]
            hint = f"\nLegacy path: current equivalents may be: {', '.join(cands[:5])}"
        print(f"Unknown endpoint '{key}'. Try --find <text>.{hint}")
        return 2
    flt = srt = None
    if "--filters" in args:
        flt = args[args.index("--filters") + 1]
    if "--sorters" in args:
        srt = args[args.index("--sorters") + 1]
    print(describe(key, info))
    problems = []
    if flt is not None:
        if "filters" not in info.get("query", []):
            problems.append("this endpoint has no 'filters' parameter")
        else:
            problems += check_filters(flt, info.get("filters", {}))
    if srt is not None:
        problems += check_sorters(srt, info.get("sorters", []))
    if flt is not None or srt is not None:
        if problems:
            print("\nPROBLEMS:")
            for p in dict.fromkeys(problems):
                print(f"  - {p}")
            return 1
        qs = {}
        if flt is not None:
            qs["filters"] = flt
        if srt is not None:
            qs["sorters"] = srt
        print("\nOK. Encoded query string:\n  ?" + urllib.parse.urlencode(qs, quote_via=urllib.parse.quote))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
