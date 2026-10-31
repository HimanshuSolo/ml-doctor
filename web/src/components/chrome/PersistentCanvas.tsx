"use client";
import { useEffect, useRef } from "react";
// decorative: ONE persistent fixed WebGL canvas behind content.
// Shader particle field resolving into a glowing loss-landscape surface.
// Scroll morphs scene/camera/lighting between chapters. Carries NO data.
// Adaptive quality: lowers DPR/particles/bloom below ~50fps; DPR cap 1.5;
// pauses when hidden; static 2D fallback for no-WebGL / reduced motion.
export default function PersistentCanvas({ running }: { running: boolean }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const runRef = useRef(running);
  useEffect(()=>{ runRef.current = running; },[running]);
  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let dead = false;
    let cleanup = () => {};
    (async () => {
      try {
        const THREE = await import("three");
        const { EffectComposer } = await import("three/addons/postprocessing/EffectComposer.js");
        const { RenderPass } = await import("three/addons/postprocessing/RenderPass.js");
        const { UnrealBloomPass } = await import("three/addons/postprocessing/UnrealBloomPass.js");
        if (dead || reduced) return;
        const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true, powerPreference: "high-performance" });
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(55, 1, 0.1, 100);
        camera.position.set(0, 2.2, 9);
        // decorative particle field
        const N = 2600;
        const pos = new Float32Array(N * 3);
        for (let i = 0; i < N; i++) {
          const a = Math.random() * Math.PI * 2, r = 2 + Math.random() * 6;
          pos[i * 3] = Math.cos(a) * r;
          pos[i * 3 + 1] = (Math.random() - 0.5) * 4;
          pos[i * 3 + 2] = Math.sin(a) * r - 2;
        }
        const pgeo = new THREE.BufferGeometry();
        pgeo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
        const pmat = new THREE.ShaderMaterial({
          transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
          uniforms: { uTime: { value: 0 }, uRun: { value: 0 } },
          vertexShader: `uniform float uTime; uniform float uRun; varying float vA;
            void main(){ vec3 p=position; float w=sin(p.x*1.4+uTime*.7)*cos(p.z*1.2+uTime*.5);
            p.y += w*(0.25+uRun*0.7); vA = 0.35+0.65*abs(w);
            vec4 mv=modelViewMatrix*vec4(p,1.0); gl_PointSize=(140.0/-mv.z)*(1.0+uRun);
            gl_Position=projectionMatrix*mv; }`,
          fragmentShader: `varying float vA; void main(){ vec2 c=gl_PointCoord-0.5; float d=length(c);
            if(d>0.5) discard; float a=smoothstep(0.5,0.0,d)*vA;
            gl_FragColor=vec4(vec3(0.10,0.30,1.0), a*0.85); }`,
        });
        const points = new THREE.Points(pgeo, pmat);
        scene.add(points);
        // decorative loss-landscape surface (wireframe plane, shader displaced)
        const surfMat = new THREE.ShaderMaterial({
          wireframe: true, transparent: true, opacity: 0.5,
          uniforms: { uTime: { value: 0 }, uMorph: { value: 0 } },
          vertexShader: `uniform float uTime; uniform float uMorph; varying float vH;
            void main(){ vec3 p=position;
            float h = exp(-pow(p.x*0.55,2.0))*1.4 + sin(p.x*1.6+uTime*0.4)*0.18*cos(p.y*1.4);
            p.z += h*uMorph; vH=h; gl_Position=projectionMatrix*modelViewMatrix*vec4(p,1.0); }`,
          fragmentShader: `varying float vH; void main(){ vec3 c=mix(vec3(0.05,0.12,0.6), vec3(0.35,0.55,1.0), clamp(vH,0.0,1.4));
            gl_FragColor=vec4(c, 0.55); }`,
        });
        const surf = new THREE.Mesh(new THREE.PlaneGeometry(11, 7, 56, 36), surfMat);
        surf.rotation.x = -Math.PI / 2.4;
        surf.position.set(0, -1.6, -1);
        scene.add(surf);
        scene.add(new THREE.AmbientLight(0x8899ff, 0.7));
        const composer = new EffectComposer(renderer);
        composer.addPass(new RenderPass(scene, camera));
        const bloom = new UnrealBloomPass(new THREE.Vector2(1, 1), 0.75, 0.55, 0.82);
        composer.addPass(bloom);
        let w = 0, h = 0, raf = 0, last = performance.now(), acc = 0, frames = 0, quality = 0;
        const resize = () => {
          w = window.innerWidth; h = window.innerHeight;
          renderer.setSize(w, h, false); composer.setSize(w, h);
          camera.aspect = w / h; camera.updateProjectionMatrix();
        };
        resize();
        window.addEventListener("resize", resize);
        const loop = (now: number) => {
          raf = requestAnimationFrame(loop);
          if (document.hidden) return;
          const dt = now - last; last = now;
          acc += dt; frames++;
          if (acc > 1200) { // adaptive quality check ~1.2s
            const fps = (frames / acc) * 1000;
            if (fps < 50 && quality < 2) {
              quality++;
              renderer.setPixelRatio(quality === 1 ? 1.15 : 1);
              bloom.strength = quality === 1 ? 0.5 : 0.3;
              points.visible = quality < 2 || runRef.current;
            }
            acc = 0; frames = 0;
          }
          const scroll = Math.min(1, window.scrollY / Math.max(document.body.scrollHeight - window.innerHeight, 1));
          const t = now * 0.001;
          pmat.uniforms.uTime.value = t;
          pmat.uniforms.uRun.value += ((runRef.current ? 1 : 0) - pmat.uniforms.uRun.value) * 0.04;
          surfMat.uniforms.uTime.value = t;
          surfMat.uniforms.uMorph.value = 0.35 + scroll * 0.9;
          points.rotation.y = t * 0.03 + scroll * 1.4;
          surf.rotation.z = scroll * 0.5;
          camera.position.y = 2.2 - scroll * 1.6;
          camera.position.z = 9 - scroll * 2.4;
          camera.lookAt(0, -0.4, -1);
          composer.render();
        };
        raf = requestAnimationFrame(loop);
        cleanup = () => { cancelAnimationFrame(raf); window.removeEventListener("resize", resize); renderer.dispose(); pgeo.dispose(); };
      } catch { /* WebGL unavailable — polished 2D fallback below stays visible */ }
    })();
    return () => { dead = true; cleanup(); };
  }, []);
  return (
    <>
      {/* decorative 2D fallback (also shows while WebGL loads / when unavailable) */}
      <div aria-hidden="true" className="bg-grid pointer-events-none fixed inset-0 -z-20 opacity-40" />
      <canvas ref={ref} aria-hidden="true" className="pointer-events-none fixed inset-0 -z-10 h-full w-full opacity-70" />
    </>
  );
}
