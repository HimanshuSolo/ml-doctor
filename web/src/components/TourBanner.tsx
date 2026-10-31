"use client";
import { useEffect, useState } from "react";
// First-visit guided tour: 3 steps + one button that plays the existing
// full demo (repro -> diverge -> healthy) through the real API.
const KEY = "mldoctor-tour-seen";
export default function TourBanner({ onPlay }: { onPlay: () => void }) {
  const [show, setShow] = useState(false);
  useEffect(() => { // deferred mount check + subscription to external storage
    let first = false;
    try { first = !localStorage.getItem(KEY); } catch { /* storage unavailable */ }
    if (!first) return;
    const t = setTimeout(() => setShow(true), 0);
    return () => clearTimeout(t);
  }, []);
  if (!show) return null;
  const dismiss = () => { try { localStorage.setItem(KEY, "1"); } catch { /* ignore */ } setShow(false); };
  return (
    <div className="rounded-2xl border border-line bg-panel p-4" role="dialog" aria-label="Guided tour">
      <p className="label">New here? 60-second tour</p>
      <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm">
        <li>Press <strong>Play full demo</strong> — three real pipeline runs, back to back.</li>
        <li>Follow the stations: Reproduce → Classify → Investigate → Patch → Verify.</li>
        <li>End on the verdict: green only when the server really verified the fix.</li>
      </ol>
      <div className="mt-3 flex flex-wrap gap-2">
        <button type="button" onClick={() => { onPlay(); dismiss(); }} className="rounded-full bg-[#bc4a1a] px-4 py-2 text-sm font-semibold text-white hover:opacity-90">▶ Play full demo</button>
        <button type="button" onClick={dismiss} className="rounded-full border border-line px-4 py-2 font-mono text-xs text-dim">Dismiss</button>
      </div>
    </div>
  );
}
