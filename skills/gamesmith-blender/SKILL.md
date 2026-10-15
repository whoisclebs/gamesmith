---
name: gamesmith-blender
description: "Build game-ready 3D assets in Blender (4.x/5.x) with bpy, headless or through a live Blender MCP connection. Covers blockout, modeling, numeric verification, UVs, materials, and export plus validation for Roblox, Unity, Godot, web/Three.js and Unreal. Use when the user wants a 3D model, prop, environment piece or low-poly asset created, repaired, optimized or exported for a game."
license: MIT
metadata:
  version: "0.1.0"
  pack: gamesmith
---

# gamesmith-blender

Produce 3D assets that drop into a game engine with no cleanup. Pair with `gamesmith` (core
pipeline and art direction) and the engine skill that receives the asset: `gamesmith-roblox`,
`gamesmith-godot`, `gamesmith-unity`, `gamesmith-web`.

## 1. Pick the mode

| Mode | Use when | Notes |
|---|---|---|
| Headless script (`blender -b -P build.py -- args`) | Default. Repeatable, diffable, CI-friendly. | One script per asset, rebuilt from scratch every run. |
| Live Blender MCP | User wants to watch/steer interactively, or inspect an existing `.blend`. | Small idempotent chunks; see `references/mcp-and-scripting.md`. |

Rule: even in MCP mode, keep the final build as a script file in the project so it can be re-run.
If Blender is not installed or not on PATH, ask the user for the executable path; do not guess.
Confirm the version first: `blender --version`.

## 2. Workflow

Work in this order. Do not skip ahead; each step gates the next.

1. **Brief.** Write down before touching Blender:
   - Anatomy list: every part of the asset, one line each (e.g. "hull, mast, sail, rope, flag").
   - Proportions: real-world height/width/depth in meters, plus 2-3 key ratios.
   - Poly budget (tris) and texture budget, from the table below and the target engine.
   - Style: faceted low-poly, stylized smooth, or realistic; palette (hex list) if flat-colored.
   - Camera distance in game (decides how much detail is worth it).
2. **Block out.** Primitives only, correct size and position, origin at the logical pivot.
   Check silhouette first; if the blockout reads badly, detail will not save it.
3. **Build one part at a time.** Name each object, put it in a collection, finish it, verify it,
   then move on. Never leave a half-modeled part while starting the next.
4. **Verify numerically after every part** (see section 3). Screenshots alone hide gaps.
5. **Six-side check.** Render or view front, back, left, right, top, bottom. Look for floating
   parts, hidden gaps, inverted faces, z-fighting, anything visible from the game camera.
6. **Cleanup.** Merge by distance, delete loose geometry, fix normals, apply modifiers you want
   baked, remove helpers (cutters, cameras, lights, empties used for construction).
7. **UV.** Per `references/modeling-rules.md`: texel density, padding, atlas for flat palettes.
8. **Materials.** Few slots. Color bands via material index, not separate stacked objects.
9. **Export** with the target's settings (`references/export-per-engine.md`).
10. **Validate** the exported file: run `scripts/export_game_asset.py`, then re-import the result
    into a fresh scene or the engine and compare size, orientation and triangle count to the brief.

## 3. Verify numerically

Print numbers from bpy instead of eyeballing. After each part, log at least:

- World-space bounding box min/max and dimensions in meters (`obj.matrix_world @ corner`).
- For parts that must touch: the gap between their bounding boxes along the contact axis
  (expected `0.0` within 1e-4, not "looks close").
- Triangle count (evaluated mesh, modifiers applied) and running total vs budget.
- Counts of non-manifold edges, loose verts, zero-area faces, flipped normals.
- Object count and names, to catch leftover helpers.

Snippets: `references/mcp-and-scripting.md`. A screenshot confirms intent; the numbers confirm truth.

## 4. Game-ready checklist

Block export until every item holds (the script in `scripts/` checks the ones marked *auto*).

