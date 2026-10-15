# Three.js

`npm install three && npm install -D @types/three`. Import addons from `three/addons/...`.
Three.js has no game loop or physics: you own both (see `game-loop-and-input.md`). Pin the
version; APIs shift between releases, so check the migration guide when upgrading.

## Renderer, scene, camera, resize

```ts
import * as THREE from 'three';

const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
document.body.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x101820);
const camera = new THREE.PerspectiveCamera(60, innerWidth / innerHeight, 0.1, 200);
camera.position.set(0, 4, 8);

scene.add(new THREE.HemisphereLight(0xffffff, 0x334455, 1.2));
const sun = new THREE.DirectionalLight(0xffffff, 2.5);
sun.position.set(5, 10, 3);
scene.add(sun);

addEventListener('resize', () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.setSize(innerWidth, innerHeight);
});
```

Colour management is on by default (sRGB output, linear working space). Colour textures you load
yourself need `tex.colorSpace = THREE.SRGBColorSpace`; data textures (normal, roughness) stay
linear. GLTFLoader sets this correctly. Lights use physical units: if a scene looks too dark or
too bright, change light intensity, not renderer hacks. Drive rendering from your own
fixed-timestep loop, or `renderer.setAnimationLoop((t) => ...)` with the accumulator inside it.

## Loading glTF (+ Draco, meshopt, KTX2)

Prefer `.glb`. Compress in the export/optimise step (`gltf-transform optimize` or
`gltfpack`), not at runtime. Copy decoders into `public/` once:
`node_modules/three/examples/jsm/libs/draco/gltf/` -> `public/draco/`,
`node_modules/three/examples/jsm/libs/basis/` -> `public/basis/`.

```ts
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { KTX2Loader } from 'three/addons/loaders/KTX2Loader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';

const loader = new GLTFLoader()
  .setDRACOLoader(new DRACOLoader().setDecoderPath('./draco/'))
  .setKTX2Loader(new KTX2Loader().setTranscoderPath('./basis/').detectSupport(renderer))
  .setMeshoptDecoder(MeshoptDecoder);   // only needed for EXT_meshopt_compression files

const gltf = await loader.loadAsync('./assets/hero.glb', (e) => onProgress(e.loaded / (e.total || 1)));
scene.add(gltf.scene);
```

Use Draco OR meshopt for geometry (meshopt also compresses animation, decodes faster); use KTX2
for textures. Cast/receive shadows by traversing `gltf.scene` and setting `castShadow` on meshes.
Clone skinned characters with `SkeletonUtils.clone` from `three/addons/utils/SkeletonUtils.js`
(plain `.clone()` breaks skeleton binding). Cache loaded glTFs and clone, do not reload.
Assets from Blender: see the `gamesmith-blender` skill for export settings.

## Animation mixer

```ts
const mixer = new THREE.AnimationMixer(gltf.scene);
const act: Record<string, THREE.AnimationAction> = {};
for (const clip of gltf.animations) act[clip.name] = mixer.clipAction(clip);

let current = act['Idle'];
current.play();
function play(name: string, fade = 0.2) {
  const next = act[name];
  if (!next || next === current) return;
  next.reset().fadeIn(fade).play();
  current.fadeOut(fade);
  current = next;
}
// each fixed or render step:
mixer.update(dt);   // dt in seconds
```

One-shot clips: `a.setLoop(THREE.LoopOnce, 1); a.clampWhenFinished = true;` and listen to
`mixer.addEventListener('finished', ...)`. Root motion is not applied automatically; drive
position from game code. Animate with `dt`, never wall-clock inside the sim.

## Dispose (prevent GPU leaks)

Removing from the scene does not free GPU memory. Dispose geometries, materials and textures you
own when a level or entity is discarded.

```ts
export function disposeTree(root: THREE.Object3D) {
  root.traverse((o) => {
    const m = o as THREE.Mesh;
    if (!m.isMesh) return;
    m.geometry.dispose();
    for (const mat of Array.isArray(m.material) ? m.material : [m.material]) {
      for (const v of Object.values(mat)) if (v instanceof THREE.Texture) v.dispose();
      mat.dispose();
    }
  });
  root.removeFromParent();
}
```

