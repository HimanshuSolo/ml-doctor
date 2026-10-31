"use client";
import { useEffect, useRef } from "react";
import { useReducedMotion } from "framer-motion";
import type { RunDatum } from "@/lib/events";
import type { Verdict } from "@/lib/reducer";

// Cinematic hero field. Two layers, clearly separated:
// - DECORATIVE ONLY: slow drifting dot grid (no data meaning, paused off-screen).
// - DATA-DRIVEN: one streak per verification run from real server telemetry
//   (run_index position, status color, peak_loss height). Nothing draws before
//   its verify_progress event arrives. Verdict ring only from completion.
const STATUS_COLOR: Record<string, string> = {
  identical: "#6f8cff", finite: "#6f8cff", different: "#ffb020", diverged: "#ff4d5e",
};

export default function HeroField({ runs, nTotal, verdict }: { runs: RunDatum[]; nTotal: number; verdict: Verdict | null }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const reduce = useReducedMotion();

  useEffect(() => {
    const cv = ref.current;
    if (!cv) return;
    const ctx = cv.getContext("2d");
    if (!ctx) return;
    let raf = 0;
    let visible = true;
    let t = Math.random() * 100;
    // Decorative drift particles: fixed count, carry no data.
    const motes = Array.from({ length: 42 }, (_, i) => ({ x: (i * 97) % 100, y: (i * 57) % 100, s: 0.4 + ((i * 13) % 10) / 14 }));

    const draw = () => {
      const w = (cv.width = cv.clientWidth * Math.min(devicePixelRatio || 1, 1.5));
      const h = (cv.height = cv.clientHeight * Math.min(devicePixelRatio || 1, 1.5));
      ctx.clearRect(0, 0, w, h);
      // Decorative motes.
      ctx.fillStyle = "rgba(148,163,184,0.16)";
      for (const m of motes) {
        const x = ((m.x + t * m.s) % 100) / 100 * w;
        ctx.fillRect(x, (m.y / 100) * h, 1.5, 1.5);
      }
      // Data streaks: only runs the server actually reported.
      const n = Math.max(runs.length, 1);
      runs.forEach((r, i) => {
        const x = ((i + 0.5) / n) * w;
        const peak = typeof r.peak_loss === "number" && isFinite(r.peak_loss) ? Math.min(r.peak_loss, 10) : 1;
        const bh = (Math.log10(peak + 1) / 1.05) * h * 0.16 + h * 0.03;
        const grad = ctx.createLinearGradient(0, h, 0, h - bh);
        const c = STATUS_COLOR[r.status] ?? "#6f8cff";
        grad.addColorStop(0, c + "22");
        grad.addColorStop(1, c);
        ctx.fillStyle = grad;
        const grow = reduce ? 1 : Math.min(1, 0.25 + t * 0.05);
        ctx.fillRect(x - 3, h - bh * grow, 6, bh * grow);
      });
      if (nTotal > 0 && runs.length === 0) {
        // Honest placeholder: faint track slots for expected runs, no fake data.
        ctx.fillStyle = "rgba(148,163,184,0.10)";
        for (let i = 0; i < Math.min(nTotal, 20); i++) ctx.fillRect(((i + 0.5) / Math.max(nTotal, 1)) * w - 3, h * 0.8, 6, h * 0.06);
      }
      // Verdict ring: only when the server completed verification.
      if (verdict) {
        ctx.strokeStyle = verdict === "PASS" ? "#19e3a0" : "#ff4d5e";
        ctx.lineWidth = 2;
        ctx.globalAlpha = 0.55 + 0.2 * Math.sin(t * 0.8);
        ctx.strokeRect(6, 6, w - 12, h - 12);
        ctx.globalAlpha = 1;
      }
    };

    const tick = () => {
      if (visible && !document.hidden) { t += 0.35; draw(); }
      if (!reduce) raf = requestAnimationFrame(tick);
    };
    draw();
    if (!reduce) raf = requestAnimationFrame(tick);
    const io = new IntersectionObserver(([e]) => { visible = e.isIntersecting; });
    io.observe(cv);
    return () => { cancelAnimationFrame(raf); io.disconnect(); };
  }, [runs, nTotal, verdict, reduce]);

  return <canvas ref={ref} aria-hidden="true" className="pointer-events-none absolute inset-0 h-full w-full" />;
}
