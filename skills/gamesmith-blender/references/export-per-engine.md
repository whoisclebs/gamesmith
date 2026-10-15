# Export per engine

Always: apply transforms, check the checklist in `SKILL.md`, export only the intended objects
(selection or a dedicated collection), then re-import the file once and compare size and
orientation. Run `scripts/export_game_asset.py` to do validate + export in one step for
`roblox`, `unity`, `godot` and `web`.

## Decision table

| Engine | Format | Units / axes | Notes |
|---|---|---|---|
| Roblox | FBX (also OBJ or glTF via the importer) | Studs: 1 stud is about 0.28 m. | Mesh triangle limit per MeshPart is around 20k: say "check current docs". Texture size limits apply: check current docs. |
| Unity | FBX (or glTF through a package) | 1 unit = 1 m. Forward -Z, Up Y on export. | Use "FBX Units Scale" so the import has scale 1. |
| Godot | glTF 2.0 binary (`.glb`) preferred | 1 unit = 1 m, Y-up (converted automatically). | Import hint suffixes in node names (`-col`, `-colonly`, ...). |
| Web / Three.js | GLB | 1 unit = 1 m, Y-up. | Compress with Draco or meshopt; textures as KTX2 where supported. |
| Unreal | FBX | Centimeters. | Collision names `UCX_`, LODs `_LODn`. |

When two options fit, prefer the one the engine skill documents as its default.

## Roblox

- Format: FBX is the safest path; the Studio 3D importer also accepts OBJ and glTF. Check the
  current importer docs for supported features (vertex colors, multiple materials, rigs).
- Scale: 1 stud is about 0.28 m. Choose one convention in the brief:
  (a) model in meters, set the object's real-world size and let the importer scale; or
  (b) model with 1 Blender unit = 1 stud. Then do a test import of a 1-unit cube and compare
  its size in Studio, and adjust `--scale`/export scale until it matches. Do not guess.
- Triangles: keep each MeshPart far below the per-mesh triangle cap (about 20k; check current docs).
  Split large models into several meshes rather than one monolith.
- Pivot: verify in Studio after import; the pivot of the imported MeshPart may follow the mesh
  origin or the bounding-box center depending on importer options. Test-import and read it.
- Textures: PBR or single color map, power-of-two sizes. Upload size limits: check current docs.
  Prefer vertex colors or a small palette texture for flat styles if the importer supports it.
- Triangulate (Triangulate modifier) before export to avoid shading differences from quad triangulation.
- FBX export settings per Roblox docs: Apply Scalings = **FBX Units Scale**, Path Mode = Copy with
  Embed Textures, Add Leaf Bones off. In the 3D Importer, check the Scale Unit setting (Stud vs meters).
- Hand off to `gamesmith-roblox` for MeshPart properties, collision fidelity and asset upload.

## Unity

