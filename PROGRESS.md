# MLDoctor — Progress (state as of 2026-10-29, stages 0+A done)

## Where things stand
- Backend pipeline DONE, tested: harness, runner, budget, mock + live LLM clients,
  diagnose, patch, verify gate, events, pipeline, FastAPI dashboard, HTML report.
- Fast: 78 passed (~14s). Slow: 13 passed (~139s). New: tests/test_harness_env.py (2).
- Stage 0 DONE: child scripts get allowlisted env (harness.child_env(); secrets with
  API_KEY/SECRET/TOKEN/PASSWORD/PRIVATE_KEY never forwarded, even via extra_env).
  README warns uploaded/pasted scripts execute locally as the server user.
- Stage A DONE — live path is REAL (Baseten verified): model slug in .env works,
  no fallback probe needed. Real response: top keys choices/created/id/model/object/
  usage; reasoning in message.reasoning_content; reasoning tokens in
  completion_tokens_details; finish_reason length when max_tokens too small
  (probe max_tokens=50 returned empty content — use >=4096 for live fixes).
- Live fix on fixtures/repro.py: 2 calls, model reported meta-models/muse-spark-open,
  diagnose correct (unseeded random.shuffle), patch REJECTED by gate (replaces shuffle
  with randperm instead of just seeding) — gate held, 0 verify runs. Ledger at
  /tmp/live_repro_ledger.jsonl (7821 total tokens). No gate loosening.
- test_llm.py fake server now returns the real shape (id/object/usage/finish_reason/
  reasoning_content) with assertions. test_live.py already covered it.
- Real calls used: 3 of 30 (1 probe + 2 fix). Session rule: no retries on failure.

## Key decisions (do not regress)
- Child harness never seeds RNGs; scripts seed from MLDOCTOR_SEED. Diverge = non-finite
  loss OR peak >10x initial, before reproducibility. Verify: 10 same-seed runs for
  non_reproducible, 5 seeds for diverged. MockClient keyed by symptom class, text-only.
- Git identity HimanshuSolo; agent never runs git. Stale .mldoctor/patched/*.py left
  alone (deletion needs user approval). Three + @react-three/fiber already installed.

## PENDING NEXT: Stage B (investigation loop), C (leakage), D (vision), E (proof/export/CI), F (frontend 3D), G (live evidence, 18-call cap)
- Frontend stays Next.js in web/ via reduce(); vanilla static/ fallback untouched.
- Honesty rules: every animation from a real server event; no PASS before completion
  event; MOCK/LIVE/DEMO badges truthful; fixtures labeled controlled.

## Commands (repo root)
- Fast: .venv/bin/python -m pytest -q | Slow: .venv/bin/python -m pytest -q -m slow
- Live fix: .venv/bin/mldoctor fix fixtures/repro.py --live -k 2 --max-calls 4 --max-tokens 4096 --ledger /tmp/ledger.jsonl
- Dashboard: .venv/bin/mldoctor serve --port 8765 (two-process) or static_next (one-process)
