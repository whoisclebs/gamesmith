"""Validate and export a game asset from Blender, headless.

    blender -b file.blend --python-exit-code 1 -P export_game_asset.py -- --target {roblox,unity,godot,web} --out path [--selection]

Works on the in-memory scene only: transforms are applied to the loaded copy and the .blend
is never saved. Prints a report; exits 1 on hard failures (no export is written then).
"""
import argparse
import os
import sys
import traceback

import bpy
import bmesh
from mathutils import Vector

# (warn_tris, fail_tris). fail_tris=None means warn only. Rough guidance, not engine limits:
# the Roblox fail value mirrors the per-MeshPart triangle cap, check current docs.
BUDGETS = {
    "roblox": (10000, 20000),
    "unity": (30000, None),
    "godot": (30000, None),
    "web": (20000, None),
}
FORMAT = {"roblox": "fbx", "unity": "fbx", "godot": "glb", "web": "glb"}
EPS_AREA = 1e-9
EPS_SCALE = 1e-4


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser(prog="export_game_asset.py")
    p.add_argument("--target", required=True, choices=sorted(BUDGETS))
    p.add_argument("--out", required=True, help="output file (extension is fixed per target)")
    p.add_argument("--selection", action="store_true", help="export only selected objects")
    p.add_argument("--max-tris", type=int, help="override the hard triangle limit")
    p.add_argument("--strict", action="store_true", help="treat warnings as failures")
    p.add_argument("--triangulate", dest="triangulate", action="store_true", default=None)
    p.add_argument("--no-triangulate", dest="triangulate", action="store_false")
    p.add_argument("--scale", type=float, default=1.0, help="FBX custom scale, applied to object transforms (e.g. Roblox studs)")
    p.add_argument("--draco", action="store_true", help="web: Draco-compress the GLB")
    return p.parse_args(argv)


def valid_kwargs(op, **kw):
    """Drop arguments this Blender version's operator does not have."""
    props = set(op.get_rna_type().properties.keys())
    dropped = sorted(k for k in kw if k not in props)
    if dropped:
        print("note: ignored unsupported export args: " + ", ".join(dropped))
    return {k: v for k, v in kw.items() if k in props}


def collect(use_selection):
    pool = bpy.context.selected_objects if use_selection else bpy.context.view_layer.objects
    return [o for o in pool if o.type == "MESH" and o.visible_get()]


def mesh_stats(obj, depsgraph):
    """Evaluated (modifiers applied) triangle count and topology problems."""
    ev = obj.evaluated_get(depsgraph)
    me = ev.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(me)
    s = {
        "tris": sum(len(f.verts) - 2 for f in bm.faces),
        "loose_verts": sum(1 for v in bm.verts if not v.link_edges),
        "loose_edges": sum(1 for e in bm.edges if not e.link_faces),
        "open_edges": sum(1 for e in bm.edges if e.is_boundary),
        "nonmanifold_edges": sum(1 for e in bm.edges if e.link_faces and not e.is_manifold and not e.is_boundary),
        "zero_area": sum(1 for f in bm.faces if f.calc_area() < EPS_AREA),
        "uv_layers": len(me.uv_layers),
        "materials": len([m for m in obj.data.materials if m]),
    }
    bm.free()
    ev.to_mesh_clear()
    return s


def world_bounds(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def apply_transforms(objs, errors, warnings):
    """Apply rotation+scale in memory; make shared mesh data single-user first."""
    mirrored = set()
    for o in objs:
        if o.library or (o.data and o.data.library):
            warnings.append(f"{o.name}: linked from a library, transforms not applied")
            continue
        if o.matrix_world.determinant() < 0:
            mirrored.add(o)
            warnings.append(f"{o.name}: negative scale (mirrored); normals recalculated after apply")
        if o.data.users > 1:
            o.data = o.data.copy()
        unapplied = any(abs(s - 1.0) > EPS_SCALE for s in o.scale)
        if unapplied:
            warnings.append(f"{o.name}: unapplied scale {tuple(round(s, 4) for s in o.scale)} (applied in memory)")
        if o.parent is not None and o.parent.type != "MESH":
            warnings.append(f"{o.name}: parented to '{o.parent.name}'; export keeps hierarchy, check pivot")
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    movable = [o for o in objs if not (o.library or (o.data and o.data.library))]
    for o in movable:
        o.select_set(True)
    if movable:
        bpy.context.view_layer.objects.active = movable[0]
        try:
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        except RuntimeError as exc:
            errors.append(f"transform_apply failed: {exc}")
        for o in movable:  # mirrored objects: make normals point outward again
            if o in mirrored:
                bm = bmesh.new()
                bm.from_mesh(o.data)
                bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
                bm.to_mesh(o.data)
                bm.free()


def add_triangulate(objs):
    for o in objs:
        if o.library:
            continue  # linked objects cannot take new modifiers
        mod = o.modifiers.new("GS_Triangulate", "TRIANGULATE")
        mod.quad_method = "BEAUTY"
        if hasattr(mod, "keep_custom_normals"):  # option removed/renamed in some versions
            mod.keep_custom_normals = True


def export(args, objs, out_path):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)

    if FORMAT[args.target] == "fbx":
        op = bpy.ops.export_scene.fbx
        kw = valid_kwargs(
            op,
            filepath=out_path,
            use_selection=True,
            object_types={"MESH"},
            apply_unit_scale=True,
            apply_scale_options="FBX_SCALE_UNITS",  # "FBX Units Scale", as Roblox docs recommend
            global_scale=args.scale,
            axis_forward="-Z",
            axis_up="Y",
            bake_space_transform=True,
            use_mesh_modifiers=True,
            mesh_smooth_type="FACE",
            add_leaf_bones=False,
            path_mode="COPY",
            embed_textures=True,
        )
    else:
        op = bpy.ops.export_scene.gltf
        kw = valid_kwargs(
            op,
            filepath=out_path,
            export_format="GLB",
            use_selection=True,
            export_apply=True,
            export_yup=True,
            export_materials="EXPORT",
            export_cameras=False,
            export_lights=False,
            export_draco_mesh_compression_enable=bool(args.draco and args.target == "web"),
        )
    result = op(**kw)
    if "FINISHED" not in result:
        raise RuntimeError(f"export operator returned {result}")


