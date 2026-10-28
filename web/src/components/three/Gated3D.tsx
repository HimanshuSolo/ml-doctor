"use client";
import dynamic from "next/dynamic";
import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { useReducedMotion } from "framer-motion";
import type { Evidence, RunDatum } from "@/lib/events";

const LossRibbons3D = dynamic(() => import("./LossRibbons3D"), { ssr: false });
const RunCubes3D = dynamic(() => import("./RunCubes3D"), { ssr: false });

function webglOk(): boolean {
  try { const c = document.createElement("canvas"); return Boolean(c.getContext("webgl2") || c.getContext("webgl")); } catch { return false; }
}
function usePaused() {
  const ref = useRef<HTMLDivElement>(null);
  const [paused, setPaused] = useState(false);
  useEffect(() => {
    const el = ref.current; if (!el) return;
    let inView = true;
    const update = () => setPaused(!inView || document.hidden);
    const io = new IntersectionObserver(([e]) => { inView = e.isIntersecting; update(); }, { threshold: 0.05 });
    io.observe(el);
    document.addEventListener("visibilitychange", update);
    return () => { io.disconnect(); document.removeEventListener("visibilitychange", update); };
  }, []);
  return { ref, paused };
}
let cachedOk: boolean | null = null;
function webglSnapshot() { if (cachedOk === null) cachedOk = webglOk(); return cachedOk; }
function useWebglOk() {
  return useSyncExternalStore(() => () => {}, webglSnapshot, () => false);
}
export function RibbonsGate({ evidence }: { evidence: Evidence | null }) {
  const reduce = useReducedMotion();
  const { ref, paused } = usePaused();
  const ok = useWebglOk();
  return <div ref={ref}>{reduce || !ok
    ? <p className="text-dim text-sm">3D ribbons off ({reduce ? "reduced motion" : "WebGL unavailable"}) — the 2D loss curves above show the same telemetry.</p>
    : <LossRibbons3D evidence={evidence} paused={paused} />}</div>;
}
export function CubesGate({ runs, verdict }: { runs: RunDatum[]; verdict: string | null }) {
  const reduce = useReducedMotion();
  const { ref, paused } = usePaused();
  const ok = useWebglOk();
  return <div ref={ref}>{reduce || !ok
    ? <p className="text-dim text-sm">3D cubes off ({reduce ? "reduced motion" : "WebGL unavailable"}) — the 2D run grid above shows the same runs.</p>
    : <RunCubes3D runs={runs} verdict={verdict} paused={paused} />}</div>;
}
