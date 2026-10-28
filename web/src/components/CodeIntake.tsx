"use client";
import { useState } from "react";
import { apiUrl } from "@/lib/api";

// End-user code intake: run a bundled fixture OR paste your own ML script.
// Pasted code is saved via POST /api/scripts (token-gated, basename-only,
// .py, 200k cap — enforced server-side) and the returned relative path feeds
// the normal pipeline. Nothing runs that the server didn't save and report.
export default function CodeIntake({ script, setScript, fixtures, getToken, onError, disabled }: {
  script: string; setScript: (v: string) => void; fixtures: string[];
  getToken: () => string; onError: (msg: string) => void; disabled: boolean;
}) {
  const [tab, setTab] = useState<"fixture" | "paste">("fixture");
  const [name, setName] = useState("my_model.py");
  const [code, setCode] = useState("");
  const [saving, setSaving] = useState(false);

  async function saveAndUse() {
    const token = getToken();
    if (!token) { onError("Token missing. Paste the ?token= printed by `mldoctor serve`."); return; }
    setSaving(true);
    try {
      const r = await fetch(apiUrl("/api/scripts"), { method: "POST",
        headers: { "X-MLDoctor-Token": token, "Content-Type": "application/json" },
        body: JSON.stringify({ name: name.trim(), content: code }) });
      if (!r.ok) { onError(`Could not save script: ${await r.text()}`); return; }
      setScript((await r.json()).script as string);
      setTab("fixture");
    } catch (e) { onError(`Server unreachable: ${e instanceof Error ? e.message : String(e)}`); }
    finally { setSaving(false); }
  }

  return (
    <div className="space-y-2">
      <div className="flex gap-2" role="tablist" aria-label="Script source">
        {(["fixture", "paste"] as const).map((t) => (
          <button key={t} type="button" role="tab" aria-selected={tab === t} onClick={() => setTab(t)}
            className={`rounded border px-3 py-1 text-sm ${tab === t ? "border-tealx text-tealx" : "border-line text-dim"}`}>
            {t === "fixture" ? "Use a fixture" : "Paste my own code"}</button>
        ))}
      </div>
      {tab === "fixture" ? (
        <>
          <label className="block text-sm">Script path (inside allowed dir)
            <input value={script} onChange={(e) => setScript(e.target.value)} disabled={disabled}
              className="mt-1 w-full rounded border border-line bg-panel2 p-2 font-mono text-sm" /></label>
          {fixtures.length > 0 && (
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <span className="text-dim">Fixtures:</span>
              {fixtures.map((f) => <button key={f} type="button" aria-pressed={script === f} onClick={() => setScript(f)}
                className={`rounded border px-2 py-1 font-mono text-xs ${script === f ? "border-bluex text-bluex" : "border-line text-dim"}`}>{f}</button>)}
            </div>
          )}
        </>
      ) : (
        <div className="space-y-2 rounded border border-line bg-panel2 p-3">
          <label className="block text-sm">Filename (saved under uploads/)
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="my_model.py"
              className="mt-1 w-full rounded border border-line bg-panel p-2 font-mono text-sm" /></label>
          <label className="block text-sm">Paste your training script
            <textarea value={code} onChange={(e) => setCode(e.target.value)} rows={8} spellCheck={false}
              placeholder="import torch …" aria-describedby="paste-hint"
              className="mt-1 w-full rounded border border-line bg-panel p-2 font-mono text-xs leading-5" /></label>
          <p id="paste-hint" className="font-mono text-xs text-dim">{code.length.toLocaleString()} / 200,000 chars · saved to uploads/ on the server, then run like any fixture</p>
          <button type="button" onClick={saveAndUse} disabled={saving || !code.trim() || disabled}
            className="rounded bg-tealx px-4 py-2 text-sm font-semibold text-black disabled:opacity-50">
            {saving ? "Saving…" : "Save & use this script"}</button>
        </div>
      )}
    </div>
  );
}
