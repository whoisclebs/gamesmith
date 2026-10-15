# Performance, export, testing and CI (Godot 4.x)

Measure first. Do not claim speedups without a before/after number from the profiler; if you could not
run the game, mark performance **NOT ASSESSED**.

## Profiling workflow

1. Run the game from the editor; open the bottom Debugger panel.
2. **Profiler**: per-function time (script and engine). Sort by self time; find the top 3 offenders.
3. **Monitors**: FPS, process/physics time, object/node/orphan-node counts, draw calls, VRAM, physics
   active objects. Rising object or orphan-node counts = leak (missing `queue_free`, un-pooled spawns).
4. **Visual Profiler**: CPU/GPU time per render stage; tells you whether you are CPU or GPU bound.
5. Debug > Visible Collision Shapes / Navigation to inspect physics and nav cost.
6. Profile an exported build on target hardware before final decisions; editor overhead skews numbers.

Custom monitors:

```gdscript
func _ready() -> void:
	Performance.add_custom_monitor("game/active_enemies", func() -> int: return get_tree().get_nodes_in_group("enemies").size())
# read built-ins in code: Performance.get_monitor(Performance.TIME_FPS)
```

## Common script-side wins

| Symptom | Fix |
|---|---|
| Heavy `_process` on many nodes | `set_process(false)` when idle; use signals/`Timer` instead of polling; process in manager arrays for thousands of simple units |
| `get_node`/`find_child`/`get_nodes_in_group` each frame | cache in `@onready` / variables |
| Allocation churn | reuse arrays/vectors, pool spawned nodes, avoid creating `Tween`/`Callable` per frame |
| Distance checks | compare `distance_squared_to` against squared radius |
| Many off-screen entities | `VisibleOnScreenNotifier2D/3D` to sleep logic; stagger updates across frames |
| String building in hot loops | `StringName` for ids/keys (`&"jump"`), avoid `+` concatenation per frame |
| Slow GDScript hotspot | move to typed code first (typed GDScript is faster), then consider C#/GDExtension only if profiled |

## Rendering

- **MultiMeshInstance2D/3D** draws thousands of identical meshes in one call (grass, bullets, debris).
  Set `transform_format` and `use_colors` **before** `instance_count`; update with `set_instance_transform`.
  Per-instance logic is yours; there is no per-instance node, culling is whole-multimesh (split into chunks).
- Reduce draw calls: share materials, atlases for 2D sprites, `CanvasGroup`/batching in 2D is automatic for
  same-texture items, avoid unique materials per instance.
- 3D: use `VisibilityRange` (HLOD) / LOD import settings, occlusion culling (`OccluderInstance3D`), baked
  lightmaps (`LightmapGI`) or `VoxelGI/SDFGI` selectively, limit shadow-casting lights and shadow map sizes.
- Pick the renderer for the target: Forward+ (desktop high-end), Mobile, Compatibility (widest hardware, web).
  The renderer is fixed per project run; web export requires Compatibility in 4.x (check docs for your version).
- Particles: cap `amount`, prefer `GPUParticles` for large counts; `CPUParticles` is the fallback where GPU particles are unsupported (GPUParticles work in Compatibility since 4.2; check docs for your version).
- Pixel art: Project Settings > Rendering > Textures default filter Nearest; stretch mode `canvas_items` / `viewport`.

## Physics

- Layers/masks: name them in Project Settings > Layer Names. `collision_layer` = what this object is;
  `collision_mask` = what it detects/collides with. Keep masks minimal (player projectile masks `enemy` + `world`,
  not `player`).

```gdscript
set_collision_layer_value(2, true)    # I am on layer 2 (enemy)
set_collision_mask_value(1, true)     # I collide with layer 1 (world)
```

- Prefer `Area` + signals for triggers over per-frame overlap queries; use `RayCast`/`ShapeCast` nodes with
  `enabled = false` unless needed, or `PhysicsDirectSpaceState` queries on demand.
- Simple shapes (circle, capsule, box) beat concave polygons; use concave only for static geometry.
- Run motion in `_physics_process`; do not scale physics steps to fix perf problems before profiling. Changing
  `physics_ticks_per_second` alters game feel and must be retested.
- 3D physics engine choices (default vs Jolt, available in newer 4.x) are project settings; check docs for the
  version before recommending.
