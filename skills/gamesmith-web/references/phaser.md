# Phaser 3

`npm install phaser`. Phaser 3 (last line 3.90) is the reference here; Phaser 4 keeps the same
scene/Arcade model but check current docs for renderer and import differences before upgrading.
Phaser owns the loop, input, audio unlock, asset loader and physics step: do not write your own loop.

## Game config (TypeScript, Vite)

```ts
import Phaser from 'phaser';
import { Boot } from './scenes/Boot';
import { Play } from './scenes/Play';
import { Hud } from './scenes/Hud';

new Phaser.Game({
  type: Phaser.AUTO,                 // WebGL with Canvas fallback
  parent: 'app',                     // id of the container div
  width: 480, height: 270,           // logical resolution (pick once, design for it)
  backgroundColor: '#1b1b2b',
  pixelArt: true,                    // nearest-neighbour; also disables antialias
  roundPixels: true,
  scale: {
    mode: Phaser.Scale.FIT,          // letterbox, keep aspect
    autoCenter: Phaser.Scale.CENTER_BOTH,
  },
  physics: {
    default: 'arcade',
    arcade: { gravity: { x: 0, y: 900 }, debug: import.meta.env.DEV },
  },
  fps: { target: 60 },               // Arcade steps at a fixed rate by default
  input: { gamepad: true },
  scene: [Boot, Play, Hud],          // first scene auto-starts
});
```

Scale modes: `FIT` (letterbox), `ENVELOP` (cover, may crop), `RESIZE` (canvas matches parent; you
handle layout in a `resize` event), `NONE`. High-DPI: Phaser renders at logical size and scales
the canvas; for crisp vector/text use a larger logical size or `resolution`-style zoom, and keep
`pixelArt: true` only for real pixel art. Keep CSS `html, body { margin:0; height:100% }`.

## Scenes: init / preload / create / update

```ts
export class Boot extends Phaser.Scene {
  constructor() { super('Boot'); }
  preload() {
    const bar = this.add.rectangle(240, 135, 0, 8, 0xffffff).setOrigin(0, 0.5);
    this.load.on('progress', (p: number) => (bar.width = 200 * p));
    this.load.setPath('assets');                       // served from public/assets
    this.load.image('tiles', 'tiles.png');
    this.load.tilemapTiledJSON('level1', 'level1.json');
    this.load.spritesheet('hero', 'hero.png', { frameWidth: 32, frameHeight: 32 });
    this.load.atlas('fx', 'fx.png', 'fx.json');
    this.load.audio('jump', ['jump.ogg', 'jump.mp3']);
  }
  create() { this.scene.start('Play', { level: 1 }); }
}

export class Play extends Phaser.Scene {
  private player!: Phaser.Physics.Arcade.Sprite;
  private cursors!: Phaser.Types.Input.Keyboard.CursorKeys;
  constructor() { super('Play'); }
  init(data: { level: number }) { /* runs before preload/create on every start */ }
  create() {
    this.anims.create({ key: 'run', frames: this.anims.generateFrameNumbers('hero', { start: 0, end: 5 }), frameRate: 12, repeat: -1 });
    this.player = this.physics.add.sprite(64, 64, 'hero').setCollideWorldBounds(true);
    this.cursors = this.input.keyboard!.createCursorKeys();
    this.scene.launch('Hud');                          // run a UI scene in parallel
    this.events.once(Phaser.Scenes.Events.SHUTDOWN, () => this.scene.stop('Hud'));
  }
  update(time: number, delta: number) {                // delta in ms
    const onGround = (this.player.body as Phaser.Physics.Arcade.Body).blocked.down;
    this.player.setVelocityX(this.cursors.left.isDown ? -140 : this.cursors.right.isDown ? 140 : 0);
    if (onGround && Phaser.Input.Keyboard.JustDown(this.cursors.up)) this.player.setVelocityY(-380);
  }
}
```

Share data between scenes with `this.registry` (global, with change events) or the `data` argument
of `scene.start`. Restart a level with `this.scene.restart()`. Objects created in `create` are
destroyed on shutdown; cleanup of your own listeners goes in the `SHUTDOWN` event.
Audio is unlocked by Phaser on the first input; check `this.sound.locked` for a "click to start" gate.

