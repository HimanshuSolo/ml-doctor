"use client";
// Sample gallery: real outcomes from docs/sample-reports (controlled fixtures,
// produced 2026-10-29). Lets a visitor see value before running anything.
const SAMPLES = [
  { fixture: "repro.py", symptom: "non-reproducible", mock: "PASS (mock patch verified)", live: "FAIL — live patch replaced shuffle instead of seeding it" },
  { fixture: "diverge.py", symptom: "diverged", mock: "FAIL — mock patch masked the loss (clip_grad)", live: "FAIL — same masking" },
  { fixture: "leakage.py", symptom: "leakage", mock: "FAIL — mock dedup ran after the split", live: "FAIL — misplaced dedup, honest metric dropped as expected" },
];
export default function SampleGallery() {
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      {SAMPLES.map((s) => (
        <article key={s.fixture} className="spot-card rounded-2xl border border-line bg-panel p-4">
          <p className="font-mono text-xs text-dim">fixtures/{s.fixture}</p>
          <h3 className="mt-1 text-lg font-bold">Symptom: {s.symptom}</h3>
          <p className="mt-2 text-sm"><span className="font-mono text-xs text-dim">MOCK </span>{s.mock}</p>
          <p className="mt-1 text-sm"><span className="font-mono text-xs text-dim">LIVE </span>{s.live}</p>
          <p className="mt-3 font-mono text-[11px] text-dim">Full bundles in docs/sample-reports/ · controlled fixtures, not real-world validation</p>
        </article>
      ))}
    </div>
  );
}
