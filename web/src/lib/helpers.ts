// Colour derived from the real hash value itself (hex -> hue).
export function hashColor(hash: string): string {
  const n = parseInt((hash || "0").slice(0, 6), 16);
  const hue = 210 + ((Number.isFinite(n) ? n : 0) % 91); // 210-300 blue->magenta; green/red reserved for pass/fail
  return `hsl(${hue} 70% 62%)`;
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
