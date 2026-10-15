# bpy patterns and MCP usage

Targets Blender 4.x/5.x. Snippets are short and complete; combine them into one build script.

## Headless skeleton

```python
# build_crate.py  -> blender -b -P build_crate.py -- --out build/crate.blend --size 0.6
import argparse, sys
import bpy, bmesh

def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True)
    p.add_argument("--size", type=float, default=0.6)
    return p.parse_args(argv)

def clear_scene():
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for item in list(coll):
            if item.users == 0:
                coll.remove(item)

if __name__ == "__main__":
    args = parse_args()
    clear_scene()
    # ... build ...
```

Everything after `--` belongs to your script; Blender ignores it. Print with `print(...)`;
stdout reaches the terminal. Exit non-zero with `sys.exit(1)` when a check fails.

Set metric units once:

```python
s = bpy.context.scene
s.unit_settings.system = "METRIC"
s.unit_settings.scale_length = 1.0
s.unit_settings.length_unit = "METERS"
```

## Mesh via bmesh (no ops, no context needed)

```python
def make_box(name, size, center=(0, 0, 0), collection=None):
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:                       # scale per axis, then move
        v.co.x = v.co.x * size[0] + center[0]
        v.co.y = v.co.y * size[1] + center[1]
        v.co.z = v.co.z * size[2] + center[2]
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    (collection or bpy.context.scene.collection).objects.link(obj)
    return obj

def make_collection(name):
    c = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(c)
    return c
```

Faceted cylinder: `bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=r, radius2=r, depth=h)`.

## Transforms, origin, normals

```python
def select_only(obj):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

def apply_transforms(obj):
    if obj.data.users > 1:
        obj.data = obj.data.copy()            # single-user first
    select_only(obj)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

def set_origin_base_center(obj):
    """Move origin to bottom center of the bounding box, keep the mesh in place."""
    from mathutils import Matrix, Vector
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    base = Vector((sum(p.x for p in pts) / 8, sum(p.y for p in pts) / 8, min(p.z for p in pts)))
    offset = obj.matrix_world.inverted() @ base
    obj.data.transform(Matrix.Translation(-offset))
    obj.location = base

def recalc_normals(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()

def merge_by_distance(obj, dist=1e-4):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=dist)
    bm.to_mesh(obj.data)
    bm.free()
```

Flat vs smooth shading: `for p in obj.data.polygons: p.use_smooth = False`. Angle-based smooth
(4.1+): `bpy.ops.object.shade_smooth_by_angle(angle=0.5236)` with the object active and selected.

## UVs

```python
import math
def smart_uv(obj, margin=0.02):
    select_only(obj)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=margin)
    bpy.ops.object.mode_set(mode="OBJECT")
```

Second UV set for lightmaps: `obj.data.uv_layers.new(name="UV2")`, make it active, unwrap again,
then reset `obj.data.uv_layers.active_index = 0`.

## Materials and slots

```python
def get_material(name, rgba):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True                         # default in 5.x; harmless
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Roughness"].default_value = 0.8
    return m

def assign_band(obj, material, faces):
    if material.name not in [s.material.name for s in obj.material_slots if s.material]:
        obj.data.materials.append(material)
    idx = [s.material for s in obj.material_slots].index(material)
    for f in faces:
        f.material_index = idx
```

For color bands, assign by face position (`poly.center.z` ranges) in one pass over `obj.data.polygons`.

## Measuring and logging stats

```python
from mathutils import Vector

def world_bbox(obj):
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi

def gap_along_z(a, b):
    """Positive = floating gap, 0 = touching, negative = overlap (b above a)."""
    return world_bbox(b)[0].z - world_bbox(a)[1].z

def tri_count(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    me = obj.evaluated_get(dg).to_mesh()
    n = sum(len(p.vertices) - 2 for p in me.polygons)
    obj.evaluated_get(dg).to_mesh_clear()
    return n

def report(objs):
    total = 0
    for o in objs:
        lo, hi = world_bbox(o)
        d = hi - lo
        t = tri_count(o)
        total += t
        print(f"{o.name:24s} tris={t:6d} size=({d.x:.3f},{d.y:.3f},{d.z:.3f}) "
              f"min=({lo.x:.3f},{lo.y:.3f},{lo.z:.3f})")
    print(f"TOTAL tris={total}")
```

Gap checks need a tolerance (`abs(gap) < 1e-4`). Print and assert; a failed assert in a script is
a useful stop. Update the depsgraph (`bpy.context.view_layer.update()`) after moving objects and
before reading `matrix_world`.

## Rendering a six-side check headlessly

Use a temporary camera and a flat light in a throwaway scene, render 6 angles with
`bpy.ops.render.render(write_still=True)` to `build/check_<side>.png`, then delete the helpers.
Use the Workbench engine (`scene.render.engine = "BLENDER_WORKBENCH"`) for speed. Keep helpers
out of the asset collection so they never reach the export.

## Live Blender MCP

Prefer a script file; when a live MCP connection is the only route, follow these habits:

1. **Inspect first.** Ask for scene info (objects, units, selected, mode) before changing anything.
2. **Small idempotent chunks.** One logical step per call (build part, then verify, then next).
   Each chunk should be safe to run twice: look up by name and replace, do not blindly add
   `Cube.001`, `Cube.002`.
3. **Inspect after each step.** Print object names, bbox, tri counts and return them; do not assume
   success because no error appeared.
4. **Screenshots are for intent, numbers are for truth.** Take the viewport screenshot for a
   visual sanity check and compare it with the printed bounding boxes.
5. **Context matters.** Operators (`bpy.ops`) need object mode and an active object; ensure
   `mode_set(mode="OBJECT")` first, and prefer data-API/bmesh code in MCP chunks.
6. **Keep the source of truth in a file.** When the model is done, write the whole build into
   a script in the project, run it headless from empty, and confirm the output matches.
7. **Confirm destructive actions.** Ask before deleting or overwriting objects the user made.
8. **Long operations.** Avoid heavy booleans/subdivision/renders in a single MCP call; they can time out.
9. **Limited connectors.** If the connector exposes only a fixed command set,
   fall back to running a Python snippet; if none exists, switch to headless mode.
10. **Save deliberately.** Save the source `.blend` only on request, under a new name; export to a
    separate folder.
