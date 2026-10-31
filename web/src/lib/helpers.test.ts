import { describe, expect, it } from "vitest";
import { buildSummary, glyphCells, hashColor } from "./helpers";

describe("hash-derived visuals", () => {
  it("glyph is deterministic and hash-sensitive", () => {
    expect(glyphCells("c603c8")).toEqual(glyphCells("c603c8"));
    expect(glyphCells("c603c8")).not.toEqual(glyphCells("012c83"));
    expect(glyphCells("c603c8")).toHaveLength(15);
  });
  it("colour follows the hash value", () => {
    expect(hashColor("c603c8")).toBe(hashColor("c603c8"));
    expect(hashColor("c603c8")).toMatch(/^hsl\(/);
  });
});

describe("buildSummary", () => {
  const base = { script: "uploads/mine.py", mode: "MOCK", verdict: null, verdictReason: null,
    symptom: null, diagnosis: null, patch: null, patchedPath: null, violations: [],
    nDone: 0, nTotal: 0, nFailed: 0, runs: [], llmCalls: null, callCap: 8, tokensUsed: null };
  it("shows none-yet honestly before completion", () => {
    const t = buildSummary(base as never);
    expect(t).toContain("verdict: none yet");
    expect(t).not.toContain("PASS");
  });
  it("reports FAIL and per-run data after verification", () => {
    const t = buildSummary({ ...base, verdict: "FAIL", verdictReason: "diverged",
      nDone: 5, nTotal: 5, runs: [{ run_index: 0, status: "diverged", param_hash: "ab12", peak_loss: 99 }] } as never);
    expect(t).toContain("FAIL");
    expect(t).toContain("#0 diverged hash=ab12 peak=99");
    expect(t).not.toContain("verdict: PASS");
  });
});

describe("explainPatch + share codec", () => {
  it("returns null before diagnosis, narrates after", async () => {
    const { explainPatch, encodeShare, decodeShare } = await import("./helpers");
    const base = { symptom: "non_reproducible", diagnosis: { culprit: "unseeded shuffle", fix_plan: "seed the RNG", reason: "epoch order differs" },
      patchedPath: "uploads/mine.py", violations: [], verdict: null, verdictReason: null, firstStep: 3,
      nDone: 5, nTotal: 5, metricBefore: null, metricAfter: null, leakageBefore: null, leakageAfter: null };
    expect(explainPatch({ ...base, diagnosis: null })).toBeNull();
    const story = explainPatch(base as never);
    expect(story).toContain("unseeded shuffle");
    expect(story).toContain("step 3");
    expect(decodeShare(encodeShare("# hello"))).toBe("# hello");
    expect(decodeShare("!!!not-valid!!!")).toBeNull();
  });
});
