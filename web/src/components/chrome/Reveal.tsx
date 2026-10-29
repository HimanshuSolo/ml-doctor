"use client";
import { motion, useReducedMotion } from "framer-motion";
import type { ReactNode } from "react";

// Scroll reveal: elements fade, rise and settle as they enter the viewport.
// Stagger siblings with incremental `delay` (40–80ms apart). Replays nothing
// on scroll-up (once), and is fully static under prefers-reduced-motion.
export default function Reveal({ children, delay = 0, y = 36, className }: {
  children: ReactNode; delay?: number; y?: number; className?: string;
}) {
  const reduce = useReducedMotion();
  if (reduce) return <div className={className}>{children}</div>;
  return (
    <motion.div className={className}
      initial={{ opacity: 0, y, scale: 0.985 }}
      whileInView={{ opacity: 1, y: 0, scale: 1 }}
      viewport={{ once: true, margin: "-60px" }}
      transition={{ duration: 0.7, delay, ease: [0.22, 1, 0.36, 1] }}>
      {children}
    </motion.div>
  );
}
export const STAGGER_MS = 70;
