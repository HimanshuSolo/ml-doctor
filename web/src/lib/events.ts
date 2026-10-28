// Typed events mirroring src/mldoctor/events.py + pipeline.py emit() calls.
// Server is the only source of truth; the UI never invents these.
export type Evidence = { loss_curves: (number | null)[][]; hash_fingerprints: string[][]; metrics: (number | null)[] };
export type Diagnosis = { symptom: string; reason: string; culprit: string; fix_plan: string };
export type Patch = { path: string; rationale: string; edits: { old: string; new: string }[] };
type Base = { seq: number; ts: number };
export type RunStatus = "identical" | "different" | "finite" | "diverged" | "error";
export type RunDatum = { run_index: number; param_hash: string | null; final_loss: number | null; peak_loss: number | null; status: RunStatus };
export type ServerEvent = Base & (
  | { type: "pipeline_started"; script: string; mock: boolean }
  | { type: "baseline_completed"; symptom: string; reason: string; metrics: (number | null)[]; runs: number; first_step: number | null; evidence: Evidence }
  | { type: "diagnosed"; diagnosis: Diagnosis }
  | { type: "patch_proposed"; patch: Patch }
  | { type: "patch_applied"; patched_path: string; diff: string }
  | { type: "verification_started"; k: number; required_k: number; mode: string }
  | { type: "verify_progress"; n_done: number; n_total: number; n_failed: number; run_index?: number; param_hash?: string | null; final_loss?: number | null; peak_loss?: number | null; status?: RunStatus }
  | { type: "verification_completed"; passed: boolean; verdict: string; reason: string; symptom: string | null; violations: string[]; k: number; metrics: (number | null)[]; seeds?: number[]; mode?: string; evidence?: Evidence }
  | { type: "pipeline_completed"; passed: boolean; verdict: string }
  | { type: "pipeline_failed"; error: string }
);
export type ServerState = { running: boolean; summary: Summary | null; events: ServerEvent[]; mock: boolean; live_configured: boolean; call_cap: number; allowed_dir: string; demo_pacing?: boolean };
export type Summary = { script: string; passed: boolean; mock: boolean; llm_calls: number; tokens_used: number; classification?: { symptom: string; reason: string }; verification?: { passed: boolean; reason: string; violations: string[]; k: number } | null; error?: string };
