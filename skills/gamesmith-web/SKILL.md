---
name: gamesmith-web
description: Build browser games in TypeScript/JavaScript with Vite, Canvas 2D, Phaser 3 or Three.js, covering scaffold, fixed-timestep loop, input, audio, assets, build and deploy. Use when the user wants a game that runs in a web browser, an HTML5 or itch.io web or jam game, a Canvas, Phaser, Three.js, PixiJS, Babylon.js or Kaplay project, or a quick single-file playable prototype.
license: MIT
metadata:
  pack: gamesmith
---

# gamesmith-web

Ship playable browser games. Design, scope and process live in the `gamesmith` skill; 3D asset
creation and glTF export live in `gamesmith-blender`. This skill covers the web engineering.

## Workflow

1. Detect: read `package.json`, lockfile, `vite.config.*`, `src/`. Reuse the existing framework and
   package manager. Never swap engines in an existing project unless asked.
2. Pick a framework with the table below (new projects only). State the choice in one line.
3. Scaffold or extend, then get a running window before adding features.
4. Build vertical slice first: input -> movement -> one goal -> win/lose -> restart.
5. Verify (see Deliverables), then report.

## Framework decision

| Need | Pick | Why |
|---|---|---|
| Jam game, throwaway prototype, < ~500 lines, no build step | Vanilla Canvas 2D, single HTML file | Zero tooling; copy `assets/single-file-prototype.html` |
| Serious 2D (sprites, tilemaps, physics, scenes, audio) | Phaser 3 | Batteries included: loader, scenes, Arcade physics, tilemaps, cameras |
| 3D, or 2D with heavy shaders/lighting | Three.js | Thin renderer; you own loop, physics, UI |
| 2D rendering only, you bring your own game logic | PixiJS | Fast WebGL/WebGPU renderer, no game framework |
| 3D with built-in physics, editor, GUI, XR | Babylon.js | Full engine, larger bundle |
| Tiny 2D jam game with minimal API | Kaplay (successor of Kaboom) | Very short code, quick to learn |
| Pure logic/board/card/text game | Vanilla TS + DOM or Canvas | No engine needed |

Defaults: 2D -> Phaser 3, 3D -> Three.js, tiny -> single file. Do not mix two renderers on one canvas.
If the user names a framework, use it.

## Default scaffold (Vite + TypeScript)

```bash
npm create vite@latest my-game -- --template vanilla-ts
cd my-game && npm install
npm install phaser            # or: npm install three && npm install -D @types/three
npm install -D vitest         # logic tests
npm run dev                   # http://localhost:5173
```

Check the current Vite docs for the Node version it requires. Layout:

```
index.html            # one <canvas> or #app container, viewport meta, no inline game code
vite.config.ts        # base: './' so the build works from any subfolder (itch.io, Pages)
public/               # copied verbatim (not hashed): favicon, large audio, draco/basis decoders
src/main.ts           # bootstrap only
src/sim/              # pure game logic: no DOM, no Phaser/Three imports -> unit-testable
src/render/           # drawing, scenes, meshes
src/input.ts         # input abstraction
src/assets.ts         # preload + typed asset keys
tests/                # vitest (sim) + playwright (smoke)
```

Keep the simulation separate from rendering: `sim` takes `(state, input, dt)` and returns/mutates
state. Rendering reads state. This is what makes the game testable and the loop swappable.

## Core rules (checklist)

- **Loop**: `requestAnimationFrame` + fixed-timestep accumulator + render interpolation. Clamp the
  frame delta (e.g. 0.25 s) to avoid the spiral of death. Never use `setInterval` for gameplay.
  Phaser owns its own loop: tune `fps`/physics settings instead of writing one. Snippet:
  `references/game-loop-and-input.md`.
- **Time units**: `dt` in seconds; speeds in units per second. Never "per frame" constants.
- **Input**: map raw devices (keyboard `event.code`, gamepad, touch, pointer) to named actions.
  Gameplay code reads actions only. Clear held keys on `blur`.
- **Pause**: pause on `visibilitychange` (hidden) and window `blur`; mute audio; reset `last` time on
  resume so no giant delta appears. Offer an explicit pause key (P / Esc) and a touch button.
- **Audio**: browsers block sound until a user gesture. Create/resume `AudioContext` (or let Phaser
  unlock) on the first `pointerdown`/`keydown`; show a "click to start" screen if audio matters.
  Pool short sounds; never `new Audio()` per shot. Persist a mute toggle.
- **Assets**: preload everything before first gameplay frame with a progress bar; fail loudly with
  the asset name on error. Prefer import-time URLs (hashed by Vite) for small art; `public/` for
  big blobs. Prefer sprite atlases, `.ogg`+`.mp3` (or `.m4a`) fallbacks, glTF `.glb` for 3D.
