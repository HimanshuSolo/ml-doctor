// Colour derived from the real hash value itself (hex -> hue).
export function hashColor(hash: string): string {
  const n = parseInt((hash || "0").slice(0, 6), 16);
  const hue = 300 + ((Number.isFinite(n) ? n : 0) % 36); // 300-335 plum->magenta; green/red/ember reserved
  return `hsl(${hue} 55% 64%)`;
}
// 5x5 mirrored glyph cells derived only from the hash's own hex digits:
// identical hashes render identical glyphs, different hashes almost never do.
export function glyphCells(hash: string): boolean[] {
  const hex = (hash || "0").padEnd(4, "0");
  const bits: boolean[] = [];
  for (let i = 0; i < 15; i++) {
    const nibble = parseInt(hex[i % hex.length], 16);
    bits.push(((nibble >> (i % 4)) & 1) === 1);
  }
  return bits;
}
// First step where a curve goes non-finite or exceeds 10x its first loss (server rule).
export function explodedStep(curves: (number | null)[][]): number | null {
  for (const c of curves) {
    const first = c.find((v) => v !== null && Number.isFinite(v)) ?? null;
    for (let i = 0; i < c.length; i++) {
      const v = c[i];
      if (v === null || !Number.isFinite(v)) return i;
      if (first !== null && Math.abs(v) > Math.max(1, Math.abs(first)) * 10) return i;
    }
  }
  return null;
}
// Markdown run summary built only from reducer state (same source as ProofPanel).
export function buildSummary(s: {
  script: string | null; mode: "MOCK" | "LIVE" | null; verdict: "PASS" | "FAIL" | null;
  verdictReason: string | null; symptom: string | null;
  diagnosis: { culprit: string; fix_plan: string } | null; patch: unknown;
  patchedPath: string | null; violations: string[];
  nDone: number; nTotal: number; nFailed: number;
  runs: { run_index: number; status: string; param_hash: string | null; peak_loss: number | null }[];
  llmCalls: number | null; callCap: number | null; tokensUsed: number | null;
}): string {
  return [
    `# MLDoctor result — ${s.script ?? "no run yet"}`,
    `- mode: ${s.mode ?? "—"} · verdict: ${s.verdict ?? "none yet"}${s.verdictReason ? ` (${s.verdictReason})` : ""}`,
    `- symptom: ${s.symptom ?? "—"}`,
    `- diagnosis: ${s.diagnosis ? `${s.diagnosis.culprit} — ${s.diagnosis.fix_plan}` : "—"}`,
    `- patch: ${s.patchedPath ?? "—"} · anti-masking: ${s.patch ? (s.violations.length === 0 ? "passed" : `VIOLATIONS: ${s.violations.join("; ")}`) : "—"}`,
    `- verification: ${s.nDone}/${s.nTotal}${s.nFailed ? ` (${s.nFailed} failed)` : ""}`,
    `- per-run: ${s.runs.filter(Boolean).map((r) => `#${r.run_index} ${r.status} hash=${r.param_hash ?? "?"} peak=${r.peak_loss ?? "?"}`).join(" | ") || "—"}`,
    `- budget: calls ${s.llmCalls ?? "—"}${s.callCap ? `/${s.callCap}` : ""} · tokens ${s.tokensUsed ?? "—"}`,
  ].join("\n");
}
export function parseDiff(diff: string) {
  return diff.split("\n").map((text) => ({ text, kind: text.startsWith("+") && !text.startsWith("+++") ? "add" as const : text.startsWith("-") && !text.startsWith("---") ? "del" as const : "ctx" as const }));
}

// Plain-language patch story built only from reducer state (same source as ProofPanel).
export function explainPatch(s: {
  symptom: string | null; diagnosis: { culprit: string; fix_plan: string; reason: string } | null;
  patchedPath: string | null; violations: string[]; verdict: "PASS" | "FAIL" | null;
  verdictReason: string | null; firstStep: number | null; nDone: number; nTotal: number;
  metricBefore: number | null; metricAfter: number | null; leakageBefore: number | null; leakageAfter: number | null;
}): string | null {
  if (!s.diagnosis) return null;
  const bits = [
    `The run was classified as ${s.symptom ?? "an unknown symptom"}.`,
    `Root cause: ${s.diagnosis.culprit} -- ${s.diagnosis.reason}`,
    `The patch${s.patchedPath ? ` (${s.patchedPath})` : ""} applies this fix: ${s.diagnosis.fix_plan}.`,
  ];
  if (s.firstStep !== null) bits.push(`Training first went wrong at step ${s.firstStep}.`);
  if (s.leakageBefore !== null && s.leakageAfter !== null) bits.push(`Overlapping rows fell from ${s.leakageBefore} to ${s.leakageAfter}.`);
  if (s.metricBefore !== null && s.metricAfter !== null) bits.push(`The honest metric moved from ${s.metricBefore.toFixed(4)} to ${s.metricAfter.toFixed(4)} (a drop is expected when leakage is removed).`);
  if (s.verdict) bits.push(`Verification across ${s.nDone}/${s.nTotal} runs: ${s.verdict}${s.verdictReason ? ` -- ${s.verdictReason}` : ""}.`);
  else if (s.violations.length) bits.push(`The anti-masking gate rejected it: ${s.violations.join("; ")}.`);
  return bits.join(" ");
}
// Shareable run link payload: base64url of the Markdown summary (client-side only).
export function encodeShare(summary: string): string {
  return btoa(unescape(encodeURIComponent(summary))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}
export function decodeShare(code: string): string | null {
  try {
    const b64 = code.replace(/-/g, "+").replace(/_/g, "/");
    return decodeURIComponent(escape(atob(b64)));
  } catch { return null; }
}

// Fit 3D trajectory runs into a viewable ball: center on the bounding box,
// scale the longest half-extent to FIT_R, guard fully-collapsed runs.
export const TRAJ_FIT_R = 2.5;
export function normalizeRuns(runs: [number, number, number][][]): { scaled: [number, number, number][][]; spread: number } {
  const pts = runs.flat();
  if (!pts.length) return { scaled: [], spread: 0 };
  const lo = [Infinity, Infinity, Infinity], hi = [-Infinity, -Infinity, -Infinity];
  for (const p of pts) for (let i = 0; i < 3; i++) {
    if (!Number.isFinite(p[i])) continue;
    lo[i] = Math.min(lo[i], p[i]); hi[i] = Math.max(hi[i], p[i]);
  }
  const center = [(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2];
  const spread = Math.hypot(hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]);
  const half = Math.max((hi[0] - lo[0]) / 2, (hi[1] - lo[1]) / 2, (hi[2] - lo[2]) / 2, 1e-9);
  const k = TRAJ_FIT_R / half;
  return {
    spread,
    scaled: runs.map((run) => run.map((p) => [
      (p[0] - center[0]) * k, (p[1] - center[1]) * k, (p[2] - center[2]) * k,
    ] as [number, number, number])),
  };
}
