import { describe, expect, it } from "vitest";
import { glyphCells, hashColor } from "./helpers";
describe("hash glyph generation (Stage 2)", () => {
  it("same hash gives the same glyph", () => {
    expect(glyphCells("a1b2c3d4")).toEqual(glyphCells("a1b2c3d4"));
    expect(hashColor("deadbeef")).toBe(hashColor("deadbeef"));
  });
  it("different hashes give different glyphs", () => {
    expect(glyphCells("000000")).not.toEqual(glyphCells("ffffff"));
    expect(glyphCells("a1b2c3")).not.toEqual(glyphCells("012c83"));
  });
  it("hash colours stay plum-to-magenta, never green or red", () => {
    for (let i = 0; i < 200; i++) {
      const m = hashColor(i.toString(16).padStart(6, "a")).match(/hsl\((\d+)/);
      const hue = Number(m?.[1]);
      expect(hue).toBeGreaterThanOrEqual(300);
      expect(hue).toBeLessThanOrEqual(335);
    }
    expect(hashColor("19e3a0-green-is-reserved")).not.toContain("hsl(160");
  });
  it("handles empty and short hashes without crashing", () => {
    expect(glyphCells("")).toHaveLength(15);
    expect(glyphCells("ab")).toHaveLength(15);
  });
});

import { normalizeRuns } from "./helpers";
describe("trajectory normalization", () => {
  it("fits far-apart runs into a viewable ball", () => {
    const { scaled, spread } = normalizeRuns([[[0, 0, 0], [1000, 0, 0]], [[0, 0, 0], [0, 1000, 0]]]);
    expect(spread).toBeGreaterThan(0);
    for (const p of scaled.flat()) for (const c of p) expect(Math.abs(c)).toBeLessThanOrEqual(2.51);
  });
  it("collapsed (healthy) runs stay finite with zero spread", () => {
    const { scaled, spread } = normalizeRuns([[[1, 1, 1], [1, 1, 1]], [[1, 1, 1], [1, 1, 1]]]);
    expect(spread).toBe(0);
    for (const p of scaled.flat()) for (const c of p) expect(Number.isFinite(c)).toBe(true);
  });
});
