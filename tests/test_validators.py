"""Regression tests for the validators. Run: python3 -m unittest discover -s tests -v"""
import glob
import json
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(ROOT, "tests", "fixtures")
S = os.path.join(ROOT, "skills")


# Errors found in SailPoint's own docs by the validator (kept as known issues, see README "Findings").
KNOWN_DOC_ISSUES = [
    # the provisioning-policy guide uses "start"/"end" for substring; the operation reference requires "begin"
    ("provisioning-policy-transform.md", "'substring' requires attribute 'begin'"),
]


def run(script, *args):
    p = subprocess.run([sys.executable, os.path.join(S, script), *args], capture_output=True, text=True)
    return p.returncode, p.stdout


class Workflows(unittest.TestCase):
    V = "isc-workflows/scripts/validate_workflow.py"

    def test_bundled_examples_have_no_errors(self):
        files = glob.glob(os.path.join(S, "isc-workflows/references/examples/*.json"))
        self.assertGreaterEqual(len(files), 5)
        for f in files:
            code, out = run(self.V, f)
            self.assertEqual(code, 0, f"{f}\n{out}")

    def test_broken_workflow(self):
        code, out = run(self.V, os.path.join(FIX, "workflow-bad.json"))
        self.assertEqual(code, 1)
        for expected in ("defaultStep", "points to 'Done'", "&& and ||", "technical name", "must start with '$'",
                         "JSONPath starting with '$'", "created disabled"):
            self.assertIn(expected, out)

    def test_cron_minutes_and_timezone(self):
        code, out = run(self.V, os.path.join(FIX, "workflow-bad-schedule.json"))
        self.assertIn("hours only", out)
        self.assertIn("timeZone", out)


class Transforms(unittest.TestCase):
    V = "isc-transforms/scripts/validate_transform.py"

    def test_ok(self):
        self.assertEqual(run(self.V, os.path.join(FIX, "transform-ok-email.json"))[0], 0)

    def test_bad(self):
        code, out = run(self.V, os.path.join(FIX, "transform-bad-conditional.json"))
        self.assertEqual(code, 1)
        self.assertIn("case-sensitive", out)
        code, out = run(self.V, os.path.join(FIX, "transform-bad-datecompare.json"))
        self.assertIn("lt, lte, gt, gte", out)
        self.assertIn("sourceName", out)

    def test_documented_examples_pass(self):
        sys.path.insert(0, os.path.join(S, "isc-transforms/scripts"))
        import re
        import validate_transform as V
        bad = []
        for f in glob.glob(os.path.join(S, "isc-transforms/references/**/*.md"), recursive=True):
            for blk in re.findall(r"```json\n(.*?)```", open(f, encoding="utf-8").read(), re.S):
                try:
                    j = json.loads(blk)
                except ValueError:
                    continue
                if isinstance(j, dict) and "type" in j and "name" in j:
                    r = V.validate(j)
                    errs = [e for e in r.errors if not any(k in f and k2 in e for k, k2 in KNOWN_DOC_ISSUES)]
                    if errs:
                        bad.append((f, errs))
        self.assertEqual(bad, [])


class Api(unittest.TestCase):
    V = "isc-api/scripts/check_filter.py"

    def test_valid(self):
        code, out = run(self.V, "GET /access-request-status/v1", "--filters",
                        'created ge 2026-01-01T00:00:00Z and accessRequestId eq "x"', "--sorters", "-created")
        self.assertEqual(code, 0, out)
        self.assertIn("filters=created%20ge", out)

    def test_invalid(self):
        code, out = run(self.V, "GET /access-request-approvals/v1/pending", "--filters", 'status EQ "PENDING"')
        self.assertEqual(code, 1)
        self.assertIn("lowercase", out)
        self.assertIn("not filterable", out)

    def test_legacy_hint(self):
        code, out = run(self.V, "GET /v3/access-request-status")
        self.assertEqual(code, 2)
        self.assertIn("/access-request-status/v1", out)


class Rules(unittest.TestCase):
    V = "isc-rules/scripts/lint_rule.py"

    def test_good_rule(self):
        code, out = run(self.V, os.path.join(FIX, "Rule - IdentityAttribute - Calculate Lifecycle.xml"))
        self.assertEqual(code, 0, out)

    def test_bad_rule(self):
        code, out = run(self.V, os.path.join(FIX, "Rule - BeforeProvisioning - Bad.xml"))
        self.assertEqual(code, 1)
        for t in ("System.out.", ".getObjectByName()", "context.", "sensitive", "Thread"):
            self.assertIn(t, out)


