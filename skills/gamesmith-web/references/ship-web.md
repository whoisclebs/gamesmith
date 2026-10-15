# Ship a web game

## Vite build

```ts
// vite.config.ts
import { defineConfig } from 'vite';
export default defineConfig({
  base: './',                       // relative URLs: works on itch.io, subpaths, file hosting
  build: { target: 'es2022', assetsInlineLimit: 4096 },
});
```

```bash
npm run build      # outputs dist/
npm run preview    # test the REAL build, not just dev
```

Asset hashing: files imported from code (`import url from './hero.png'`, or
`new URL('./hero.png', import.meta.url)`) get content-hashed names in `dist/assets/`, so long
cache lifetimes are safe. Files in `public/` are copied untouched at the root with no hash: serve
them with revalidation, or add a version query (`?v=1.2.0`) / rename on change. Phaser/Three paths
loaded as strings at runtime (`this.load.image('x', 'assets/x.png')`) must live in `public/`.
Inspect bundle size with `npx vite-bundle-visualizer`; enable host gzip/brotli.

## Deploy

| Target | Steps |
|---|---|
| itch.io | `npm run build`, zip the CONTENTS of `dist/` (index.html at zip root), upload as "HTML", tick "played in the browser", set viewport size (or fullscreen), enable the fullscreen button. Needs relative paths (`base: './'`); runs inside an iframe |
| Netlify | Connect repo; build `npm run build`, publish `dist`. Or `npx netlify deploy --dir=dist --prod`. Optional `netlify.toml` with `[build] command="npm run build" publish="dist"` |
| GitHub Pages | Repo Settings -> Pages -> source "GitHub Actions". Project sites serve from `/<repo>/`, so `base: './'` or `base: '/<repo>/'` |

GitHub Pages workflow (`.github/workflows/pages.yml`; check current action versions):
```yaml
name: Deploy
on: { push: { branches: [main] }, workflow_dispatch: {} }
permissions: { contents: read, pages: write, id-token: write }
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: { name: github-pages, url: '${{ steps.d.outputs.page_url }}' }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 22, cache: npm }
      - run: npm ci && npm test --if-present && npm run build
      - uses: actions/upload-pages-artifact@v3
        with: { path: dist }
      - id: d
        uses: actions/deploy-pages@v4
```

Ask the user before pushing, deploying or uploading anything.
iframe caveats (itch.io, game portals): no top-level navigation, `localStorage` may be blocked
(try/catch), audio needs a click, fullscreen needs a gesture. Portals may require their own SDK.

## Saves (localStorage, versioned)

```ts
const KEY = 'mygame.save';
const VERSION = 2;
interface Save { v: number; best: number; settings: { mute: boolean } }
const defaults = (): Save => ({ v: VERSION, best: 0, settings: { mute: false } });

const migrations: Record<number, (s: any) => any> = {
  1: (s) => ({ ...s, v: 2, settings: { mute: !!s.mute } }),   // v1 -> v2
};
export function load(): Save {
  try {
    let s = JSON.parse(localStorage.getItem(KEY) ?? 'null');
    if (!s || typeof s.v !== 'number') return defaults();
    while (s.v < VERSION) s = migrations[s.v]?.(s) ?? defaults();
    return { ...defaults(), ...s };
  } catch { return defaults(); }                              // corrupt JSON, blocked storage
}
export function save(s: Save) {
  try { localStorage.setItem(KEY, JSON.stringify(s)); } catch { /* quota/private mode: keep playing */ }
}
```

Save on meaningful events (level end, setting change, tab hidden), not every frame. Validate
loaded values (untrusted), use IndexedDB for large blobs, offer a reset option. Cloud saves and
leaderboards need a backend: out of scope unless asked.

## PWA / offline (optional)

