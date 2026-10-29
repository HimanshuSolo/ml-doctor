"use client";
import { motion, useReducedMotion, useScroll, useSpring } from "framer-motion";
import type { State } from "@/lib/reducer";
import { stepIndex } from "@/components/hud";

// Pinned scroll-story rail. Sticky while the story sections scroll past it.
// - DATA: stage name, real verify progress bar, real verdict — all from state.
// - DECORATIVE ONLY: the thin scroll-linked hairline (page position, not data).
const NAMES = ["Reproduce", "Classify", "Investigate", "Patch", "Verify"];
const ANCHORS = ["#h-repro", "#h-inv", "#h-patch", "#h-verify", "#h-report"];

export default function StoryPinned({ s }: { s: State }) {
  const reduce = useReducedMotion();
  const { scrollYProgress } = useScroll();
  const hairline = useSpring(scrollYProgress, { stiffness: 90, damping: 22 });
  const active = stepIndex(s);
  const pct = s.nTotal > 0 ? Math.min(100, Math.round((100 * s.nDone) / s.nTotal)) : 0;

  return (
    <div className="relative -mx-4 border-y border-line bg-panel/70 px-4 py-2">
      <div className="mx-auto flex max-w-6xl items-center gap-3">
        <ol className="flex flex-1 items-center gap-1 overflow-x-auto">
          {NAMES.map((n, i) => (
            <li key={n} className="flex items-center gap-1 whitespace-nowrap">
              <a href={ANCHORS[Math.min(i, ANCHORS.length - 1)]}
                aria-current={i === active ? "step" : undefined}
                className={`rounded px-2 py-1 text-xs transition-colors duration-300 ${i === active ? "bg-tealx/15 text-tealx outline outline-1 outline-tealx/60" : i < active ? "text-tealx" : "text-dim"}`}>
                {i < active ? "✓ " : ""}{i + 1} · {n}
              </a>
              {i < NAMES.length - 1 && <span aria-hidden="true" className="text-line">—</span>}
            </li>
          ))}
        </ol>
        <div className="hidden items-center gap-2 font-mono text-xs text-dim sm:flex" role="status">
          <span className="h-1 w-24 overflow-hidden rounded bg-panel2">
            <motion.span className="block h-full bg-tealx" animate={{ width: `${pct}%` }} transition={reduce ? { duration: 0 } : { type: "spring", stiffness: 120, damping: 20 }} />
          </span>
          {s.nDone}/{s.nTotal || "—"}{s.verdict ? ` · ${s.verdict}` : ""}
        </div>
      </div>
      {/* Decorative only: page scroll position hairline, not telemetry. */}
      {!reduce && <motion.div aria-hidden="true" className="absolute inset-x-0 bottom-0 h-[2px] origin-left bg-tealx" style={{ scaleX: hairline }} />}
    </div>
  );
}