- Navigation: bake once, avoid per-frame path requests for many agents (stagger, cache, use avoidance).

## Export

1. Install export templates matching the editor version exactly (Editor > Manage Export Templates).
2. Project > Export > Add preset (Windows, Linux, macOS, Android, iOS, Web). Presets save to `export_presets.cfg`
   (commit it; secrets and keystore passwords are kept out of the file via `.godot/export_credentials.cfg`).
3. Set include filters for non-resource files (e.g. `*.json,*.csv`), exclude `tests/*`, `addons/gut/*`, docs.
4. Release vs debug: ship release; debug builds keep the remote debugger and asserts.
5. Test the exported build, not only the editor: `user://` paths, missing files, case-sensitive paths on
   Linux/Web/Android (match file-name case exactly), shaders/first-run stutter, input on target devices.
6. Android needs JDK, Android SDK and a keystore; iOS and macOS signing need Apple tooling. Check current docs
   for the version's required tool versions; do not hardcode them.

### Web export caveats

- Output is `index.html` + `.js` + `.wasm` + `.pck`; it must be served over HTTP(S), not opened from `file://`.
- Threaded builds need `SharedArrayBuffer`, which requires cross-origin isolation headers
  (`Cross-Origin-Opener-Policy: same-origin`, `Cross-Origin-Embedder-Policy: require-corp`). Recent 4.x versions
  offer single-threaded export that avoids this and hosts like itch.io; check the preset options for your version.
- Use the Compatibility renderer; some features (certain shaders, compute, large textures, GDExtension) are
  limited or unavailable.
- Audio and fullscreen/pointer lock need a user gesture first; show a "click to start" screen.
- Download size matters: compress textures (VRAM compression off for web unless needed), trim unused assets,
  serve with gzip/brotli.
- C# projects: web support in 4.x is limited; verify against current docs before committing to it.
- `user://` is IndexedDB-backed and can be cleared by the browser.

## Automated testing

| Tool | Notes |
|---|---|
| GUT (`addons/gut`) | Tests are `extends GutTest`, files `test_*.gd`, functions `test_*`. |
| gdUnit4 (`addons/gdUnit4`) | Tests `extends GdUnitTestSuite`, richer scene-runner and assertion API; has a C# variant. |

```gdscript
extends GutTest
func test_damage_clamps_hp() -> void:
	var h := Health.new()
	h.max_hp = 10
	h.hp = 10
	h.take_damage(25)
	assert_eq(h.hp, 0)
	h.free()
```

- Test pure logic (health, inventory, save migration, damage math, state transitions) as plain objects; use
  scene runners only for integration. Avoid timing-dependent tests; drive time via explicit `_physics_process(delta)` calls.
- GUT headless: `godot --headless -s addons/gut/gut_cmdln.gd -gdir=res://tests -gexit`
- gdUnit4 ships `runtest` scripts (`addons/gdUnit4/runtest.sh|.cmd`) that read `GODOT_BIN`; verify flags in its docs for your version.
- Cheap smoke test without a framework: a script that instantiates each main scene, runs a few frames, and quits non-zero on error.

## CI with headless Godot

```bash
# 1) import assets once so .godot/ exists (fresh checkouts have no cache)
godot --headless --path . --import
# 2) run tests
godot --headless --path . -s addons/gut/gut_cmdln.gd -gdir=res://tests -gexit
# 3) export (preset name must match export_presets.cfg exactly)
mkdir -p build/web
godot --headless --path . --export-release "Web" build/web/index.html
# variants: --export-debug "Preset" out ; --export-pack "Preset" game.pck
```

- Pin the Godot version (download the exact release binary and matching export templates, or use a maintained
  container image such as `barichello/godot-ci`); cache templates between runs.
- Export templates are installed under the user data dir (`~/.local/share/godot/export_templates/<version>/`
  on Linux); the version folder name must match `godot --version`.
- A non-zero exit or `ERROR:` lines in the log should fail the job; first-time imports may print benign errors, so
  run `--import` separately and re-run export after.
- Upload `build/` as the artifact; for itch.io use `butler push`. Keep signing secrets in CI secrets, never in the repo.
- Android/iOS CI additionally needs SDKs and signing configured on the runner; mark as **NOT ASSESSED** if untested.
