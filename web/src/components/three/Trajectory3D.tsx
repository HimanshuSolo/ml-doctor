"use client";
import { useEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import type { Evidence } from "@/lib/events";
import { normalizeRuns } from "@/lib/helpers";

type P3 = [number, number, number];
function Controls() {
  const { camera, gl } = useThree();
  const ref = useRef<OrbitControls | null>(null);
  useEffect(() => {
    const c = new OrbitControls(camera, gl.domElement);
    c.enableDamping = true; c.dampingFactor = 0.08; ref.current = c;
    return () => { c.dispose(); ref.current = null; };
  }, [camera, gl]);
  useFrame(() => ref.current?.update());
  return null;
}
function RunLine({ pts, color }: { pts: P3[]; color: string }) {
  const obj = useMemo(() => {
    const v = pts.map((p) => new THREE.Vector3(p[0], p[1], p[2]));
    return new THREE.Line(new THREE.BufferGeometry().setFromPoints(v),
      new THREE.LineBasicMaterial({ color }));
  }, [pts, color]);
  return <primitive object={obj} />;
}
// Endpoint markers so even a fully-collapsed (healthy) run renders visibly.
function Endpoints({ runs, color }: { runs: P3[][]; color: string }) {
  const obj = useMemo(() => {
    const v = runs.flatMap((r) => (r.length ? [r[0], r[r.length - 1]] : []))
      .map((p) => new THREE.Vector3(p[0], p[1], p[2]));
    const g = new THREE.BufferGeometry().setFromPoints(v);
    return new THREE.Points(g, new THREE.PointsMaterial({ color, size: 0.14 }));
  }, [runs, color]);
  return <primitive object={obj} />;
}
export default function Trajectory3D({ evidence, paused }: { evidence: Evidence | null; paused: boolean }) {
  const raw: P3[][] = useMemo(() => (evidence?.trajectory ?? []).map((run) =>
    run.filter((p): p is [number, number, number] =>
      !!p && p.every((c) => c !== null && Number.isFinite(c as number)))
      .map((p) => [p[0], p[1], p[2]] as P3)
  ).filter((r) => r.length > 0), [evidence]);
  const { scaled, spread } = useMemo(() => normalizeRuns(raw), [raw]);
  if (!raw.length) return <p className="text-dim text-sm">No trajectory yet.</p>;
  const converged = spread < 1e-6;
  return (
    <div>
      <div style={{ height: 280 }} role="img" aria-label={converged ? "3D trajectory: runs overlap (healthy)" : "3D parameter trajectory fan"}>
        <Canvas frameloop={paused ? "never" : "always"} dpr={[1, 1.5]} camera={{ position: [4, 3, 6], fov: 50 }}>
          <ambientLight intensity={0.8} /><directionalLight position={[4, 6, 5]} intensity={1.1} />
          {scaled.slice(0, 20).map((run, i) => <RunLine key={i} pts={run} color={i === 0 ? "#ff8a5f" : "#b0a696"} />)}
          <Endpoints runs={scaled.slice(0, 20)} color="#f5efe6" />
          <gridHelper args={[7, 7, "#3a322a", "#3a322a"]} position={[0, -2.8, 0]} />
          <axesHelper args={[3.2]} />
          <Controls />
        </Canvas>
      </div>
      <p className="mt-1 font-mono text-xs text-dim">
        {converged
          ? "Runs overlap on one point: identical parameters (healthy) — endpoints marked."
          : "Random 3D projection of parameters; axes have no meaning. Lines fan apart before the patch, collapse after."}
      </p>
    </div>
  );
}
