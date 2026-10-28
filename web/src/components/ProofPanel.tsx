"use client";
import { useState } from "react";
import type { State } from "@/lib/reducer";
import { buildSummary } from "@/lib/helpers";

// "Proof, not prompts": the checklist a plain chatbot can't give you. Every
// row ticks ONLY from server-reported state — pending rows stay visibly
// pending. The Markdown summary is built from the same state for copy-paste.
function Row({ ok, title, detail }: { ok: boolean; title: string; detail: string }) {
  return (
    <li className={`flex gap-2 rounded border px-3 py-2 text-sm ${ok ? "border-tealx/50" : "border-line"}`}>
      <span aria-hidden="true" className={ok ? "text-tealx" : "text-dim"}>{ok ? "✓" : "○"}</span>
      <div><strong className="font-semibold">{title}</strong>
        <p className="font-mono text-xs text-dim">{detail}</p></div>
    </li>
  );
}

export default function ProofPanel({ s }: { s: State }) {
  const [copied, setCopied] = useState(false);
  const rows = [
    { ok: s.symptom !== null, title: "Reproduced from your code", detail: s.symptom ?? "waiting for baseline_completed" },
    { ok: s.diagnosis !== null, title: "Root cause isolated", detail: s.diagnosis ? `${s.diagnosis.culprit} — ${s.diagnosis.reason}` : "waiting for diagnosis" },
    { ok: s.diff !== null, title: "Minimal patch proposed", detail: s.patchedPath ?? "waiting for patch_applied" },
    { ok: s.patch !== null && s.violations.length === 0, title: "Anti-masking gate passed", detail: s.patch ? (s.violations.length === 0 ? "patch fixes the cause, doesn't hide it" : s.violations.join("; ")) : "checked at patch time" },
    { ok: s.nTotal > 0 && s.nDone >= s.nTotal, title: "Verified across runs, not once", detail: s.nTotal > 0 ? `${s.nDone}/${s.nTotal} runs reported` : "waiting for verification_started" },
    { ok: s.verdict !== null, title: s.verdict === "FAIL" ? "Verdict: rejected (shown honestly)" : "Verdict from the server", detail: s.verdict ? `${s.verdict}${s.verdictReason ? ` — ${s.verdictReason}` : ""}` : "only verification_completed sets this" },
  ];
  async function copy() {
    try { await navigator.clipboard.writeText(buildSummary(s)); }
    catch {
      const ta = document.createElement("textarea");
      ta.value = buildSummary(s); document.body.appendChild(ta); ta.select();
      document.execCommand("copy"); ta.remove();
    }
    setCopied(true); setTimeout(() => setCopied(false), 2000);
  }
  return (
    <section aria-label="Proof checklist" className="space-y-2">
      <h3 className="label">Proof, not prompts · what a chatbot can&apos;t give you</h3>
      <ul className="grid gap-2 sm:grid-cols-2">
        {rows.map((r) => <Row key={r.title} {...r} />)}
      </ul>
      <button type="button" onClick={copy} disabled={s.phase === "idle"}
        className="rounded border border-line px-3 py-1.5 font-mono text-xs text-dim hover:text-tealx disabled:opacity-50">
        {copied ? "✓ Copied summary" : "Copy Markdown summary"}</button>
    </section>
  );
}
