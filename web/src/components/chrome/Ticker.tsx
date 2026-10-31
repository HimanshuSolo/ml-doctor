"use client";
import type { State } from "@/lib/reducer";
// Marquee ticker built from the real event log (reduce().events) — no invented entries.
export default function Ticker({ s }: { s: State }) {
  const items = s.events.length
    ? s.events.slice(-14).map((e) => `#${e.seq} ${e.type} · ${new Date(e.ts * 1000).toLocaleTimeString()}`)
    : ["NO SERVER EVENTS YET — TICKER FILLS FROM REAL EVENTS ONLY"];
  const row = [...items, ...items];
  return (
    <div className="themed-chrome overflow-hidden border-y border-line py-2" aria-label="Live event ticker">
      <div className="ticker-track flex w-max gap-8 whitespace-nowrap font-mono text-[11px] tracking-wider">
        {row.map((t, i) => <span key={i}><span className="text-[#6f8cff]">◆</span> {t}</span>)}
      </div>
    </div>
  );
}