def main():
    args = parse_args()
    errors, warnings = [], []
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")  # file saved in Edit mode: flush edits, allow transform_apply

    objs = collect(args.selection)
    if not objs:
        print("FAIL: no visible mesh objects" + (" in selection" if args.selection else ""))
        sys.exit(1)
    others = [o.name for o in bpy.context.view_layer.objects
              if o.type in {"CAMERA", "LIGHT", "ARMATURE"} and o.visible_get()]
    if others:
        warnings.append("not exported (static meshes only): " + ", ".join(others))

    scene = bpy.context.scene
    if scene.unit_settings.system != "NONE" and abs(scene.unit_settings.scale_length - 1.0) > 1e-6:
        warnings.append(f"scene unit scale is {scene.unit_settings.scale_length}, expected 1.0 (meters)")

    apply_transforms(objs, errors, warnings)
    bpy.context.view_layer.update()

    tri_warn, tri_fail = BUDGETS[args.target]
    if args.max_tris:
        tri_fail = args.max_tris
    dg = bpy.context.evaluated_depsgraph_get()
    total = 0
    print(f"== gamesmith-blender report: target={args.target} objects={len(objs)} ==")
    for o in objs:
        s = mesh_stats(o, dg)
        total += s["tris"]
        lo, hi = world_bounds([o])
        d = hi - lo
        print(f"{o.name:28s} tris={s['tris']:6d} size=({d.x:.3f},{d.y:.3f},{d.z:.3f}) m "
              f"open={s['open_edges']} nonman={s['nonmanifold_edges']} "
              f"loose={s['loose_verts']}v/{s['loose_edges']}e zero={s['zero_area']}")
        if s["loose_verts"] or s["loose_edges"]:
            errors.append(f"{o.name}: {s['loose_verts']} loose verts, {s['loose_edges']} loose edges")
        if s["zero_area"]:
            errors.append(f"{o.name}: {s['zero_area']} zero-area faces")
        if s["nonmanifold_edges"]:
            warnings.append(f"{o.name}: {s['nonmanifold_edges']} non-manifold edges (3+ faces)")
        if s["open_edges"]:
            warnings.append(f"{o.name}: {s['open_edges']} open boundary edges (ok for cards/foliage)")
        if not s["uv_layers"]:
            warnings.append(f"{o.name}: no UV map")
        if not s["materials"]:
            warnings.append(f"{o.name}: no material")
        if o.name.startswith(("Cube", "Cylinder", "Sphere", "Plane", "Cone", "Torus")):
            warnings.append(f"{o.name}: default primitive name")

    lo, hi = world_bounds(objs)
    d = hi - lo
    print(f"TOTAL tris={total} (warn>{tri_warn}, fail>{tri_fail})")
    print(f"bounds min=({lo.x:.3f},{lo.y:.3f},{lo.z:.3f}) max=({hi.x:.3f},{hi.y:.3f},{hi.z:.3f}) "
          f"size=({d.x:.3f},{d.y:.3f},{d.z:.3f}) m")
    if abs(lo.z) > 1e-3:
        warnings.append(f"lowest point is at Z={lo.z:.3f}, expected 0 for ground-standing assets")
    if max(d) > 1000 or max(d) < 0.001:
        warnings.append("overall size outside 1 mm - 1 km: check unit scale")
    if tri_fail is not None and total > tri_fail:
        errors.append(f"triangle count {total} exceeds hard limit {tri_fail}")
    elif total > tri_warn:
        warnings.append(f"triangle count {total} exceeds the rough budget {tri_warn}")

    for w in warnings:
        print("WARN:", w)
    for e in errors:
        print("ERROR:", e)
    if errors or (args.strict and warnings):
        print("RESULT: FAIL (nothing exported)")
        sys.exit(1)

    triangulate = args.triangulate if args.triangulate is not None else args.target == "roblox"
    if triangulate and FORMAT[args.target] == "fbx":
        add_triangulate(objs)  # in memory only, the .blend is never saved

    out = os.path.splitext(args.out)[0] + "." + FORMAT[args.target]
    try:
        export(args, objs, out)
    except Exception as exc:  # noqa: BLE001 - report any exporter failure and exit non-zero
        print(f"RESULT: FAIL export error: {exc}")
        sys.exit(1)
    print(f"RESULT: OK -> {out} ({os.path.getsize(out)} bytes)")


if __name__ == "__main__":
    try:
        main()
    except Exception:  # Blender exits 0 on an uncaught script error unless --python-exit-code is set
        traceback.print_exc()
        sys.exit(1)
