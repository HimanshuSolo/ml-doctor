"use client";
import { motion, useReducedMotion } from "framer-motion";
import type { State } from "@/lib/reducer";

// Pipeline rail: stage position derived only from server-reported state.
const STAGES = ["Reproduce", "Investigate", "Patch", "Verify", "Report"] as const;
export function railIndex(s: State): number {
  if (s.phase === "done") return 4;
  if (s.verdict || s.nTotal > 0) return 3;
  if (s.diff || s.patch) return 2;
  if (s.diagnosis) return 1;
  if (s.symptom || s.phase === "running" || s.phase === "failed") return 0;
  return -1;
}
export default function Rail({ s }: { s: State }) {
  const active = railIndex(s);
  const reduce = useReducedMotion();
  return (
    <nav aria-label="Pipeline stages" className="border-y border-line py-3">
      <ol className="flex flex-col gap-1 sm:flex-row sm:items-center sm:gap-0">
        {STAGES.map((label, i) => {
          const state = i < active || s.phase === "done" ? "done" : i === active ? "active" : "todo";
          return (
            <li key={label} aria-current={state === "active" ? "step" : undefined} className="flex items-center gap-2 sm:flex-1">
              <motion.span aria-hidden="true"
                animate={reduce ? undefined : { scale: state === "active" ? [1, 1.25, 1] : 1 }}
                transition={{ duration: 0.9, repeat: state === "active" && !reduce ? Infinity : 0 }}
                className={`inline-block h-2 w-2 rounded-full ${state === "done" ? "bg-tealx" : state === "active" ? "bg-tealx" : "bg-line"}`} />
              <span className={`label ${state === "todo" ? "" : "!text-ink"}`}>{label}</span>
              {i < STAGES.length - 1 && <span aria-hidden="true" className={`mx-2 hidden h-px flex-1 sm:block ${i < active ? "bg-tealx" : "bg-line"}`} />}
              <span className="sr-only">{state === "done" ? "(completed)" : state === "active" ? "(current)" : "(not reached)"}</span>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
