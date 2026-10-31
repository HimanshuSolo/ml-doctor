"use client";
import { useEffect, useState } from "react";
// decorative: short skippable boot sequence on first load — NOT a progress indicator for real work
export default function Boot() {
  const [show, setShow] = useState(false);
  useEffect(() => {
    try {
      if (sessionStorage.getItem("mldoctor-booted")) return;
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    } catch { return; }
    const on = setTimeout(() => setShow(true), 0);
    const off = setTimeout(() => { setShow(false); try { sessionStorage.setItem("mldoctor-booted", "1"); } catch { /* ignore */ } }, 1400);
    return () => { clearTimeout(on); clearTimeout(off); };
  }, []);
  if (!show) return null;
  return (
    <div className="fixed inset-0 z-[95] grid place-items-center bg-black text-white" role="presentation">
      <div className="text-center">
        <p className="font-mono text-xs tracking-[0.3em] text-[#6f8cff]">MLDOCTOR</p>
        <p className="display-huge mt-2">Prove it.</p>
        <div className="mx-auto mt-6 h-[3px] w-56 origin-left bg-[#2f5bff]" style={{ animation: "boot-bar 1.1s cubic-bezier(0.22,1,0.36,1) forwards" }} />
        <button type="button" className="mt-6 font-mono text-xs text-white/60 underline underline-offset-4 hover:text-white"
          onClick={() => { setShow(false); try { sessionStorage.setItem("mldoctor-booted", "1"); } catch { /* ignore */ } }}>Skip intro</button>
      </div>
    </div>
  );
}
