"use client";
import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import type { RunDatum } from "@/lib/events";
import { hashColor } from "@/lib/helpers";

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
const BAD = new Set(["different", "diverged", "error"]);
function Cube({ run, i, verdict, onHover }: { run: RunDatum; i: number; verdict: string | null; onHover: (r: RunDatum | null) => void }) {
  const mesh = useRef<THREE.Mesh>(null);
  const bad = BAD.has(run.status);
  const targetRot = bad ? Math.PI : 0;
  const color = bad ? "#e86a6a" : verdict === "PASS" ? "#3ecf8e" : run.param_hash ? hashColor(run.param_hash) : "#38bdf8";
  useFrame((_, dt) => { if (mesh.current) mesh.current.rotation.y += (targetRot - mesh.current.rotation.y) * Math.min(dt * 5, 1); });
  return (
    <mesh ref={mesh} position={[(i % 5) * 1.1 - 2.2, Math.floor(i / 5) * -1.1 + 0.6, 0]}
      onPointerOver={(e) => { e.stopPropagation(); onHover(run); }} onPointerOut={() => onHover(null)}>
      <boxGeometry args={[0.82, 0.82, 0.82]} />
      <meshStandardMaterial color={color} roughness={0.35} metalness={0.15} />
    </mesh>
  );
}
export default function RunCubes3D({ runs, verdict, paused }: { runs: RunDatum[]; verdict: string | null; paused: boolean }) {
  const [hover, setHover] = useState<RunDatum | null>(null);
  if (!runs.filter(Boolean).length) return <p className="text-dim text-sm">No verification runs yet for 3D.</p>;
  return (
    <div>
      <div style={{ height: 260 }} role="img" aria-label="3D verification run cubes">
        <Canvas frameloop={paused ? "never" : "always"} dpr={[1, 1.5]} camera={{ position: [0, 1.5, 6.5], fov: 50 }}>
          <ambientLight intensity={0.7} /><directionalLight position={[4, 6, 5]} intensity={1.2} />
          {runs.filter(Boolean).slice(0, 20).map((r, i) => <Cube key={r.run_index} run={r} i={i} verdict={verdict} onHover={setHover} />)}
          <Controls />
        </Canvas>
      </div>
      <p className="mt-1 font-mono text-xs text-dim" aria-live="polite">
        {hover ? `run ${hover.run_index + 1}: ${hover.status} · hash ${hover.param_hash ?? "—"} · peak loss ${hover.peak_loss ?? "—"} · final ${hover.final_loss ?? "—"}` : "Hover a cube for its hash and peak loss. Colour comes from the run's real hash / server status."}
      </p>
    </div>
  );
}
