import type { Diagnosis, Evidence, Patch, RunDatum, ServerEvent, ServerState } from "./events";
export type Verdict = "PASS" | "FAIL";
export type HistoryEntry = { script: string; verdict: string; passed: boolean; at: number };
export type State = {
  phase: "idle" | "running" | "done" | "failed"; mode: "MOCK" | "LIVE" | null;
  demoPacing: boolean; liveConfigured: boolean; callCap: number | null;
  llmCalls: number | null; tokensUsed: number | null; script: string | null;
  symptom: string | null; reason: string | null; metrics: (number | null)[];
  firstStep: number | null; evidenceBefore: Evidence | null; evidenceAfter: Evidence | null;
  diagnosis: Diagnosis | null; patch: Patch | null; patchedPath: string | null; diff: string | null;
  verifyK: number; verifyMode: string | null; nDone: number; nTotal: number; nFailed: number;
  runs: RunDatum[];
  verdict: Verdict | null; verdictReason: string | null; violations: string[];
  events: ServerEvent[]; history: HistoryEntry[]; error: string | null; lastSeq: number;
};
export const initialState: State = {
  phase: "idle", mode: null, demoPacing: false, liveConfigured: false, callCap: null,
  llmCalls: null, tokensUsed: null, script: null, symptom: null, reason: null, metrics: [],
  firstStep: null, evidenceBefore: null, evidenceAfter: null, diagnosis: null, patch: null,
  patchedPath: null, diff: null, verifyK: 0, verifyMode: null, nDone: 0, nTotal: 0, nFailed: 0, runs: [],
  verdict: null, verdictReason: null, violations: [], events: [], history: [], error: null, lastSeq: -1,
};
export type Action = { kind: "event"; event: ServerEvent } | { kind: "server_state"; state: ServerState } | { kind: "run_started"; script: string } | { kind: "run_error"; error: string } | { kind: "server_unreachable"; error: string } | { kind: "clear_error" } | { kind: "hydrate_history"; history: HistoryEntry[] };
// The single pure function all UI state derives from. Counters only move up
// (Math.max), verdict is set only by verification_completed, mode only by
// pipeline_started.mock / server summary - never by a UI toggle.
export function reduce(state: State, action: Action): State {
  if (action.kind === "hydrate_history") return { ...state, history: action.history.filter((h) => typeof h.script === "string").slice(-20) };
  if (action.kind === "run_started") return { ...initialState, history: state.history, liveConfigured: state.liveConfigured, callCap: state.callCap, demoPacing: state.demoPacing, phase: "running", script: action.script, error: null };
  if (action.kind === "clear_error") return { ...state, error: null };
  if (action.kind === "run_error" || action.kind === "server_unreachable") return { ...state, error: action.error, phase: state.phase === "running" ? "failed" : state.phase };
  if (action.kind === "server_state") {
    let s: State = { ...state, liveConfigured: action.state.live_configured, callCap: action.state.call_cap, demoPacing: Boolean(action.state.demo_pacing) };
    if (action.state.summary) s = { ...s, llmCalls: action.state.summary.llm_calls, tokensUsed: action.state.summary.tokens_used, mode: s.mode ?? (action.state.summary.mock ? "MOCK" : "LIVE") };
    for (const ev of action.state.events) s = reduce(s, { kind: "event", event: ev });
    return s.mode === "LIVE" ? { ...s, demoPacing: false } : s;
  }
  const e = action.event;
  if (e.seq <= state.lastSeq && state.events.some((x) => x.seq === e.seq)) return state;
  const s: State = { ...state, lastSeq: Math.max(state.lastSeq, e.seq), events: [...state.events, e].slice(-200) };
  switch (e.type) {
    case "pipeline_started": return { ...s, phase: "running", script: e.script, mode: e.mock ? "MOCK" : "LIVE", demoPacing: e.mock ? s.demoPacing : false, error: null, verdict: null };
    case "baseline_completed": return { ...s, symptom: e.symptom, reason: e.reason, metrics: e.metrics, firstStep: e.first_step, evidenceBefore: e.evidence };
    case "diagnosed": return { ...s, diagnosis: e.diagnosis };
    case "patch_proposed": return { ...s, patch: e.patch };
    case "patch_applied": return { ...s, patchedPath: e.patched_path, diff: e.diff };
    case "verification_started": return { ...s, verifyK: e.k, verifyMode: e.mode, nTotal: Math.max(s.nTotal, e.k) };
    case "verify_progress": {
      const runs = [...s.runs];
      if (typeof e.run_index === "number" && e.status) {
        runs[e.run_index] = { run_index: e.run_index, param_hash: e.param_hash ?? null, final_loss: e.final_loss ?? null, peak_loss: e.peak_loss ?? null, status: e.status };
      }
      return { ...s, runs, nDone: Math.max(s.nDone, e.n_done), nTotal: Math.max(s.nTotal, e.n_total), nFailed: Math.max(s.nFailed, e.n_failed) };
    }
    case "verification_completed": return { ...s, verdict: e.passed ? "PASS" : "FAIL", verdictReason: e.reason, violations: e.violations ?? [], evidenceAfter: e.evidence ?? s.evidenceAfter, nTotal: Math.max(s.nTotal, e.k), nDone: Math.max(s.nDone, e.k) };
    case "pipeline_completed": return { ...s, phase: "done", history: [...s.history, { script: s.script ?? "?", verdict: e.verdict, passed: e.passed, at: e.ts }] };
    case "pipeline_failed": return { ...s, phase: "failed", error: e.error };
    default: return s;
  }
}
