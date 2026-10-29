# MLDoctor — Progress (state as of 2026-10-29, stages 0,A,B,C,D,E,F,G done)

## Where things stand
- Backend + Next.js frontend done. Fast: 86 passed (~20s). Slow: 13 passed (~128s).
  Web: tsc 0 errors, eslint 0 errors, vitest 17 passed, build + build:copy pass.
- Stage B: fixed experiment menu (overfit_one_batch dropped — cannot be done
  reliably without editing the script); diagnose loop max 3, events wired.
- Stage C: fixtures/leakage.py (CONTROLLED); split row-hash overlap in harness;
  classify leakage when overlap_ratio > 0.05 (natural load_digits ~2.7% ignored).
- Stage D: --vision + dashboard toggle; one real probe timed out once (no retry);
  live vision is text-only in practice; reports state whether an image was sent.
- Stage E: proof bundle JSON+HTML, `recheck`, `check` (exit codes), CI sample
  (UNTESTED in real CI), patch export (.patch + .md PR text). Never auto-push.
- Stage F: investigation timeline, leakage view, trajectory fan 3D (random
  projection, axes meaningless), verification cubes, loss ribbons, first-divergence
  scrubber, proof panel + share card. All from reduce() only.
- Stage G: live fixes repro/diverge/leakage all FAIL honestly (gates held);
  docs/sample-reports/ has the table. Mock leakage/repro smokes: PASS except
  live misplacement ("dedup after split" flagged; .mldoctor/patched kept).

## Key decisions (do not regress)
- Child env allowlist (harness.child_env()); secrets never forwarded.
- Live needs --max-tokens >=4096 (reasoning eats small budgets). No retries.
- Leakage verify: overlap == 0; dedup must be before split; metric drop is honest.

## Real calls (session total: 9 of 30; Stage G cap 18 not reached)
1 probe + 2 repro + 2 diverge + 3 leakage(+investigate) + 1 vision probe (timeout).

## Frontend rework (2026-10-29, uncommitted)
- Single slim sticky header: removed floating nav pill, merged status into `web/src/components/hud.tsx`; removed Pricing page + Diagnose/Verify/Proof stubs (dead-end routes, only `/` remains).
- Palette: neon teal/electric blue replaced by warm paper + deep-teal accent (`--accent`), light default, `[data-theme="dark"]` flip.
- Hero spiral: crisp SVG `FluidBlob` with scroll-linked rotate/parallax; grid background follows theme.
- Scroll animations: section fade-up reveals (`Reveal`), staggered blocks, animated section underlines, hero word-clip reveal, button hover/tap, thicker scroll-progress hairline. Fixed hydration #418 (token check deferred to mount); removed full-screen route overlay.
- Verified: eslint 0 errors, `tsc --noEmit` clean, vitest 17 passed, `npm run build:copy` OK; headless screenshots of top + full page reviewed. Working tree still uncommitted — commit only on explicit ask.