`npm i -D vite-plugin-pwa`, then:
```ts
// vite.config.ts
import { VitePWA } from 'vite-plugin-pwa';
plugins: [VitePWA({ registerType: 'autoUpdate', manifest: { name: 'My Game', short_name: 'Game',
  display: 'fullscreen', orientation: 'landscape', background_color: '#000',
  icons: [{ src: 'icon-512.png', sizes: '512x512', type: 'image/png' }] },
  workbox: { globPatterns: ['**/*.{js,css,html,png,ogg,glb,json}'] } })]
```

Needs HTTPS (localhost exempt). Stale service workers cause "my fix did not deploy" bugs: test an update. Skip PWA for jam/itch.io builds.

## Mobile considerations

- `<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">`; size the
  container with `100dvh`; pad UI with `env(safe-area-inset-*)`.
- Touch controls, `touch-action: none` (see `game-loop-and-input.md`); no hover-only UI.
- iOS Safari limits fullscreen: call `requestFullscreen()` from a button where supported, or use
  "Add to Home Screen". Use `screen.orientation.lock` only where available; else a "rotate device" overlay.
- Unlock audio on first touch; iOS may mute Web Audio when the ringer switch is silent.
- Cap `devicePixelRatio`, textures, particles; add a low-quality toggle; test long sessions on a real low-end phone.
- Stop pull-to-refresh: `overscroll-behavior: none` on `html, body`.

## Performance and Lighthouse

Lighthouse measures load (LCP, TBT, bundle weight), not frame time; profile gameplay in DevTools.
- Tiny HTML, visible loading screen; lazy-load levels, decoders and music.
- Compress art (WebP/AVIF, KTX2), audio (Ogg/AAC), meshes (Draco/meshopt). Cache hashed files
  long; revalidate `index.html` and `public/`.
- Frame budget: **NOT ASSESSED** until profiled on target devices; watch GC pauses and long tasks.

## Testing logic with Vitest

Test `src/sim` as pure functions with a seeded RNG and fixed `dt`; no DOM, no canvas.

```ts
import { describe, it, expect } from 'vitest';
import { rng } from '../src/sim/rng';
import { stepWorld, newWorld } from '../src/sim/world';

describe('sim', () => {
  it('is deterministic for a seed', () => {
    const run = () => { const w = newWorld(rng(42)); for (let i = 0; i < 600; i++) stepWorld(w, { x: 1, y: 0 }, 1 / 60); return w; };
    expect(run()).toEqual(run());
  });
  it('collecting a coin raises the score', () => {
    const w = newWorld(rng(1)); w.player.x = w.coin.x; w.player.y = w.coin.y;
    stepWorld(w, { x: 0, y: 0 }, 1 / 60);
    expect(w.score).toBe(1);
  });
});
```

Script: `"test": "vitest run"`. Cover win/lose, scoring, collisions, save migration, level parsing; not rendering.

## Playwright smoke test

```bash
npm i -D @playwright/test && npx playwright install chromium
```

```ts
import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: 'tests/e2e',
  webServer: { command: 'npm run build && npm run preview -- --port 4173', port: 4173, reuseExistingServer: true },
  use: { baseURL: 'http://localhost:4173' },
});
```

```ts
import { test, expect } from '@playwright/test';

test('loads, takes input, no console errors', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => m.type() === 'error' && errors.push(m.text()));
  await page.goto('/');
  const canvas = page.locator('canvas');
  await expect(canvas).toBeVisible();
  await canvas.click();                       // also unlocks audio
  await page.keyboard.down('ArrowRight');
  await page.waitForTimeout(500);
  await page.keyboard.up('ArrowRight');
  // needs a test hook: window.__game = { getState } in dev/test builds
  const state = await page.evaluate(() => (window as any).__game?.getState?.());
  expect(state?.player.x).toBeGreaterThan(0);
  expect(errors).toEqual([]);
});
```

WebGL in headless CI may need software-rendering flags; if the canvas stays blank there, say so.
Add `"test:e2e": "playwright test"` and report which tests you actually ran.