## Arcade physics

```ts
const coins = this.physics.add.group({ allowGravity: false, immovable: true });
this.physics.add.collider(this.player, ground);                       // solid
this.physics.add.overlap(this.player, coins, (_p, c) => {             // trigger
  (c as Phaser.Physics.Arcade.Sprite).disableBody(true, true); this.registry.inc('score', 1);
});
this.player.setSize(16, 24).setOffset(8, 8);                          // tighten the hitbox
const bullets = this.physics.add.group({ classType: Bullet, maxSize: 30, runChildUpdate: true });
const b = bullets.get(x, y) as Bullet | null;                         // pooled: get() then b.fire()
```

Use groups with `maxSize` as object pools; never `new` sprites per shot. Arcade handles AABB and
circles only; for slopes, rotated bodies or joints use Matter (`physics.default: 'matter'`),
which is heavier. Use `setVelocity`/`setAcceleration`/`setDrag`/`setMaxVelocity` over moving `x`/`y`.
Add coyote time and jump buffering in `update` with timers for good platformer feel.

## Tilemaps (Tiled)

In Tiled: embed the tileset in the map (or keep image path correct), export JSON, name layers
(`Ground`, `Decor`), add a boolean custom property `collides` on tiles, and put spawn points in an
object layer.

```ts
const map = this.make.tilemap({ key: 'level1' });
const tileset = map.addTilesetImage('tiles-in-tiled', 'tiles')!;   // 1st arg = tileset name inside Tiled
const ground = map.createLayer('Ground', tileset, 0, 0)!;
ground.setCollisionByProperty({ collides: true });
this.physics.add.collider(this.player, ground);
const spawn = map.findObject('Objects', (o) => o.name === 'spawn')!;
this.player.setPosition(spawn.x!, spawn.y!);
this.physics.world.setBounds(0, 0, map.widthInPixels, map.heightInPixels);
```

Mismatched tileset/layer names return null: that is the usual cause of a blank map. Extrude tile
edges (tools like `tile-extruder`) if you see seams when the camera scrolls or zooms.

## Cameras, tweens, particles

```ts
const cam = this.cameras.main;
cam.setBounds(0, 0, map.widthInPixels, map.heightInPixels);
cam.startFollow(this.player, true, 0.1, 0.1);        // roundPixels, lerp x/y
cam.setZoom(1); cam.shake(120, 0.005); cam.flash(80); cam.fadeOut(300);

this.tweens.add({ targets: sprite, y: '-=12', duration: 400, yoyo: true, repeat: -1, ease: 'Sine.easeInOut' });
this.tweens.chain({ targets: sprite, tweens: [{ scale: 1.3, duration: 80 }, { scale: 1, duration: 120 }] });
this.time.delayedCall(500, () => this.scene.start('GameOver'));   // timers pause with the scene

const burst = this.add.particles(0, 0, 'fx', {                    // 3.60+ API: emitter is the game object
  frame: 'spark', speed: { min: 60, max: 180 }, lifespan: 400,
  scale: { start: 1, end: 0 }, gravityY: 300, emitting: false,
});
burst.explode(16, x, y);                                          // one-shot at a position
```

Put the HUD in its own scene with a fixed camera so zoom/shake does not move it; set
`.setScrollFactor(0)` for HUD objects kept in the main scene. Text: `this.add.text(...)`;
bitmap text is faster for frequently changing numbers.

## Gotchas

- Frame-rate-dependent code: use `delta` (ms) or physics velocities, never per-frame increments.
- Pixel art blurry: `pixelArt: true`, power-of-two-friendly integer zoom, and no sub-pixel camera.
- Large bundle (the library is big): code-split scenes with dynamic `import()`, rely on gzip/brotli.
- Do not destroy a sprite inside its own collision callback without `disableBody`/`destroy` safety checks.
- Hot reload with Vite recreates the `Game`; call `game.destroy(true)` in `import.meta.hot.dispose`.
- Deterministic tests: use `Phaser.Math.RND.sow([seed])` or your own seeded RNG; keep rules out of scenes.
