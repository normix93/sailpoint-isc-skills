# Evaluation

`questions.jsonl` — questions an ISC engineer actually asks, one per line (the `user-*` ones come from real day-to-day work and were added after the first graded run of the first 40; the `src-*` ones were added in 0.2.0 with the `isc-sources` skill and graded separately: `runs-sources/`, `results-sources.md`):

- `q` — the question;
- `must` — facts a correct answer has to contain;
- `must_not` — common wrong answers that cost points;
- `source` — the SailPoint spec file or doc page the expected answer comes from.

## How the results were produced

1. **Baseline**: a model answers every question closed-book (no skills, no web, no files).
2. **With skills**: the same model answers using only `skills/` (it may run the scripts), still no web.
3. **Grading**: a separate agent that wrote neither answer set grades both, blind (answers shuffled as A/B per question), against `must` / `must_not`:
   - 2 = every `must` fact present and correct, nothing from `must_not`;
   - 1 = partly right (some facts missing or vague) and nothing harmful;
   - 0 = wrong, missing the core fact, or contains a `must_not` error.
4. `score.py` un-blinds the grades and writes `results.md`.

Files of the last run are in `runs/`. To reproduce with another model, repeat steps 1–3 and run:

```bash
python3 evals/score.py evals/runs/grades.jsonl evals/runs/blind_map.json > evals/results.md
```

Limits: 40 questions written by the maintainer from the same sources the skills use, so the set tests whether the skills deliver what the docs say — not unknown unknowns. A single run, one model. Contributions of real-world questions with sources are the best way to make this harder.