- [ ] Scale and rotation applied (scale 1,1,1; rotation 0,0,0) *auto*
- [ ] Real-world units: scene unit = meters, scale 1.0; asset dimensions match the brief
- [ ] Origin/pivot at the base center (props, buildings, characters) or the logical hinge/grip point
- [ ] Lowest point at Z=0 when the asset stands on the ground
- [ ] Merge by distance done; no duplicate vertices *auto (via counts)*
- [ ] No loose verts/edges, no zero-area faces *auto*
- [ ] No unintended non-manifold or open edges (open planes for foliage/cards are intentional) *auto*
- [ ] Normals consistent and facing outward; smoothing deliberate (flat for faceted style)
- [ ] Triangulated where the engine expects it (glTF always is; use a Triangulate modifier for FBX when needed)
- [ ] Single-user mesh data (no accidental shared datablocks across different objects) *auto*
- [ ] Objects and collections named meaningfully (`Crate_Lid`, not `Cube.004`); materials named
- [ ] No leftover cutters, booleans, cameras, lights, empties, hidden junk *auto (selection/visible only)*
- [ ] UV0 present on every textured mesh; UV2 only if the engine bakes lightmaps
- [ ] Triangle count within budget *auto*
- [ ] `.blend` source saved separately from the export; the export step never overwrites it

## 5. Poly budget (rough guidance)

Triangle counts per single asset. These are starting points, **not** platform limits; confirm
hard limits in the current engine docs and the project brief. If the user gave a number, use theirs.

| Asset type | Mobile / Roblox-class | PC / console |
|---|---|---|
| Small prop (cup, coin, key) | 100-500 | 500-2k |
| Medium prop (chair, crate, barrel) | 300-1.5k | 1.5k-8k |
| Large prop / vehicle | 1.5k-6k | 6k-30k |
| Building / modular kit piece | 500-3k | 3k-20k |
| Foliage (tree, bush) | 200-1.5k (cards help) | 1k-10k |
| Weapon / held item | 300-2k | 2k-15k |
| Character (stylized) | 1.5k-6k | 6k-30k |
| Collision mesh | 12-200 (hull) | 50-500 |

Budget the whole scene, not just one asset: count how many instances are on screen at once.
Anything NOT in this table: say **NOT ASSESSED** and ask for a target rather than inventing one.

## 6. Hard rules

- Never save over the user's source `.blend` from an export script; export from memory or a copy.
- Start every build script by clearing the scene so reruns are deterministic.
- Use `bmesh`/data API for geometry; use `bpy.ops` only where there is no data-API route, and
  ops need a correct context (object mode, active/selected object).
- Names, sizes and colors come from the brief, not improvisation. Keep palette values in one dict.
- After changing a part, re-run its numeric checks; fixes in one place often shift another.
- Ask before deleting user objects that were not created by your script.
- Static meshes are the baseline here. Rigging and animation are out of scope for this skill;
  if the brief needs them, say so and agree on bones/naming with the user first.

## 7. Export and validate

```
blender -b asset.blend -P skills/gamesmith-blender/scripts/export_game_asset.py -- --target godot --out build/crate.glb
```

Targets: `roblox`, `unity`, `godot`, `web`. Add `--selection` to export only the selected objects.
The script reports triangle counts, scale, open edges and loose geometry, and exits non-zero on
hard failures. It never saves the `.blend`. Settings and per-engine caveats live in
`references/export-per-engine.md`; Unreal and anything else are covered there too.

Then hand off to the engine skill for import, materials and collision setup.

## Reference index

| File | Read when |
|---|---|
| `references/modeling-rules.md` | Choosing sides/chamfers, UV layout, normals, LODs, collision meshes |
| `references/export-per-engine.md` | Choosing format and exact FBX/glTF settings per engine, `bpy` export calls |
| `references/mcp-and-scripting.md` | Writing bpy build scripts, running via MCP, measuring and logging stats |
| `scripts/export_game_asset.py` | Headless validate-and-export step |
