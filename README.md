# MLDoctor
Reproduce, investigate, patch, and verify broken ML training scripts; the verification gate decides success.
Status: Stage 0 approved; scaffold batch pending review (unverified).
Built during the Meta Global AI Developer Hackathon (statement finalized in Stage 11).
## Setup
TODO in Stage 1 (venv + install commands pending approval).
## Env vars
TODO in Stage 3 (keys via env only; `.env.example` then).
## `mldoctor serve`
TODO in Stage 8 (127.0.0.1 only, mock by default).
## How it works
TODO (harness -> runner -> diagnose -> patch -> verify).
## Limitations
TODO (CPU-only, small scripts, no GPU/distributed/notebooks).
## Results
TODO in Stage 11 (honest, including failures).
## Demo script
TODO in Stage 11 (3-minute video).
## Fixtures (CONTROLLED, CPU-only)
`fixtures/repro.py`, `fixtures/diverge.py`, `fixtures/healthy.py`; `leakage.py` deferred until after Stage 5.
# ml-doctor
