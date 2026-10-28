import { describe, expect, it } from "vitest";
import { resolveApiBase } from "./api";

describe("api base resolution", () => {
  it("dev on port 3000 defaults to the backend address", () => {
    expect(resolveApiBase(undefined, "3000")).toBe("http://127.0.0.1:8765");
  });
  it("one-process pages call the same origin on any port", () => {
    expect(resolveApiBase(undefined, "8765")).toBe("");
    expect(resolveApiBase(undefined, "8789")).toBe("");
    expect(resolveApiBase(undefined, "")).toBe("");
  });
  it("explicit env always wins and trims the trailing slash", () => {
    expect(resolveApiBase("http://127.0.0.1:9000/", "3000")).toBe("http://127.0.0.1:9000");
    expect(resolveApiBase("http://127.0.0.1:9000", "8765")).toBe("http://127.0.0.1:9000");
  });
});
