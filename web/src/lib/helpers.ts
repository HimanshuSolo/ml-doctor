// Colour derived from the real hash value itself (hex -> hue).
export function hashColor(hash: string): string {
  const n = parseInt((hash || "0").slice(0, 6), 16);
  return `hsl(${Number.isFinite(n) ? n % 360 : 0} 70% 45%)`;
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
export function parseDiff(diff: string) {
  return diff.split("\n").map((text) => ({ text, kind: text.startsWith("+") && !text.startsWith("+++") ? "add" as const : text.startsWith("-") && !text.startsWith("---") ? "del" as const : "ctx" as const }));
}
