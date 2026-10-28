# MLDoctor — Progress (state as of 2026-10-28, session mild-cosmos)

## Where things stand
- Backend pipeline is DONE and fully tested: harness, runner, budget, mock + live LLM clients,
  diagnose, patch, verify gate, events, pipeline, FastAPI dashboard, HTML report.
- Fast suite: 52 passed (~9s). Slow suite (`-m slow`): 13 passed (~150s). `pip install -e .` works; `mldoctor` entry point works.
- All work is committed and pushed (HEAD in sync with origin). 31 commits landed, one per file, all authored `HimanshuSolo`.
- Git discipline: user runs all git commands. One exception was granted for the per-file commit round (done); default back to user-runs-git.

## Repo layout (all under ~/projects/meta-hackathon)
- `src/mldoctor/`: budget, cli, diagnose, events, harness, llm, patch, pipeline, plots, report, runner, server, verify + `static/` (index.html, app.css, app.js)
- `fixtures/`: healthy.py, repro.py, diverge.py (CONTROLLED, known bugs; no leakage fixture per rules)
- `tests/`: test_budget, test_diagnose_patch, test_failures, test_gate, test_live, test_llm, test_mock_symptoms, test_pipeline, test_progress_plots, test_runner, test_server, test_verify; conftest adds `src` to path
- Patched outputs default to `.mldoctor/patched/` (gitignored via `.mldoctor/` + `*.patched.py`). Stale `fixtures/*.patched.py` were deleted with approval.
- `.venv` has torch, sklearn, pytest, fastapi, uvicorn, httpx, matplotlib. Deps declared in `pyproject.toml` dependencies.

## Key decisions (do not regress)
- Child harness never seeds RNGs; scripts seed from MLDOCTOR_SEED. `repro.py` bug = unseeded `random.shuffle`.
- Diverge = non-finite loss OR peak >10x initial, checked BEFORE reproducibility.
- Verify counts: `non_reproducible` = 10 same-seed runs; `diverged` = 5 different seeds (hash identity across seeds is meaningless, so each seed is judged on finite/sane losses). `-k` = baseline runs only (default 5); `--verify-k` overrides verification counts.
- MockClient is keyed by symptom class (repro gets seeding fix; diverged gets LR 0.05 + StandardScaler). Text-only; no image input.
- Live path (OpenAI-style POST `{base}/chat/completions`, env MLDOCTOR_BASE_URL/API_KEY/MODEL, optional MLDOCTOR_AUTH_SCHEME, max_tokens, no retries, kill switch MLDOCTOR_DISABLE_LIVE=1) is UNVERIFIED against Baseten — tested only against fake local servers. Needed for live check: the three env vars + Baseten auth scheme, max_tokens/usage support, image-input format.
- Missing API key errors only for non-local base URLs (local fake-server tests need none).
- Git identity: `HimanshuSolo <himanshu.pv.verma@gmail.com>` — never add any other name; no Co-authored-by trailers.

## PENDING NEXT: frontend polish round (not started)
User asked for Next.js, but standing rules forbid new dependencies and require vanilla HTML/CSS/JS, fully offline (no CDN/fonts/images), max 5 static files each under ~400 lines, targeted edits only. CONFLICT NOT YET RESOLVED with user. Current dashboard is 3 files (index.html, app.css, app.js); allowed additions: charts.js, effects.js.
- Visual: dark "mission control" (navy/charcoal, teal + electric blue accents, amber warnings, red failure, green only for verified success). Monospace data, sans labels. Status never color-only. prefers-reduced-motion disables non-essential motion, keeps info.
- Animation rule: EVERY animation driven by a real SSE server event. Never fake progress; no PASS/success colors/celebration without server `verify_passed` (pipeline emits `verification_completed` with verdict, and `pipeline_completed`); never show LIVE when mode is MOCK.
- Perf: transform/opacity only, no layout thrash, cap canvas/particles, pause when tab hidden. Subtle background (grid/particles) pausing when idle.
- Build order: 1 design system (CSS vars) → 2 pipeline tracker (Reproduce, Classify, Investigate, Patch, Verify; glowing active step, animated connectors) → 3 run grid (K cells light up from `verify_progress`, hover shows hash/peak loss) → 4 hash cells (colors derived from actual hash values; shimmer before patch, snap to matching after) → 5 loss curves (progressive stroke-dashoffset from telemetry, diverge "exploded at step N" marker, before/after toggle) → 6 odometer counter (rolling digits from `verify_progress`) → 7 hypothesis FLIP cards with confidence bars → 8 diff viewer (sequential highlight on `patch_proposed`, red/green lines, panel listing anti-masking checks + results) → 9 verdict stamp (PASS/FAIL from `verification_completed`, FAIL treated as feature) → 10 event log (terminal-style, timestamps, autoscroll, collapsible) → 11 optional "Demo pacing" toggle (MOCK only, fixed server-side delays between events, visible DEMO PACING badge, never in LIVE, default off) → 12 empty/loading/error states (server unreachable, token missing, run active, script not allowed, live not configured).
- Testing: pytest for demo-pacing rule (never in live) + event payload fields UI depends on (`verify_progress`: n_done/n_total/n_failed; per-run hash values). Manual browser checklist (≤10 items): counter+grid progress together, hash match after patch, FAIL patch display, reduced-motion, nothing animates before its event, MOCK/LIVE badge truthful, no non-localhost network (check via DevTools Network tab).
- Final report must include: changed files, assumptions, unverified items, manual checklist, dashboard commands. Do not run git.

## Commands (from repo root)
- Fast tests: `.venv/bin/python -m pytest -q`
- Slow tests: `.venv/bin/python -m pytest -q -m slow`
- CLI: `.venv/bin/mldoctor fix fixtures/repro.py`
- Dashboard: `.venv/bin/mldoctor serve --port 8765` (open printed token URL; start cmd must be smoke-tested in-session; note sandbox namespaces make cross-call reachability checks fail — claim reachability only from a same-call check)
