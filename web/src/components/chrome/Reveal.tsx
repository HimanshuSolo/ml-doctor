"use client";
import { motion, useReducedMotion } from "framer-motion";
import type { ReactNode } from "react";

// Presentation-only scroll reveal (clip-path + 8px settle, 600ms, 40ms stagger
// via `delay`). Never touches state or telemetry; content is visible without JS
// motion because the initial state is fully opaque, only clipped/slid a touch.
export default function Reveal({ children, delay = 0, className }: { children: ReactNode; delay?: number; className?: string }) {
  const reduce = useReducedMotion();
  if (reduce) return <div className={className}>{children}</div>;
  return (
    <motion.div className={className}
      initial={{ opacity: 1, y: 8, clipPath: "inset(0 0 6% 0)" }}
      whileInView={{ opacity: 1, y: 0, clipPath: "inset(0 0 0% 0)" }}
      viewport={{ once: true, margin: "-40px" }}
      transition={{ type: "spring", stiffness: 90, damping: 20, delay }}>
      {children}
    </motion.div>
  );
}
export const STAGGER_MS = 40;
