# Contributing

Thanks for helping keep this accurate.

- **Something wrong or outdated?** Open an issue with the question you asked, the answer you got, and the SailPoint source (doc URL or spec file) that says otherwise.
- **Generated files** (first line says `GENERATED`) are never edited by hand: fix `tools/build_references.py` or wait for the weekly refresh PR.
- **Hand-written references** (`references/*.md` without the banner): keep the "checked on" date and the source URL up to date; summarise SailPoint's product docs in your own words, don't paste them.
- **Validators**: add a fixture under `tests/fixtures/` and a test in `tests/test_validators.py` for every new check, plus one for the false positive you're fixing.
- **New questions for the eval set** are very welcome (`evals/questions.jsonl`): one line per question with the facts a correct answer must contain and the source.
- No tenant data, credentials, customer names or internal URLs anywhere in the repo.

Run before a PR:

```bash
python3 -m unittest discover -s tests -v
```