Do not dispose shared assets still used elsewhere (cached glTF, shared materials): dispose at the
owner level. Also dispose render targets and `PMREMGenerator` results, and call `renderer.dispose()`
when tearing down the whole game. Check for leaks: log `renderer.info.memory` (geometries,
textures) and `renderer.info.render.calls` after restarting a level several times; counts must
return to baseline. Remove event listeners and cancel the loop on teardown.

## Instancing (many identical objects)

```ts
const COUNT = 2000;
const mesh = new THREE.InstancedMesh(new THREE.BoxGeometry(1, 1, 1), new THREE.MeshStandardMaterial(), COUNT);
mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);   // if updated often
const tmp = new THREE.Object3D();                        // reuse: no per-frame allocation
for (let i = 0; i < COUNT; i++) {
  tmp.position.set((i % 50) * 2, 0, Math.floor(i / 50) * 2);
  tmp.updateMatrix();
  mesh.setMatrixAt(i, tmp.matrix);
  mesh.setColorAt(i, new THREE.Color().setHSL(i / COUNT, 0.6, 0.5));
}
mesh.instanceMatrix.needsUpdate = true;
if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
mesh.computeBoundingSphere();   // else frustum culling uses stale bounds
scene.add(mesh);
```

One InstancedMesh = one draw call. For static scenery of different shapes sharing one material,
merge geometry (`BufferGeometryUtils.mergeGeometries`) or use `BatchedMesh`.
Picking instances: `Raycaster.intersectObject(mesh)` returns `instanceId`.

## Physics options

| Option | Notes |
|---|---|
| Rapier (`@dimforge/rapier3d-compat`) | WASM, fast, deterministic builds available, robust character controller; async init |
| cannon-es | Pure JS, simple, fine for small scenes and jams; slower and less stable |
| Custom (raycast + AABB) | Often enough: grid/voxel games, kinematic characters, simple platformers |

```ts
import RAPIER from '@dimforge/rapier3d-compat';
await RAPIER.init();
const world = new RAPIER.World({ x: 0, y: -9.81, z: 0 });
world.timestep = 1 / 60;                                   // match your fixed step
const body = world.createRigidBody(RAPIER.RigidBodyDesc.dynamic().setTranslation(0, 5, 0));
world.createCollider(RAPIER.ColliderDesc.ball(0.5), body);
world.createCollider(RAPIER.ColliderDesc.cuboid(20, 0.5, 20).setTranslation(0, -0.5, 0)); // static ground
// inside game.update(step):  world.step();
// inside render:             const t = body.translation(); mesh.position.set(t.x, t.y, t.z);
```

Step physics inside the fixed `update`, copy transforms to meshes in `render` (interpolate for
smoothness). Keep colliders simple (primitives or convex hulls), not render meshes.

## Performance

- Measure first: `renderer.info.render` (calls, triangles) and the browser Performance panel, on
  the weakest target device. Budgets depend on target hardware: **NOT ASSESSED** until profiled.
- Cut draw calls: share materials, instance repeats, merge static geometry, atlas textures.
- Textures dominate VRAM: an uncompressed RGBA texture costs about width x height x 4 bytes (plus
  roughly a third for mipmaps). Resize art to what is visible; use KTX2/Basis (GPU-compressed)
  for large sets; avoid non-needed 4K maps; reuse one texture across materials.
- Shadows: one shadow-casting light, tight shadow camera frustum, modest map size; bake static light.
- Cap pixel ratio at 2 (lower on mobile if frame time suffers); add a quality setting.
- Frustum culling is on by default; add LOD (`THREE.LOD`) for distant detail; fog hides far clipping.
- Avoid per-frame `new Vector3/Quaternion/Matrix4`; reuse scratch objects.
- Postprocessing (bloom, SSAO) multiplies fill cost: make it optional.
- Set `matrixAutoUpdate = false` on static objects after one `updateMatrix()`.
- Lazy-load levels and decoders; show a loading screen; never block the first frame on everything.
- Detect lost context: listen for `webglcontextlost` / `webglcontextrestored` on the canvas.
