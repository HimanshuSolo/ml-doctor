import { describe, expect, it } from "vitest";
import { initialState, reduce } from "./reducer";
import type { ServerEvent } from "./events";
let seq = 0;
const ev = (p: Record<string, unknown>): ServerEvent => ({ seq: seq++, ts: 1, ...p }) as ServerEvent;
const started = () => ev({ type: "pipeline_started", script: "fixtures/repro.py", mock: true });
describe("reduce", () => {
  it("verdict stays null until verification_completed (pass or fail)", () => {
    let s = reduce(initialState, { kind: "event", event: started() });
    s = reduce(s, { kind: "event", event: ev({ type: "verify_progress", n_done: 3, n_total: 10, n_failed: 0 }) });
    expect(s.verdict).toBeNull();
    const pass = reduce(s, { kind: "event", event: ev({ type: "verification_completed", passed: true, verdict: "PASS", reason: "ok", symptom: "healthy", violations: [], k: 10, metrics: [] }) });
    expect(pass.verdict).toBe("PASS");
    const fail = reduce(s, { kind: "event", event: ev({ type: "verification_completed", passed: false, verdict: "FAIL", reason: "masking", symptom: null, violations: ["empty patch"], k: 0, metrics: [] }) });
    expect(fail.verdict).toBe("FAIL"); expect(fail.violations).toEqual(["empty patch"]);
  });
  it("counters only increase from events", () => {
    let s = reduce(initialState, { kind: "event", event: started() });
    s = reduce(s, { kind: "event", event: ev({ type: "verify_progress", n_done: 5, n_total: 10, n_failed: 1 }) });
    s = reduce(s, { kind: "event", event: ev({ type: "verify_progress", n_done: 2, n_total: 10, n_failed: 0 }) });
    expect(s.nDone).toBe(5); expect(s.nFailed).toBe(1);
  });
  it("mode badge follows the server, not a toggle", () => {
    expect(initialState.mode).toBeNull();
    expect(reduce(initialState, { kind: "event", event: started() }).mode).toBe("MOCK");
    seq = 100;
    expect(reduce(initialState, { kind: "event", event: ev({ type: "pipeline_started", script: "x.py", mock: false }) }).mode).toBe("LIVE");
  });
  it("failed verification shows FAIL and never PASS", () => {
    let s = reduce(initialState, { kind: "event", event: started() });
    s = reduce(s, { kind: "event", event: ev({ type: "verify_progress", n_done: 1, n_total: 2, n_failed: 1, run_index: 0, param_hash: "abc123", final_loss: 9, peak_loss: 9, status: "different" }) });
    expect(s.verdict).toBeNull(); // no verdict before the completion event
    s = reduce(s, { kind: "event", event: ev({ type: "verification_completed", passed: false, verdict: "FAIL", reason: "hashes differ", symptom: "non_reproducible", violations: [], k: 2, metrics: [] }) });
    expect(s.verdict).toBe("FAIL"); expect(s.verdict).not.toBe("PASS");
  });
  it("per-run cells appear only when their verify_progress event arrives", () => {
    let s = reduce(initialState, { kind: "event", event: started() });
    s = reduce(s, { kind: "event", event: ev({ type: "verification_started", k: 3, required_k: 3, mode: "same-seed" }) });
    expect(s.runs.filter(Boolean)).toHaveLength(0); expect(s.nTotal).toBe(3);
    s = reduce(s, { kind: "event", event: ev({ type: "verify_progress", n_done: 1, n_total: 3, n_failed: 0, run_index: 0, param_hash: "a1b2c3", final_loss: 0.5, peak_loss: 2, status: "identical" }) });
    expect(s.runs.filter(Boolean)).toHaveLength(1);
    expect(s.runs[0]).toMatchObject({ param_hash: "a1b2c3", status: "identical", peak_loss: 2 });
    expect(s.runs[1]).toBeUndefined();
    s = reduce(s, { kind: "event", event: ev({ type: "verify_progress", n_done: 2, n_total: 3, n_failed: 1, run_index: 1, param_hash: "ffff00", final_loss: 0.6, peak_loss: 2, status: "different" }) });
    expect(s.runs.filter(Boolean)).toHaveLength(2); expect(s.runs[1].status).toBe("different");
  });
  it("demo pacing never appears in LIVE mode", () => {
    const liveState = { running: false, summary: null, events: [], mock: false, live_configured: true, call_cap: 8, allowed_dir: ".", demo_pacing: true };
    let s = reduce(initialState, { kind: "server_state", state: liveState });
    s = reduce(s, { kind: "event", event: ev({ type: "pipeline_started", script: "x.py", mock: false }) });
    expect(s.mode).toBe("LIVE"); expect(s.demoPacing).toBe(false);
    const mockS = reduce({ ...initialState, demoPacing: true }, { kind: "event", event: ev({ type: "pipeline_started", script: "x.py", mock: true }) });
    expect(mockS.demoPacing).toBe(true);
  });
  it("grid sizes to the server verification_started count (10 / 5)", () => {
    let s = reduce(initialState, { kind: "event", event: ev({ type: "verification_started", k: 10, required_k: 10, mode: "same-seed" }) });
    expect(s.nTotal).toBe(10); expect(s.runs.filter(Boolean)).toHaveLength(0);
    s = reduce(initialState, { kind: "event", event: ev({ type: "verification_started", k: 5, required_k: 5, mode: "seeds" }) });
    expect(s.nTotal).toBe(5);
  });
  it("hydrate_history restores persisted history, caps at 20, drops bad rows", () => {
    const good = Array.from({ length: 25 }, (_, i) => ({ script: `f${i}.py`, verdict: "PASS", passed: true, at: i }));
    const s = reduce(initialState, { kind: "hydrate_history", history: [...good, { script: 42, verdict: "x", passed: false, at: 99 }] as never });
    expect(s.history).toHaveLength(20);
    expect(s.history.every((h) => typeof h.script === "string")).toBe(true);
    expect(s.phase).toBe("idle"); // hydration never starts or completes a run
  });
  it("duplicate seq is ignored; pipeline_failed surfaces the error", () => {
    const e1 = started(); let s = reduce(initialState, { kind: "event", event: e1 });
    expect(reduce(s, { kind: "event", event: e1 }).events).toHaveLength(1);
    s = reduce(s, { kind: "event", event: ev({ type: "pipeline_failed", error: "boom" }) });
    expect(s.phase).toBe("failed"); expect(s.error).toBe("boom"); expect(s.verdict).toBeNull();
  });
});