class Templates(unittest.TestCase):
    V = "isc-notifications/scripts/check_template.py"

    def test_ok(self):
        code, out = run(self.V, os.path.join(FIX, "template-ok.html"), "--vars",
                        "accessibleItems,accessProfileName,approved,reviewerComment,requestedObjectName,requesterName")
        self.assertEqual(code, 0, out)

    def test_bad(self):
        code, out = run(self.V, os.path.join(FIX, "template-bad.html"), "--vars", "approved", "--v2",
                        "--subject", "Stop 4<5")
        self.assertEqual(code, 1)
        for t in ("<head>", "never closed", "$user is only available", "$foo", "DISABLED"):
            self.assertIn(t, out)


class Search(unittest.TestCase):
    V = "isc-search/scripts/lint_query.py"

    def test_skill_examples_clean(self):
        import re
        text = open(os.path.join(S, "isc-search/SKILL.md"), encoding="utf-8").read()
        rows = re.findall(r"\| [^|]+ \| `([^`]+)` \((\w+)\) \|", text)
        self.assertGreater(len(rows), 5)
        for q, idx in rows:
            code, out = run(self.V, q, "--index", idx)
            self.assertEqual(code, 0, f"{q}\n{out}")

    def test_bad(self):
        code, out = run(self.V, 'name eq "x" and @entitlements(name:a)', "--index", "identities")
        self.assertEqual(code, 1)
        self.assertIn("filters` syntax", out)
        self.assertIn("not a nested object", out)


class Sources(unittest.TestCase):
    V = "isc-sources/scripts/check_source_config.py"

    def test_bad_policy(self):
        code, out = run(self.V, os.path.join(FIX, "source-bad-policy.json"))
        self.assertEqual(code, 1)
        for needle in ("did you mean 'CREATE'", "comes later", "type 'text' is not valid", "duplicate field 'uid'",
                       "did you mean 'lower'"):
            self.assertIn(needle, out)

    def test_bad_source_correlation_ncd_schedule(self):
        code, out = run(self.V, os.path.join(FIX, "source-bad-misc.json"))
        self.assertEqual(code, 1)
        for needle in ("unknown feature 'PROVISION'", "deleteThreshold must be an integer 0-100", "plain-text secret",
                       "only does EQ", "without any attribute selected", "Quartz cron"):
            self.assertIn(needle, out)

    def test_documented_policies_pass(self):
        # JSON policies in this skill's references and in SailPoint's provisioning-policy transform guide
        import re
        import tempfile
        files = glob.glob(os.path.join(S, "isc-sources/references/*.md")) + \
            glob.glob(os.path.join(S, "isc-transforms/references/guides/provisioning-policy-transform.md"))
        checked = 0
        for f in files:
            for blk in re.findall(r"```json\n(.*?)```", open(f, encoding="utf-8").read(), re.S):
                try:
                    j = json.loads(blk)
                except ValueError:
                    continue
                with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
                    json.dump(j, fh)
                code, out = run(self.V, fh.name)
                os.unlink(fh.name)
                errs = [l for l in out.splitlines() if "ERROR" in l
                        and not any(k in f and k2 in l for k, k2 in KNOWN_DOC_ISSUES)]
                self.assertEqual(errs, [], f"{f}: {out}")
                checked += 1
        self.assertGreaterEqual(checked, 4)


class SkillFiles(unittest.TestCase):
    def test_frontmatter_and_links(self):
        import re
        for sk in glob.glob(os.path.join(S, "*/SKILL.md")):
            t = open(sk, encoding="utf-8").read()
            m = re.match(r"^---\nname: ([a-z0-9-]+)\ndescription: (.+?)\n---\n", t)
            self.assertTrue(m, sk)
            self.assertEqual(m.group(1), os.path.basename(os.path.dirname(sk)))
            self.assertLessEqual(len(m.group(2)), 1024)
            for ref in set(re.findall(r"`((?:references|scripts)/[^`*<> ]+?\.(?:md|py|json))`", t)):
                self.assertTrue(os.path.exists(os.path.join(os.path.dirname(sk), ref)), f"{sk}: missing {ref}")


if __name__ == "__main__":
    unittest.main()
