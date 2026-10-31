"use client";
import { useState } from "react";
import type { State } from "@/lib/reducer";
// Full-screen verdict — triggered ONLY by reduce() verdict, which is set
// only by the server's verification_completed event. PASS and FAIL are
// equally dramatic and deliberate. Dismissible; also in Verify chapter.
export default function VerdictMoment({ s }: { s: State }) {
  const [dismissed, setDismissed] = useState<string | null>(null);
  if (!s.verdict || dismissed === s.verdict) return null;
  const pass = s.verdict === "PASS";
  return (
    <div className={`fixed inset-0 z-[85] grid place-items-center ${pass ? "bg-[#1a4dff] text-white" : "bg-black text-white"}`} role="alertdialog" aria-label={`Verdict: ${s.verdict}`}>
      {pass && <div aria-hidden="true" className="verdict-ring absolute h-64 w-64 rounded-full border-4 border-white/70" />}
      <div className={`relative text-center ${pass ? "" : "verdict-glitch"}`}>
        <p className="font-mono text-xs tracking-[0.35em] opacity-80">{s.mode ?? ""}{s.mode === "MOCK" ? " · SIMULATED" : ""} — SERVER VERDICT</p>
        <p className="mt-3 text-[clamp(4rem,16vw,13rem)] font-bold leading-none tracking-tight">{pass ? "VERIFIED" : "REJECTED"}</p>
        {s.verdictReason && <p className="mx-auto mt-4 max-w-xl px-4 font-mono text-sm opacity-85">{s.verdictReason}</p>}
        <p className="mt-2 font-mono text-xs opacity-70">{s.nDone}/{s.nTotal} runs · {s.nFailed} failed — from verification_completed only</p>
        <button type="button" autoFocus onClick={() => setDismissed(s.verdict)} className="mt-8 rounded-full border border-white/60 px-6 py-2.5 font-mono text-sm hover:bg-white hover:text-black">View evidence ↓</button>
      </div>
    </div>
  );
}
