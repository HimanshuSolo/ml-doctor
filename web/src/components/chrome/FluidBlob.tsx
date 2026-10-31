"use client";
import { motion, useReducedMotion, useScroll, useTransform } from "framer-motion";

// DECORATIVE ONLY spiral: an Archimedean spiral drawn as crisp SVG vector
// (not a blurred canvas), so it is visible on light and dark surfaces.
// Slow rotation respects prefers-reduced-motion. Carries no data meaning.
function spiralPath(cx: number, cy: number, turns: number, maxR: number): string {
  const steps = Math.floor(turns * 90);
  let d = "";
  for (let i = 0; i <= steps; i++) {
    const t = (i / steps) * turns * Math.PI * 2;
    const r = (t / (turns * Math.PI * 2)) * maxR;
    const x = cx + Math.cos(t) * r;
    const y = cy + Math.sin(t) * r;
    d += `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)} `;
  }
  return d;
}
const DOTS = Array.from({ length: 9 }, (_, i) => {
  const t = 0.7 + i * 0.72;
  const r = (t / (Math.PI * 2 * 3.4)) * 150;
  return { x: 170 + Math.cos(t) * r, y: 170 + Math.sin(t) * r, r: 3.5 - i * 0.22 };
});

export default function FluidBlob() {
  const reduce = useReducedMotion();
  const { scrollYProgress } = useScroll();
  const rotate = useTransform(scrollYProgress, [0, 1], [0, 140]);
  const y = useTransform(scrollYProgress, [0, 1], [0, 90]);
  return (
    <motion.div aria-hidden="true" style={reduce ? undefined : { rotate, y }}
      className="pointer-events-none absolute -top-2 right-0 hidden w-[min(42vw,380px)] opacity-90 sm:block">
      <svg viewBox="0 0 340 340" className="h-auto w-full" role="presentation">
        <circle cx="170" cy="170" r="158" fill="none" stroke="var(--line)" strokeWidth="1" strokeDasharray="3 7" />
        <circle cx="170" cy="170" r="112" fill="none" stroke="var(--line)" strokeWidth="1" />
        <g className={reduce ? undefined : "spiral-spin"}>
          <path d={spiralPath(170, 170, 3.4, 150)} fill="none" stroke="var(--accent)" strokeWidth="2.25" strokeLinecap="round" opacity="0.85" />
          <path d={spiralPath(170, 170, 3.4, 150)} fill="none" stroke="var(--accent2)" strokeWidth="7" strokeLinecap="round" opacity="0.10" />
          {DOTS.map((d, i) => <circle key={i} cx={d.x} cy={d.y} r={Math.max(d.r, 1.6)} fill={i % 3 === 2 ? "var(--amberx, #ffb020)" : "var(--accent)"} opacity={0.95 - i * 0.07} />)}
          <circle cx="170" cy="170" r="5" fill="var(--accent)" />
        </g>
      </svg>
    </motion.div>
  );
}
