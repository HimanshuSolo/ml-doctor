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

function drawShareCard(s: State): HTMLCanvasElement {
  const c = document.createElement("canvas");
  c.width = 720; c.height = 400;
  const g = c.getContext("2d");
  if (!g) return c;
  g.fillStyle = "#05070c"; g.fillRect(0, 0, 720, 400);
  g.fillStyle = "#eef2ff"; g.font = "bold 26px system-ui, sans-serif";
  g.fillText("MLDoctor proof", 28, 52);
  g.font = "15px ui-monospace, monospace"; g.fillStyle = "#8b97b8";
  const stamp = `${s.mode ?? "—"}${s.mode === "MOCK" ? " (simulated)" : ""}`;
  g.fillText(`mode: ${stamp}`, 28, 92);
  g.fillText(`script: ${s.script ?? "—"}`, 28, 118);
  g.fillText(`symptom: ${s.symptom ?? "—"}`, 28, 144);
  g.fillStyle = s.verdict === "PASS" ? "#19e3a0" : "#ff4d5e";
  g.font = "bold 34px system-ui, sans-serif";
  g.fillText(s.verdict ?? "NO VERDICT YET", 28, 205);
  g.fillStyle = "#8b97b8"; g.font = "14px ui-monospace, monospace";
  g.fillText(`verification: ${s.nDone}/${s.nTotal} runs, ${s.nFailed} failed`, 28, 245);
  if (s.verdictReason) g.fillText(s.verdictReason.slice(0, 74), 28, 270);
  g.fillText("Generated client-side from real run state only.", 28, 372);
  return c;
}

export default function ProofPanel({ s }: { s: State }) {
  const [copied, setCopied] = useState(false);
  const [recheckCopied, setRecheckCopied] = useState(false);
  const [cardUrl, setCardUrl] = useState<string | null>(null);
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
      <div className="flex flex-wrap gap-2">
        <button type="button" onClick={copy} disabled={s.phase === "idle"}
          className="rounded border border-line px-3 py-1.5 font-mono text-xs text-dim hover:text-tealx disabled:opacity-50">
          {copied ? "✓ Copied summary" : "Copy Markdown summary"}</button>
        <button type="button" disabled={s.phase === "idle"} onClick={() => {
          const a = document.createElement("a");
          a.href = "/api/proof.json"; a.download = "mldoctor-proof.json"; a.click();
        }} className="rounded border border-line px-3 py-1.5 font-mono text-xs text-dim hover:text-tealx disabled:opacity-50">
          Download proof bundle (.json)</button>
        <button type="button" disabled={s.phase === "idle"} onClick={async () => {
          const cmd = "mldoctor recheck mldoctor-proof.json";
          try { await navigator.clipboard.writeText(cmd); } catch { /* clipboard unavailable */ }
          setRecheckCopied(true); setTimeout(() => setRecheckCopied(false), 2000);
        }} className="rounded border border-line px-3 py-1.5 font-mono text-xs text-dim hover:text-tealx disabled:opacity-50">
          {recheckCopied ? "✓ Copied" : "Copy recheck command"}</button>
        <button type="button" disabled={s.phase === "idle"} onClick={() => setCardUrl(drawShareCard(s).toDataURL("image/png"))}
          className="rounded border border-line px-3 py-1.5 font-mono text-xs text-dim hover:text-tealx disabled:opacity-50">
          Render share card (PNG)</button>
      </div>
      <p className="font-mono text-xs text-dim">Recheck: <code>mldoctor recheck mldoctor-proof.json</code></p>
      {cardUrl ? (
        <figure className="space-y-1">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={cardUrl} alt={`Share card: ${s.mode ?? "no mode"} ${s.verdict ?? "no verdict"}`} className="max-w-full rounded border border-line" />
          <figcaption className="font-mono text-xs text-dim">Stamped {s.mode ?? "—"}{s.mode === "MOCK" ? " (simulated)" : ""} · rendered from real state only.</figcaption>
        </figure>
      ) : null}
    </section>
  );
}
