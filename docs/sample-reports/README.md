# Sample reports (controlled fixtures)

| Date | Fixture | Mode | Calls | Verdict |
|---|---|---|---|---|
| 2026-10-29 | repro.py | LIVE (muse-spark-open) | 2 | FAIL — patch rejected (replaces shuffle instead of seeding) |
| 2026-10-29 | diverge.py | LIVE (muse-spark-open) | 2 | FAIL — masks loss (clip_grad) |
| 2026-10-29 | leakage.py | LIVE + investigate (muse-spark-open) | 3 | FAIL — dedup misplaced (leakage masking) |
| 2026-10-29 | repro.py | MOCK | 2 | PASS |
| 2026-10-29 | leakage.py | MOCK | 2 | FAIL in manual smoke (mock patch placement) |

All fixtures are controlled, known-bug cases.

## Files in this folder

- LIVE: `live-{repro,diverge,leakage}-ledger.jsonl` — model
  `meta-models/muse-spark-open`, 2026-10-29. Verdicts and diffs are in
  `.mldoctor/patched/{repro,diverge,leakage}.patched.py` (produced by those
  runs; diff vs `fixtures/` shows the rejected proposal).
- MOCK: `mock-{repro,diverge,leakage}.json` (+ `.html`, `.md`, `.patch`) —
  proof bundles from offline mock runs for comparison. Regenerate with
  `mldoctor fix <fixture> --proof docs/sample-reports/mock-<name>`.

Token totals from the ledgers: repro 7821 total (5932 reasoning),
diverge 6353 (4357), leakage 9340 (7078). No secret values are stored here.
