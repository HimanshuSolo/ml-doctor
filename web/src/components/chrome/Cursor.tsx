"use client";
import { useEffect, useRef } from "react";
// decorative: custom cursor — blue dot with eased trail, grows over interactive elements
export default function Cursor() {
  const dot = useRef<HTMLDivElement>(null);
  const ring = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    if (!window.matchMedia("(hover:hover) and (pointer:fine)").matches) return;
    document.documentElement.classList.add("has-cursor");
    let x = -100, y = -100, rx = -100, ry = -100, raf = 0;
    const move = (e: MouseEvent) => {
      x = e.clientX; y = e.clientY;
      const t = e.target as HTMLElement;
      const hot = Boolean(t.closest("a,button,input,textarea,select,label,[tabIndex]"));
      if (ring.current) ring.current.style.width = ring.current.style.height = hot ? "44px" : "28px";
      document.querySelectorAll<HTMLElement>(".spot-card").forEach((el) => {
        const r = el.getBoundingClientRect();
        el.style.setProperty("--mx", `${e.clientX - r.left}px`);
        el.style.setProperty("--my", `${e.clientY - r.top}px`);
      });
    };
    const loop = () => {
      rx += (x - rx) * 0.16; ry += (y - ry) * 0.16;
      if (dot.current) dot.current.style.transform = `translate(${x}px,${y}px) translate(-50%,-50%)`;
      if (ring.current) ring.current.style.transform = `translate(${rx}px,${ry}px) translate(-50%,-50%)`;
      raf = requestAnimationFrame(loop);
    };
    window.addEventListener("mousemove", move, { passive: true });
    raf = requestAnimationFrame(loop);
    return () => { window.removeEventListener("mousemove", move); cancelAnimationFrame(raf); document.documentElement.classList.remove("has-cursor"); };
  }, []);
  return (<>
    <div ref={ring} aria-hidden="true" className="pointer-events-none fixed left-0 top-0 z-[100] hidden h-7 w-7 rounded-full border border-[#1a4dff] opacity-70 md:block" />
    <div ref={dot} aria-hidden="true" className="pointer-events-none fixed left-0 top-0 z-[100] hidden h-[6px] w-[6px] rounded-full bg-[#1a4dff] md:block" />
  </>);
}
