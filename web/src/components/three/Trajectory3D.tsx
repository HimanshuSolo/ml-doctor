"use client";
import { useMemo } from "react";
import * as THREE from "three";
import { Canvas } from "@react-three/fiber";
import type { Evidence } from "@/lib/events";

type P3 = [number | null, number | null, number | null];
function Line({ pts, color }: { pts: P3[]; color: string }) {
  const obj = useMemo(() => {
    const v = pts.filter((p) => p.every((c) => c !== null && Number.isFinite(c as number)))
      .map((p) => new THREE.Vector3(p[0] as number, p[1] as number, p[2] as number));
    return new THREE.Line(new THREE.BufferGeometry().setFromPoints(v),
      new THREE.LineBasicMaterial({ color }));
  }, [pts, color]);
  return <primitive object={obj} />;
}
export default function Trajectory3D({ evidence, paused }: { evidence: Evidence | null; paused: boolean }) {
  const traj = evidence?.trajectory ?? [];
  const flat = traj.flat().filter((p) => p && p.every((c) => c !== null)) as [number, number, number][];
  const maxAbs = Math.max(...flat.map((p) => Math.max(...p.map(Math.abs))), 1e-6);
  const scaled: P3[][] = traj.map((run) => run.map((p) => {
    if (!p || p.some((c) => c === null)) return [null, null, null];
    return [(p[0] as number) / maxAbs * 3, (p[1] as number) / maxAbs * 3, (p[2] as number) / maxAbs * 3];
  }));
  if (!traj.length) return <p className="text-dim text-sm">No trajectory yet.</p>;
  return (
    <div>
      <div style={{ height: 280 }} role="img" aria-label="3D parameter trajectory fan">
        <Canvas frameloop={paused ? "never" : "always"} dpr={[1, 1.5]} camera={{ position: [4, 3, 6], fov: 50 }}>
          <ambientLight intensity={0.8} /><directionalLight position={[4, 6, 5]} intensity={1.1} />
          {scaled.slice(0, 20).map((run, i) => <Line key={i} pts={run} color={i === 0 ? "#ff8a5f" : "#b0a696"} />)}
          <gridHelper args={[6, 6, "#3a322a", "#171310"]} />
        </Canvas>
      </div>
      <p className="mt-1 font-mono text-xs text-dim">Random 3D projection of parameters; axes have no meaning. Lines fan apart before the patch, collapse after.</p>
    </div>
  );
}
