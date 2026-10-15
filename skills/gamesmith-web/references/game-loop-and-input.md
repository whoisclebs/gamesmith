# Game loop and input (framework-free)

Use for Canvas 2D, Three.js, PixiJS or any custom renderer. Phaser has its own loop and input.

## Fixed-timestep loop with interpolation

Simulate at a constant step (deterministic, framerate independent); render once per frame,
blending previous and current state by `alpha` (leftover time / step).

```ts
export interface Game {
  update(dt: number): void;      // fixed step, seconds
  render(alpha: number): void;   // 0..1 blend between previous and current state
}

export function startLoop(game: Game, step = 1 / 60, maxFrame = 0.25) {
  let last = performance.now();
  let acc = 0;
  let raf = 0;
  let running = false;

  const frame = (now: number) => {
    raf = requestAnimationFrame(frame);
    acc += Math.min(Math.max((now - last) / 1000, 0), maxFrame); // clamp: no spiral of death
    last = now;
    while (acc >= step) {
      game.update(step);
      acc -= step;
    }
    game.render(acc / step);
  };
  const start = () => {
    if (running) return;
    running = true;
    last = performance.now();    // drop the time spent paused
    acc = 0;
    raf = requestAnimationFrame(frame);
  };
  const stop = () => {
    running = false;
    cancelAnimationFrame(raf);
  };
  document.addEventListener('visibilitychange', () => (document.hidden ? stop() : start()));
  window.addEventListener('blur', stop);
  window.addEventListener('focus', start);
  start();
  return { start, stop };
}
```

Interpolating an entity (store previous state in `update`, lerp in `render`):

```ts
class Body { x = 0; y = 0; px = 0; py = 0; vx = 0; vy = 0; }
function step(b: Body, dt: number) { b.px = b.x; b.py = b.y; b.x += b.vx * dt; b.y += b.vy * dt; }
function drawX(b: Body, a: number) { return b.px + (b.x - b.px) * a; } // same for y
```

Rules: gameplay in `update` only; `render` never mutates state; teleports must also set `px/py`
(else the sprite streaks); keep `step` constant for deterministic replays and tests.
A manual pause key just skips `update` while still rendering. Three.js `renderer.setAnimationLoop(fn)`
can drive the same accumulator.

## Input manager (keyboard + pointer, action-mapped)

Use `event.code` (layout independent). Edge sets clear after each fixed update, so `pressed`
fires once per press even when several steps run in one frame.

```ts
type Action = 'left' | 'right' | 'up' | 'down' | 'jump' | 'fire' | 'pause';

const BINDINGS: Record<Action, string[]> = {
  left: ['ArrowLeft', 'KeyA'], right: ['ArrowRight', 'KeyD'],
  up: ['ArrowUp', 'KeyW'], down: ['ArrowDown', 'KeyS'],
  jump: ['Space'], fire: ['KeyJ', 'KeyZ'], pause: ['KeyP', 'Escape'],
};
const PREVENT = new Set(['Space', 'ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown']);

export class Input {
  private down = new Set<string>();
  private hit = new Set<string>();
  private released = new Set<string>();
  pointer = { x: 0, y: 0, down: false };           // canvas-space CSS pixels
  virtual: Partial<Record<Action, boolean>> = {};  // touch buttons / gamepad write here

  constructor(target: HTMLElement) {
    addEventListener('keydown', (e) => {
      if (PREVENT.has(e.code)) e.preventDefault();
      if (!e.repeat) { this.down.add(e.code); this.hit.add(e.code); }
    });
    addEventListener('keyup', (e) => { this.down.delete(e.code); this.released.add(e.code); });
    addEventListener('blur', () => { this.down.clear(); this.pointer.down = false; });
    target.addEventListener('pointerdown', (e) => { this.pointer.down = true; this.move(e, target); });
    target.addEventListener('pointermove', (e) => this.move(e, target));
    addEventListener('pointerup', () => (this.pointer.down = false));
    addEventListener('pointercancel', () => (this.pointer.down = false));
  }
  private move(e: PointerEvent, t: HTMLElement) {
    const r = t.getBoundingClientRect();
    this.pointer.x = e.clientX - r.left;
    this.pointer.y = e.clientY - r.top;
  }
  held(a: Action) { return !!this.virtual[a] || BINDINGS[a].some((c) => this.down.has(c)); }
  pressed(a: Action) { return BINDINGS[a].some((c) => this.hit.has(c)); }
  axis(neg: Action, pos: Action) { return (this.held(pos) ? 1 : 0) - (this.held(neg) ? 1 : 0); }
  endStep() { this.hit.clear(); this.released.clear(); }   // call after every game.update()
}
```

