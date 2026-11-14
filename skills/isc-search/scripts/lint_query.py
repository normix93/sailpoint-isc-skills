#!/usr/bin/env python3
"""Lint a SailPoint ISC search query string (the `query.query` of POST /search/v1 or the UI search bar).

Usage:  python3 lint_query.py 'attributes.cloudLifecycleState:active AND @accounts(source.name:"AD")' [--index identities]
Exit 0 = no errors, 1 = errors. Standard library only.

Catches the common mistakes: API `filters` syntax (eq, ==) used in search, lowercase and/or,
spaces around ':', unbalanced quotes/parentheses, conditions on the same nested object split
into separate @groups, .exact on fields that don't support it, unknown nested objects for the index.
"""
from __future__ import annotations

import json
import re
import sys

NESTED = {
    "identities": {"accounts", "access", "apps"},
    "accessprofiles": {"entitlements", "apps"},
    "entitlements": {"accessModelMetadata"},
    "roles": {"entitlements", "accessModelMetadata", "dimensions", "dimensionSchemaAttributes"},
    "accountactivities": {"accountRequests", "originalRequests", "expansionItems", "approvals"},
    "events": set(),
}
NO_EXACT = {"email", "id", "phone", "employeeNumber", "processingState", "type", "tags"}


def lint(q: str, index: str | None) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    if q.count('"') % 2:
        errors.append("unbalanced double quotes")
    depth = 0
    for ch in re.sub(r'"[^"]*"', "", q):
        depth += ch == "("
        depth -= ch == ")"
        if depth < 0:
            errors.append("unbalanced parentheses")
            break
    if depth > 0:
        errors.append("unbalanced parentheses")
    outside = re.sub(r'"[^"]*"', '""', q)
    for quoted in re.findall(r'(?<!\.exact:)"([^"]*[*?][^"]*)"', q):
        warnings.append(f'wildcard inside quotes ("{quoted}") may not behave like a wildcard (standard query-string treats quoted text as a phrase, though SailPoint examples use "*@acme.com"); check the result count, or use field.exact:/regex/')
    if re.search(r"\s(eq|ne|sw|co)\s", outside) or "==" in outside:
        errors.append("that's API `filters` syntax (eq/==); search uses field:value, e.g. name:\"John\"")
    if re.search(r"\s(and|or|not)\s", outside):
        warnings.append("lowercase and/or/not are treated as search terms; boolean operators must be UPPERCASE (AND, OR, NOT)")
    if re.search(r"\w:\s", outside) or re.search(r"\w\s:", outside):
        errors.append("no spaces before or after ':' (field:value)")
    for m in re.finditer(r"(?<![\w@.])([A-Za-z_][\w.]*)\.exact:", outside):
        last = m.group(1).split(".")[-1]
        if last in NO_EXACT:
            errors.append(f"'.exact' is not supported on '{m.group(1)}'")
    groups = re.findall(r"@(\w+)\(", outside)
    for g in set(groups):
        if groups.count(g) > 1:
            warnings.append(f"@{g}(...) appears more than once: conditions in separate groups can match different "
                            f"{g} items; put conditions that must hold on the same item inside one @{g}( ... AND ... )")
    if index:
        allowed = NESTED.get(index)
        if allowed is not None:
            for g in set(groups):
                if g not in allowed:
                    errors.append(f"@{g} is not a nested object of index '{index}' (nested: {', '.join(sorted(allowed)) or 'none'})")
    for m in re.finditer(r"(?<![\w@.])(accounts|access|apps)\.(\w+):", outside):
        warnings.append(f"'{m.group(0)}' uses a nested object without @: write @{m.group(1)}({m.group(2)}:…)")
    multi = re.findall(r"(?<![\w.])[\w.]+:([A-Za-z0-9_-]+\s+(?!(?:AND|OR|NOT|TO)\b)[A-Za-z0-9_-]+)(?=\s|$)", outside)
    for _ in multi:
        warnings.append("a multi-word value without double quotes is split into OR terms; wrap phrases in \"…\"")
        break
    if re.search(r"(?<!\\)\d\d:\d\d:\d\d", outside) and not re.search(r"\[[^\]]*TO", outside):
        warnings.append("escape ':' inside times (2026-01-01T10\\:00\\:00Z) or quote the value")
    return errors, warnings


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    q = argv[1]
    index = argv[argv.index("--index") + 1] if "--index" in argv else None
    errors, warnings = lint(q, index)
    if "--json" in argv:
        print(json.dumps({"errors": errors, "warnings": warnings}, indent=2))
    else:
        for e in errors:
            print(f"ERROR   {e}")
        for w in warnings:
            print(f"WARNING {w}")
        print(f"{len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
