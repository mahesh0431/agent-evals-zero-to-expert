// 3D hero: the agent-eval loop as a living system (three.js r128 from cdnjs).
// Task samples flow into the agent, the agent acts on the environment through tools,
// transcripts flow to graders, scores flow into the metric.
(function () {
  const host = document.querySelector(".hero3d");
  if (!host || !window.THREE) { if (host) host.innerHTML = '<div class="fallback">Interactive 3D view needs WebGL.</div>'; return; }
  const T = window.THREE;
  const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim() || "#888";
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;

  let renderer;
  try { renderer = new T.WebGLRenderer({ antialias: true, alpha: true }); }
  catch (e) { host.innerHTML = '<div class="fallback">Interactive 3D view needs WebGL.</div>'; return; }
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  host.prepend(renderer.domElement);
  const scene = new T.Scene();
  const camera = new T.PerspectiveCamera(42, 1, 0.1, 100);
  camera.position.set(0, 3.6, 8.2);
  camera.lookAt(0, -0.4, 0);
  scene.add(new T.AmbientLight(0xffffff, 0.75));
  const dl = new T.DirectionalLight(0xffffff, 0.7); dl.position.set(4, 8, 6); scene.add(dl);

  const world = new T.Group(); scene.add(world);

  function label(text, color) {
    const c = document.createElement("canvas"); c.width = 512; c.height = 128;
    const g = c.getContext("2d");
    g.font = "700 54px Inter, system-ui, sans-serif"; g.textAlign = "center"; g.textBaseline = "middle";
    g.fillStyle = color; g.fillText(text, 256, 64);
    const tex = new T.CanvasTexture(c);
    const s = new T.Sprite(new T.SpriteMaterial({ map: tex, transparent: true, depthWrite: false }));
    s.scale.set(3.2, 0.8, 1);
    return s;
  }

  // nodes around the loop
  const nodes = {
    task:   { pos: [-4.2, 0, 1.2],  color: "--good",   name: "Tasks" },
    agent:  { pos: [0, 0.4, 0],     color: "--accent", name: "Agent", big: true },
    env:    { pos: [3.6, 0, 2.0],   color: "--warn",   name: "Environment" },
    grader: { pos: [2.6, 0, -2.8],  color: "--violet", name: "Graders" },
    metric: { pos: [-2.6, 0, -2.8], color: "--bad",    name: "Metrics" },
  };
  const meshes = [];
  Object.values(nodes).forEach(n => {
    const col = new T.Color(css(n.color));
    const geo = n.big ? new T.IcosahedronGeometry(0.9, 1) : new T.SphereGeometry(0.5, 32, 16);
    const m = new T.Mesh(geo, new T.MeshStandardMaterial({ color: col, roughness: 0.35, metalness: 0.1, flatShading: !!n.big, emissive: col, emissiveIntensity: 0.18 }));
    m.position.set(...n.pos); world.add(m); meshes.push(m); n.mesh = m;
    const halo = new T.Mesh(new T.RingGeometry(n.big ? 1.15 : 0.7, n.big ? 1.22 : 0.75, 48), new T.MeshBasicMaterial({ color: col, transparent: true, opacity: 0.45, side: T.DoubleSide }));
    halo.rotation.x = -Math.PI / 2; halo.position.set(n.pos[0], n.pos[1] - (n.big ? 0.9 : 0.5), n.pos[2]); world.add(halo);
    const l = label(n.name, css(n.color)); l.position.set(n.pos[0], n.pos[1] + (n.big ? 1.8 : 1.0), n.pos[2]); world.add(l);
  });

  // flows (curves with travelling particles)
  const flows = [
    ["task", "agent", "--good", 0.6],
    ["agent", "env", "--accent", 0.9],
    ["env", "agent", "--warn", 0.9],
    ["agent", "grader", "--violet", 0.6],
    ["grader", "metric", "--violet", 0.5],
    ["metric", "task", "--bad", 0.35],
  ];
  const particles = [];
  flows.forEach(([a, b, color, rate], fi) => {
    const A = new T.Vector3(...nodes[a].pos), B = new T.Vector3(...nodes[b].pos);
    const mid = A.clone().add(B).multiplyScalar(0.5);
    mid.y += 1.1 + (fi % 2) * 0.4;
    if (a === "env" && b === "agent") mid.y = -1.0;
    const curve = new T.QuadraticBezierCurve3(A, mid, B);
    const col = new T.Color(css(color));
    const line = new T.Line(new T.BufferGeometry().setFromPoints(curve.getPoints(48)), new T.LineBasicMaterial({ color: col, transparent: true, opacity: 0.35 }));
    world.add(line);
    const count = Math.round(6 * rate) + 2;
    for (let i = 0; i < count; i++) {
      const p = new T.Mesh(new T.SphereGeometry(0.075, 10, 8), new T.MeshBasicMaterial({ color: col }));
      p.userData = { curve, t: i / count, speed: 0.12 + 0.08 * rate };
      world.add(p); particles.push(p);
    }
  });

  // floor grid
  const grid = new T.GridHelper(16, 16, new T.Color(css("--line")), new T.Color(css("--line")));
  grid.position.y = -1.6; grid.material.transparent = true; grid.material.opacity = 0.5; world.add(grid);

  // ambient dust: many small eval "samples" drifting around the loop
  const dustGeo = new T.BufferGeometry(); const N = 420; const arr = new Float32Array(N * 3);
  for (let i = 0; i < N; i++) { const r = 3 + Math.random() * 6, a = Math.random() * Math.PI * 2; arr[i * 3] = Math.cos(a) * r; arr[i * 3 + 1] = -1.2 + Math.random() * 4; arr[i * 3 + 2] = Math.sin(a) * r; }
  dustGeo.setAttribute("position", new T.BufferAttribute(arr, 3));
  const dust = new T.Points(dustGeo, new T.PointsMaterial({ color: new T.Color(css("--accent-2")), size: 0.05, transparent: true, opacity: 0.55 }));
  world.add(dust);

  // pointer drag to rotate
  let drag = false, lastX = 0, rotV = reduce ? 0 : 0.0018, targetRot = 0;
  host.addEventListener("pointerdown", e => { drag = true; lastX = e.clientX; host.setPointerCapture(e.pointerId); });
  host.addEventListener("pointerup", () => drag = false);
  host.addEventListener("pointermove", e => { if (drag) { targetRot += (e.clientX - lastX) * 0.008; lastX = e.clientX; } });

  function resize() {
    const w = host.clientWidth, h = host.clientHeight;
    renderer.setSize(w, h, false); camera.aspect = w / h;
    camera.position.z = w < 600 ? 12.5 : 8.2; camera.lookAt(0, -0.4, 0);
    camera.updateProjectionMatrix();
  }
  addEventListener("resize", resize); resize();

  let visible = true;
  new IntersectionObserver(es => visible = es[0].isIntersecting).observe(host);
  let last = performance.now();
  function frame(now) {
    const dt = Math.min(0.05, (now - last) / 1000); last = now;
    if (visible) {
      targetRot += rotV;
      world.rotation.y += (targetRot - world.rotation.y) * 0.08;
      if (!reduce) {
        particles.forEach(p => { p.userData.t = (p.userData.t + p.userData.speed * dt) % 1; p.position.copy(p.userData.curve.getPoint(p.userData.t)); });
        nodes.agent.mesh.rotation.y += dt * 0.4; dust.rotation.y -= dt * 0.03; nodes.agent.mesh.rotation.x += dt * 0.15;
        meshes.forEach((m, i) => m.position.y = Object.values(nodes)[i].pos[1] + Math.sin(now / 900 + i) * 0.08);
      } else {
        particles.forEach(p => p.position.copy(p.userData.curve.getPoint(p.userData.t)));
      }
      renderer.render(scene, camera);
    }
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
})();