- **Canvas sizing**: logical game resolution fixed; backing store = CSS size x `devicePixelRatio`
  (cap at 2 for perf). Handle `resize`/orientation; letterbox instead of stretching. Use
  `image-rendering: pixelated` + integer scale for pixel art.
- **No per-frame allocations**: no `{}`/`[]`/closures/`new Vector3()` in `update`/`render`. Pool
  bullets and particles; reuse temp vectors; avoid `forEach`/spread in hot paths. Allocation causes GC hitches.
- **Determinism**: all gameplay randomness through one seeded RNG (below); cosmetic randomness may
  use `Math.random`. Log the seed so bugs replay. Never read wall-clock time inside `sim`.
- **State & saves**: serializable plain-data state; versioned save key (see `references/ship-web.md`).
- **Mobile**: touch controls, `touch-action: none` on the canvas, `100dvh`, no hover-only UI,
  test at least one low-end profile. Respect `prefers-reduced-motion` for shake/flash.
- **Cleanup**: remove listeners and dispose GPU resources when a scene ends (Three.js especially).
- **Accessibility basics**: remappable or alternative controls, readable font sizes, do not rely on
  color alone, no flashing > 3 Hz.

Seeded RNG (mulberry32, 32-bit state):

```ts
export function rng(seed: number) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296; // [0,1)
  };
}
```

Asset preload pattern (images + audio buffers, with progress):

```ts
export async function preload(urls: Record<string, string>, onProgress: (p: number) => void) {
  const out: Record<string, ImageBitmap | AudioBuffer> = {};
  const ctx = new AudioContext(); // decoding works before unlock; only playback needs a gesture
  let done = 0;
  await Promise.all(Object.entries(urls).map(async ([key, url]) => {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`asset failed: ${key} (${url}) ${res.status}`);
    out[key] = /\.(ogg|mp3|wav|m4a)$/.test(url)
      ? await ctx.decodeAudioData(await res.arrayBuffer())
      : await createImageBitmap(await res.blob());
    onProgress(++done / Object.keys(urls).length);
  }));
  return out;
}
```

## Common pitfalls

- Blurry canvas on retina: forgot `devicePixelRatio` scaling of the backing store.
- Game runs 2x fast on 120/144 Hz monitors: movement tied to frames instead of `dt`/fixed step.
- Audio silent on first load: context never resumed from a gesture handler.
- Keys stick after alt-tab: no `blur` handler. Page scrolls on arrows/space: no `preventDefault`.
- 404s after deploy: absolute asset paths with a non-root host. Use `base: './'` and relative URLs.
- GPU memory climbs on restart: Three.js geometries/materials/textures not disposed.
- Tests flaky: unseeded randomness or real time inside the simulation.
- `localStorage` throws in private mode or sandboxed iframes: wrap in try/catch.

## Deliverables (every web-game task)

Report all of these:

1. **Run command**: install + dev + production preview, e.g. `npm install && npm run dev`, and the URL.
2. **Files**: list created/changed files with one-line purpose each.
3. **Controls**: keyboard / gamepad / touch mapping.
4. **Test steps**: numbered manual checklist (start, move, goal reached, lose, restart, pause by
   switching tabs, resize window, mobile emulation) plus automated commands (`npm test`,
   `npx playwright test`). Say which you actually ran; mark the rest **NOT ASSESSED**.
5. **Known gaps**: what is stubbed, placeholder art/audio, untested devices/browsers.
6. For release: build command, output folder (`dist/`), and the deploy target steps.

Minimum verification before claiming done: the build succeeds, the page loads with no console
errors, and one input visibly changes the game state. If you cannot run a browser, say so.

## Reference index

Read only what the task needs (each is one level deep):

| File | When |
|---|---|
| `references/game-loop-and-input.md` | Any custom loop (Canvas, Three.js, Pixi): fixed timestep, input manager, gamepad polling, touch controls |
| `references/phaser.md` | Phaser 3 project: config, scenes, Arcade physics, Tiled tilemaps, cameras, tweens, particles, scaling |
| `references/threejs.md` | Three.js project: renderer/camera, glTF + Draco/meshopt/KTX2, animation, dispose, instancing, physics, perf |
| `references/ship-web.md` | Build, deploy (itch.io, Netlify, GitHub Pages), PWA, saves, mobile, perf, Vitest, Playwright |
| `assets/single-file-prototype.html` | Starting point for a no-build Canvas 2D prototype or jam game |

Related skills: `gamesmith` (design, scope, process), `gamesmith-blender` (3D assets, glTF export).
