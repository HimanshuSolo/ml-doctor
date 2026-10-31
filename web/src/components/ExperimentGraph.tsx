"use client";
import { motion } from "framer-motion";
import type { State } from "@/lib/reducer";
// Experiments as nodes on a graph — from real experiment events only.
export default function ExperimentGraph({ s }: { s: State }) {
  const nodes = s.experiments.map((e) => String(e.experiment));
  if (!nodes.length && !s.activeExperiment) return <p className="text-sm text-dim">No experiments yet — nodes appear only on real <span className="font-mono">experiment_result</span> events.</p>;
  const all = s.activeExperiment && !nodes.includes(s.activeExperiment) ? [...nodes, s.activeExperiment] : nodes;
  return (
    <div className="overflow-x-auto rounded-xl border border-line bg-panel2 p-4" role="img" aria-label={`Experiment graph: ${all.join(", ")}`}>
      <div className="flex min-w-max items-center gap-0">
        {all.map((n, i) => (
          <div key={`${n}-${i}`} className="flex items-center">
            <motion.div layout initial={{ opacity: 0, scale: 0.85 }} animate={{ opacity: 1, scale: 1 }}
              className={`rounded-full border px-4 py-2 font-mono text-xs ${n === s.activeExperiment ? "animate-pulse border-[#ffb020] text-[#ffb020]" : "border-[#6f8cff] text-[#6f8cff]"}`}>
              {n}{n === s.activeExperiment ? " · running" : " ✓"}
            </motion.div>
            {i < all.length - 1 && <span aria-hidden="true" className="h-[2px] w-10 bg-[#6f8cff]/60" />}
          </div>
        ))}
      </div>
      <p className="mt-3 font-mono text-[11px] text-dim">{nodes.length} completed · {s.activeExperiment ? `running: ${s.activeExperiment}` : "none running"} — server events only</p>
    </div>
  );
}