Call `input.endStep()` after each `update`. Never sample input inside `render`.
Normalize diagonals: divide by `Math.hypot(ax, ay)` when it exceeds 1.

## Gamepad API polling

Pads are polled: call `navigator.getGamepads()` every frame (snapshots in Chrome). A pad appears
only after the player presses a button.

```ts
const DEAD = 0.18;
const dz = (v: number) => (Math.abs(v) < DEAD ? 0 : v);

export function pollPad(input: Input) {
  const pad = Array.from(navigator.getGamepads()).find((p) => p && p.connected);
  if (!pad) return { x: 0, y: 0 };
  const v = input.virtual;
  // "standard" mapping: 0 A, 1 B, 2 X, 3 Y, 9 Start, 12-15 D-pad, axes 0/1 left stick
  const std = pad.mapping === 'standard';
  v.jump = !!pad.buttons[0]?.pressed;
  v.fire = !!pad.buttons[std ? 2 : 1]?.pressed;
  v.pause = !!pad.buttons[9]?.pressed;
  let x = dz(pad.axes[0] ?? 0) + (pad.buttons[15]?.pressed ? 1 : 0) - (pad.buttons[14]?.pressed ? 1 : 0);
  let y = dz(pad.axes[1] ?? 0) + (pad.buttons[13]?.pressed ? 1 : 0) - (pad.buttons[12]?.pressed ? 1 : 0);
  const len = Math.hypot(x, y);
  if (len > 1) { x /= len; y /= len; }
  return { x, y };   // analog move vector, y positive = down
}
```

Call `pollPad` once per frame before the update loop and feed the result to the sim as input data.
For button edges, keep last frame's booleans and compare.

## Touch controls

Use Pointer Events (one path for mouse, pen, touch). CSS on canvas/overlay:
`touch-action: none; user-select: none; -webkit-touch-callout: none;`.

```ts
// Floating virtual stick on the left half, buttons are DOM elements on the right.
export function touchStick(el: HTMLElement, out: { x: number; y: number }, radius = 60) {
  let id = -1, ox = 0, oy = 0;
  el.addEventListener('pointerdown', (e) => {
    if (id !== -1 || e.clientX > innerWidth / 2) return;       // left half only
    id = e.pointerId; ox = e.clientX; oy = e.clientY;
    el.setPointerCapture(id);
  });
  el.addEventListener('pointermove', (e) => {
    if (e.pointerId !== id) return;
    const dx = e.clientX - ox, dy = e.clientY - oy;
    const len = Math.hypot(dx, dy) || 1, k = Math.min(len, radius) / radius;
    out.x = (dx / len) * k; out.y = (dy / len) * k;
  });
  const end = (e: PointerEvent) => { if (e.pointerId === id) { id = -1; out.x = out.y = 0; } };
  el.addEventListener('pointerup', end);
  el.addEventListener('pointercancel', end);
}

// Hold-style button: bind a DOM element to an action.
export function touchButton(el: HTMLElement, input: Input, a: Action) {
  const set = (v: boolean) => (input.virtual[a] = v);
  el.addEventListener('pointerdown', (e) => { e.preventDefault(); set(true); });
  for (const t of ['pointerup', 'pointercancel', 'pointerleave'] as const) el.addEventListener(t, () => set(false));
}
```

Touch checklist: thumb-sized buttons clear of edges and notches (`env(safe-area-inset-*)`);
multi-touch (track `pointerId`); show touch UI only when `matchMedia('(pointer: coarse)').matches`;
draw a visible stick base/knob; first touch unlocks audio; block pinch/double-tap zoom via
`touch-action`; add a pause button (no Esc key).

Merge keyboard, pad and touch into one move vector (`{x, y}`, -1..1) so gameplay stays device-agnostic.
