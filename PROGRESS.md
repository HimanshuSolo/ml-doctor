# MLDoctor — Progress
## Done
- Scaffold: LICENSE (MIT, `[Your Name]` placeholder), .gitignore, README skeleton, pyproject.toml.
- Chunk A: feasibility probe, harness, runner, CLI `run`, 3 CONTROLLED fixtures, 8 tests.
- Env: .venv (Python 3.14.7) + torch 2.14.1+cpu, sklearn 1.9.1, pytest 9.1.1, numpy 2.5.4.
## Works (verified by runs below)
- Probe: 15/15 steps, no gaps, IDENTICAL same-seed hashes (default 6 threads).
- pytest 8/8: healthy/repro/diverge fixtures classify correctly; healthy not flagged.
- CLI: `run` prints healthy / non_reproducible@step0 on fixtures (k=2 smoke).
## Not verified
- `pip install -e .` (needs install approval; using PYTHONPATH=src + conftest).
- Chunks B/C/D (not built). Leakage + multi-experiment loop dropped per new rules.
## Next step (exact)
- You review git diff, then say "start chunk B" (llm, budget, diagnose, patch, verify).
## Key decisions
- Wrap optimizer instances via Optimizer.__init__ (base step patch is a no-op).
- Child never seeds RNGs (scripts seed from MLDOCTOR_SEED; avoids masking bugs).
- Diverge = non-finite OR peak loss >10x initial; checked before reproducibility.
- Param hash stdlib-only (uint8 view + sha256); crashed runs report `error`.
## Commands (from repo root)
- Tests: `.venv/bin/python -m pytest tests/ -q`
- Probe: `.venv/bin/python feasibility/harness_probe.py`
- CLI: `PYTHONPATH=src .venv/bin/python -m mldoctor.cli run fixtures/healthy.py -k 2`
## Update (chunks B+C, one pass)
- B: budget, llm (mock + OpenAI-compatible vs fake server), diagnose, patch, verify gate (stats-aware k, anti-masking diff, hand-written correct/masking patches per fixture). Text-only; image pending Baseten docs.
- C: events (EventBus), pipeline, CLI `fix` terminal summary; FastAPI serve (127.0.0.1, per-launch token, allowed-dir, SSE) + 3-file dashboard (static/index.html, app.css, app.js), Mock badge always visible. HTML report + run history skipped.
- Deps approved+installed in .venv: fastapi, uvicorn, httpx. Tests: 39 passed.
- Commands: `.venv/bin/python -m pytest tests/ -q` | `PYTHONPATH=src .venv/bin/python -m mldoctor.cli fix fixtures/repro.py -k 2` | `PYTHONPATH=src .venv/bin/python -m mldoctor.cli serve --port 8765` (open printed token URL)
- Mock keyed by symptom (diverged: LR 0.05 + StandardScaler); patched defaults to .mldoctor/; verify spec: non_reproducible=10 same-seed, diverged=5 seeds. 42 tests pass.
- Parts 1-6 round: gate expanded (epochs/dataset/model/try-except/NaN/hardcode/check-removal/empty), slow marker split, verify_progress+evidence+plots, live env path offline-tested, pip install -e . works, HTML report, README rewrite. Fast 52 passed (~9s), slow 13 passed (~150s).
