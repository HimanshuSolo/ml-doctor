"use client";
import { useEffect, useState } from "react";
import { useReducedMotion } from "framer-motion";

// Purely decorative background: animated grid + film grain (inline SVG noise,
// no external assets). Carries no data. Pauses when the tab is hidden and
// never animates under prefers-reduced-motion.
export default function Background() {
  const reduce = useReducedMotion();
  const [hidden, setHidden] = useState(false);
  useEffect(() => {
    const f = () => setHidden(document.hidden);
    document.addEventListener("visibilitychange", f);
    return () => document.removeEventListener("visibilitychange", f);
  }, []);
  const grain = "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/%3E%3C/filter%3E%3Crect width='160' height='160' filter='url(%23n)' opacity='0.5'/%3E%3C/svg%3E\")";
  return (
    <div aria-hidden="true" className="pointer-events-none fixed inset-0 -z-10">
      <div className={`absolute inset-0 opacity-100 ${reduce || hidden ? "" : "bg-grid"}`}
        style={{ backgroundImage: "linear-gradient(color-mix(in srgb, var(--inkc) 7%, transparent) 1px, transparent 1px), linear-gradient(90deg, color-mix(in srgb, var(--inkc) 7%, transparent) 1px, transparent 1px)", backgroundSize: "44px 44px" }} />
      <div className="absolute inset-0 opacity-[0.035]" style={{ backgroundImage: grain }} />
    </div>
  );
}
