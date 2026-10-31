"use client";
import { useEffect, useRef, useState } from "react";
// Lenis inertial scroll + GSAP ScrollTrigger chapter reveals.
// Scroll drives layout/camera/reveals ONLY — never data or progress.
// "Follow run" glides to the chapter of the real active step; manual scroll pauses it.
export default function SmoothScroll({ activeStep }: { activeStep: number }) {
  const [follow, setFollow] = useState(true);
  const followRef = useRef(true);
  const lenisRef = useRef<{ scrollTo: (t: string, o?: object) => void; destroy: () => void } | null>(null);
  useEffect(()=>{ followRef.current = follow; },[follow]);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let dead = false;
    let cleanup = () => {};
    (async () => {
      const [{ default: Lenis }, gsapMod] = await Promise.all([import("lenis"), import("gsap")]);
      if (dead) return;
      const gsap = gsapMod.gsap ?? gsapMod.default;
      const { ScrollTrigger } = await import("gsap/ScrollTrigger");
      gsap.registerPlugin(ScrollTrigger);
      const lenis = new Lenis({ lerp: 0.09, wheelMultiplier: 1 });
      lenisRef.current = lenis as never;
      lenis.on("scroll", ScrollTrigger.update);
      const tick = (time: number) => lenis.raf(time * 1000);
      gsap.ticker.add(tick);
      gsap.ticker.lagSmoothing(0);
      const pause = () => { if (followRef.current) setFollow(false); };
      window.addEventListener("wheel", pause, { passive: true });
      window.addEventListener("touchmove", pause, { passive: true });
      gsap.utils.toArray<HTMLElement>("[data-reveal]").forEach((el) => {
        gsap.fromTo(el, { opacity: 0, y: 44, clipPath: "inset(0 0 12% 0)" },
          { opacity: 1, y: 0, clipPath: "inset(0 0 0% 0)", duration: 0.9, ease: "power3.out",
            scrollTrigger: { trigger: el, start: "top 88%", once: true } });
      });
      cleanup = () => { window.removeEventListener("wheel", pause); window.removeEventListener("touchmove", pause); gsap.ticker.remove(tick); lenis.destroy(); ScrollTrigger.getAll().forEach((t: { kill: () => void }) => t.kill()); };
    })();
    return () => { dead = true; cleanup(); };
  }, []);

  useEffect(() => {
    if (!follow || activeStep < 0) return;
    const ids = ["#chapter-pipeline", "#chapter-pipeline", "#chapter-investigate", "#chapter-patch", "#chapter-verify"];
    const target = ids[activeStep];
    if (target) lenisRef.current?.scrollTo(target, { offset: -70, duration: 1.4 });
  }, [activeStep, follow]);

  return (
    <button type="button" aria-pressed={follow} onClick={() => setFollow(!follow)}
      className={`fixed bottom-4 right-4 z-[80] rounded-full border px-4 py-2 font-mono text-xs shadow-lg backdrop-blur ${follow ? "border-[#1a4dff] bg-[#1a4dff] text-white" : "border-line bg-panel text-dim"}`}>
      {follow ? "● FOLLOW RUN" : "○ FOLLOW RUN"}
    </button>
  );
}
