"use client";
import { useEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import type { Evidence } from "@/lib/events";

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
// y: clamped log scale, so a diverging run visibly shoots up without flattening the rest.
const yOf = (v: number) => Math.min(Math.log10(1 + Math.max(v, 0)) * 2.2, 4.5);
function Ribbon({ curve, index }: { curve: (number | null)[]; index: number }) {
  const geom = useMemo(() => {
    const pts = curve.map((v, j) => new THREE.Vector3((j / Math.max(curve.length - 1, 1)) * 8 - 4, v === null ? 4.5 : yOf(v), index * 0.75));
    const verts: number[] = [], idx: number[] = [];
    pts.forEach((p, j) => { verts.push(p.x, p.y, p.z - 0.16, p.x, p.y, p.z + 0.16); if (j > 0) { const a = (j - 1) * 2; idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2); } });
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(verts, 3));
    g.setIndex(idx); g.computeVertexNormals();
    return g;
  }, [curve, index]);
  return <mesh geometry={geom}><meshStandardMaterial color={index === 0 ? "#2ee6c8" : `hsl(${204 + index * 18}, 70%, 60%)`} side={THREE.DoubleSide} roughness={0.45} metalness={0.1} /></mesh>;
}
export default function LossRibbons3D({ evidence, paused }: { evidence: Evidence | null; paused: boolean }) {
  if (!evidence?.loss_curves?.length) return <p className="text-dim text-sm">No telemetry yet for 3D.</p>;
  return (
    <div style={{ height: 320 }} role="img" aria-label="3D loss ribbons from real telemetry">
      <Canvas frameloop={paused ? "never" : "always"} dpr={[1, 1.5]} camera={{ position: [6, 4.5, 9], fov: 50 }}>
        <ambientLight intensity={0.7} /><directionalLight position={[5, 8, 5]} intensity={1.2} />
        {evidence.loss_curves.slice(0, 12).map((c, i) => <Ribbon key={i} curve={c} index={i} />)}
        <gridHelper args={[10, 10, "#1c2530", "#10161f"]} position={[0, -0.02, 2]} />
        <Controls />
      </Canvas>
    </div>
  );
}
