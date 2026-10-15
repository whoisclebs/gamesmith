# Modeling rules for game assets

Rules of thumb for low-poly and stylized work. Apply what fits the brief's style; realistic
assets bend several of these, but the cleanliness rules (UVs, normals, scale) always hold.

## Low-poly construction

| Rule | Why / how |
|---|---|
| Faceted cylinders use 8, 12 or 16 sides | 8 for small/far, 12 default, 16 only for hero silhouettes. Odd counts break symmetry and UV tiling. |
| Chamfer only with a purpose | A bevel is worth its tris only if it catches light on a visible edge or defines a silhouette. Otherwise leave edges hard. |
| Color bands via material index | One mesh, several material slots (or a palette texture), assigned per face. Do not stack thin colored objects to fake stripes: that adds hidden faces and z-fighting. |
| Insets are cut into the parent | A window, panel or plate is an inset/extrude of the wall's own faces, not a separate box floating in front of it. No coplanar overlapping faces. |
| Repeat validated modules | Build one plank, one window, one pillar. Verify it (bbox, tris, normals), then duplicate with linked placement. Never copy a module you have not checked. |
| Bridge loops for pipes and handles | Connect two edge loops with `bpy.ops.mesh.bridge_edge_loops` or build the tube from a loop; do not intersect a cylinder through a wall and leave buried faces. |
| Delete what the camera never sees | Bottom faces of props that sit on the ground, faces inside walls, back of wall decor. Keep them if the object can be tipped, picked up or seen from below. |
| Share vertices | No duplicate vertices at seams unless a hard UV/normal split needs them (export splits those automatically). |
| Symmetry | Model half and mirror with a Mirror modifier (clipping on, merge on), apply before export. Verify center verts sit at X=0. |
| Booleans are construction tools | Apply them, then clean ngons and stray verts, and delete the cutter. Never ship a live boolean. |
| Quads while building, tris at export | Ngons are fine in blockout, but resolve them before UV and export. |
| Thin parts need thickness or be single-sided on purpose | Leaves, flags, cloth cards may be open planes; mark them intentional so validation does not flag them. |

Scale sanity: build in meters. A door is about 2 m tall, a chair seat about 0.45 m. Check the
bounding box against a real-world number from the brief.

## Pivot and orientation

- Origin at the base center for things that stand; at the hinge for doors; at the grip for held items.
- Pick one forward axis per project and keep it (document it in the brief). Blender is Z-up,
  -Y forward by convention; engines convert on export (see `export-per-engine.md`).
- Set origin via data, not by eye: translate the mesh so the desired point is at (0,0,0), then
  keep object location where you want it placed. Snippet in `mcp-and-scripting.md`.

## UVs

| Topic | Guidance |
|---|---|
| Texel density | Pick one px/m for the whole project (e.g. a number agreed in the brief) and keep every asset on it. Compare by checking UV area vs surface area ratio per object. |
| Island padding | Leave a margin of a few pixels at the target texture size (more for mipmapped/atlas textures; 4-8 px is a common starting point). Padding too small bleeds neighbors at distance. |
| Seams | Put seams on edges the player rarely sees: undersides, backs, hard edges. |
| Smart UV Project | Good default for hard-surface low-poly: `bpy.ops.uv.smart_project(angle_limit=radians(66), island_margin=0.02)`. Re-pack afterwards. |
| Flat-color palette atlas | For faceted style, a tiny palette texture (e.g. 8x8 or 16x16 swatches) plus UVs that sit in the swatch center gives many colors with one material and no seams. Keep UVs inside the swatch with a half-texel inset. |
| Tiling textures | Use only for large repeated surfaces (floors, walls); keep UVs in 0-1 offset by whole tiles. |
| Mirrored UVs | Allowed for symmetric parts only if the texture has no directional detail and normal maps are mirrored-safe. |
| UV2 (lightmap) | Only when the engine bakes lightmaps (Unity, Unreal, Godot LightmapGI). Needs non-overlapping, 0-1, uniquely unwrapped islands. Create a second UV layer named `UV2`; do not reuse UV0 if it overlaps or tiles. Check the engine skill. |
| Every textured mesh has UV0 | Name the layer `UVMap` or `UV0` consistently. |

## Normals and smoothing

- Recalculate outside: `bpy.ops.mesh.normals_make_consistent(inside=False)` in edit mode, or
  `bmesh.ops.recalc_face_normals(bm, faces=bm.faces)` in data code.
- Faceted style: flat shading everywhere (`mesh.polygons.foreach_set("use_smooth", [False]*n)`).
- Smooth style: smooth shade plus an angle limit so hard edges stay crisp.
  Blender 4.1 removed "Auto Smooth" on the mesh: use `bpy.ops.object.shade_smooth_by_angle(angle=radians(30))`
  (or the Smooth by Angle modifier). Do not set `mesh.use_auto_smooth`; it no longer exists.
- Negative scale flips normals; apply scale, then recalc normals.
- Check for inverted faces numerically: for a closed convex-ish part, face normals should point
  away from the part center (dot product of normal and center-to-face vector > 0).
- Custom split normals and weighted normals survive export only if the exporter is told to
  write normals; both FBX and glTF do by default.

## LODs

| Item | Rule |
|---|---|
| Naming | `AssetName_LOD0`, `_LOD1`, `_LOD2`. Unity builds an LOD group from FBX files named this way; Unreal imports `_LODn` from the same FBX. Godot and web use separate files or the engine's own mesh LOD. |
| Reduction | Roughly halve triangle count per level as a starting ratio; confirm against the brief. Use Decimate (collapse) with ratio, then re-check UV and normals. |
| Silhouette first | Reduce interior detail before silhouette. Remove bevels and small insets at LOD1, tiny parts at LOD2. |
| Shared materials | LODs reuse the same materials and UV layout so they swap without popping color. |
| Last LOD | Often a billboard card or a coarse box; props that are never far may need only LOD0. Ask what the camera distances are. |
| Not needed | Mobile props seen at a fixed small distance, and very low-poly pieces. Skip LODs rather than adding tooling. |

## Collision meshes

| Engine | Convention |
|---|---|
| Unreal | Separate meshes named `UBX_Name_00` (box), `UCP_` (capsule), `USP_` (sphere), `UCX_Name_00` (convex hull). Same origin as the render mesh. |
| Godot | Add suffix to the node name: `-col` (trimesh/convex alongside the visible mesh), `-colonly` (invisible collider only), `-convcol` / `-convcolonly` (convex). Exact options: `export-per-engine.md`. |
| Unity | No automatic convention. Export a simplified mesh named `Name_collider` and assign it to a MeshCollider (convex if the body is dynamic), or use primitive colliders. |
| Roblox | Collision comes from the MeshPart's CollisionFidelity setting (Default, Box, Hull, Precise) rather than a separate mesh. Check current docs. |
| Web | Build physics shapes from the AABB or a hull in code; ship a simplified mesh only if a precise trimesh is truly needed. |

Collision mesh rules: far fewer triangles than the render mesh; convex pieces for dynamic
bodies (split concave shapes into several hulls); no thin slivers; watertight where convex;
hide or exclude it from render export unless the engine strips by name.