- FBX settings that make the model import with scale 1 and no rotation:
  - Scale: Apply Scalings = **FBX Units Scale**, Unit scale 1.0
  - Forward = **-Z Forward**, Up = **Y Up** (Blender's FBX defaults)
  - Apply Transform on (bakes the axis conversion into the mesh; if animation/rig problems
    appear, turn it off and apply rotation yourself)
- In Unity's importer: Scale Factor 1, Convert Units on, Bake Axis Conversion matches how you exported.
- Materials: embed textures or ship them next to the FBX; keep material names stable.
- LOD: name meshes `Name_LOD0`, `Name_LOD1`... in one file for an automatic LOD group.
- glTF works through a package (for example glTFast); then follow the Godot/web settings below.
- Hand off to `gamesmith-unity`.

## Godot

- Use glTF 2.0 binary (`.glb`). Godot imports it directly and converts Y-up automatically.
- Import hint suffixes on object names (Godot strips the suffix on import):

| Suffix | Effect |
|---|---|
| `-col` | Adds a trimesh collider alongside the visible mesh |
| `-convcol` | Adds a convex collider alongside the visible mesh |
| `-colonly` | Collider only, mesh is not rendered |
| `-convcolonly` | Convex collider only |
| `-noimp` | Node is skipped on import |

  Verify the full list in the current Godot docs ("Import configuration"). Other hints (such as
  navmesh, occluders, loop animations) exist as well.
- Keep lights and cameras out of the file (export flags below).
- Hand off to `gamesmith-godot`.

## Web / Three.js

- Export GLB with materials, UV0, normals; no cameras or lights.
- Compression, from smallest download to least compatibility concerns:
  - Meshopt (`EXT_meshopt_compression`): good geometry compression, fast decode, works with morphs.
  - Draco (`KHR_draco_mesh_compression`): strong geometry compression, needs the Draco decoder at runtime.
  - Textures: KTX2 (Basis Universal) reduces GPU memory; otherwise keep PNG/JPEG/WebP small.
- Blender can apply Draco on export (`export_draco_mesh_compression_enable=True`). For meshopt and
  KTX2, post-process with glTF-Transform (`gltf-transform optimize in.glb out.glb ...`; check its
  `--help` for the current flags).
- The loader must register the matching decoders (DRACOLoader, MeshoptDecoder, KTX2Loader).
- Hand off to `gamesmith-web`.

## Unreal

- FBX, with centimeters: either set the Blender scene Unit Scale to 0.01 and Length to
  Centimeters while modeling, or export with the scale factor needed to land at 1 uu = 1 cm.
  Test-import a 100 cm cube and confirm it reads 100.
- Collision: separate meshes `UCX_<Name>_00` (convex), `UBX_` (box), `USP_` (sphere), `UCP_` (capsule).
- LODs: `<Name>_LOD0`, `<Name>_LOD1`... in one FBX. Smoothing groups: export face smoothing.
- Lightmap: author UV2 (second UV channel) when baked lighting is used.
- There is no dedicated gamesmith Unreal skill; treat as outside the core pack and ask the user
  to confirm project conventions.

## bpy export calls

Operator argument names occasionally change between Blender versions. The export script filters
keyword arguments against the operator's real property list; do the same when pasting these.

```python
import bpy

def keep_valid(op, **kw):
    valid = set(op.get_rna_type().properties.keys())
    return {k: v for k, v in kw.items() if k in valid}

# FBX (Unity, Roblox, Unreal)
bpy.ops.export_scene.fbx(**keep_valid(
    bpy.ops.export_scene.fbx,
    filepath="//build/asset.fbx",
    use_selection=True,
    object_types={"MESH", "EMPTY"},
    apply_unit_scale=True,
    apply_scale_options="FBX_SCALE_UNITS", # "FBX Units Scale"
    global_scale=1.0,
    axis_forward="-Z",
    axis_up="Y",
    bake_space_transform=True,             # "Apply Transform"
    use_mesh_modifiers=True,
    mesh_smooth_type="FACE",
    use_tspace=False,
    add_leaf_bones=False,
    path_mode="COPY",
    embed_textures=True,
))

# glTF 2.0 binary (Godot, web, Unity via package, Roblox via importer)
bpy.ops.export_scene.gltf(**keep_valid(
    bpy.ops.export_scene.gltf,
    filepath="//build/asset.glb",
    export_format="GLB",
    use_selection=True,
    export_apply=True,                     # apply modifiers
    export_yup=True,
    export_materials="EXPORT",
    export_cameras=False,
    export_lights=False,
    export_draco_mesh_compression_enable=False,
))
```

Notes: `//` paths are relative to the open `.blend`; use absolute paths when running with `-b`
and no file. `use_selection=True` needs the objects selected in the view layer. FBX writes
polygons as-is; add a Triangulate modifier first if the engine needs triangles. Never call
`bpy.ops.wm.save_mainfile` from an export script.
