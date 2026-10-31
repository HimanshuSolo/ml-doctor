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
  it("handles empty and short hashes without crashing", () => {
    expect(glyphCells("")).toHaveLength(15);
    expect(glyphCells("ab")).toHaveLength(15);
  });
});
