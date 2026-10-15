---
name: gamesmith-godot
description: Build and review Godot 4.x games (GDScript first, C# notes) - scene composition, typed GDScript, signals, Resources, saves, performance, export and tests. Use when a project has project.godot, .tscn/.gd files, or the user asks to make, fix, refactor, optimize, test or export a Godot game.
license: MIT
metadata:
  author: gamesmith
  engine: godot
  version: "1.0"
---

# gamesmith-godot

Engine skill for Godot 4.x. Design, scope, game feel, balancing and release process live in the
`gamesmith` skill; 3D asset creation and export live in `gamesmith-blender`. This skill covers
how to build the game inside Godot correctly.

## Step 0 - detect the project and pin the version

1. Read `project.godot` at the project root.
   - `config_version=5` means Godot 4.x (`4` means Godot 3: stop, this skill does not apply).
   - `config/features=PackedStringArray("4.3", "Forward Plus")` gives the minor version and renderer
     (Forward Plus, Mobile, or Compatibility).
   - Note `[autoload]`, `[input]` (action names), `[layer_names]`, and `run/main_scene`.
2. Check for C#: any `*.csproj` / `*.sln` next to `project.godot` means the .NET build. Read the C# notes below.
3. Check `addons/` for GUT, gdUnit4, and other plugins before suggesting a test or tool.
4. Version-pin warning: your knowledge of Godot APIs may lag the project's version. Before using an API you
   are not certain exists in that minor version, check the official docs for that version
   (docs.godotengine.org, version selector) or the project's own code. Known moving parts: `TileMap` vs
   `TileMapLayer` (4.3+), typed `Dictionary` (4.4+), `get_gravity()` on bodies (4.3+), `.uid` files (4.4+),
   web export threading defaults, physics engine options. If unsure, say so and verify; do not guess.
5. If there is no project yet, create the layout below and a minimal `project.godot` via the editor or
   `godot --headless --path . --quit` after writing it by hand; confirm the Godot version with the user.

## Core rules

| Area | Rule |
|---|---|
| Typing | Static types everywhere: `var hp: int = 10`, `func hit(dmg: int) -> void`, `Array[Enemy]`. Use `:=` only when the type is obvious. |
| Composition | One scene = one reusable thing with one job. Build entities from child nodes/scenes, not deep inheritance. |
| Messaging | "Call down, signal up": parents call methods on children; children emit signals, never reach into parents. Siblings talk via a shared parent or an injected reference. |
| Signals | Declare with typed args, connect in `_ready()` (or in the editor), emit with `.emit()`. Name past tense: `died`, `health_changed`. |
| Async | Use `await` (`await get_tree().create_timer(1.0).timeout`), never `yield`. Guard against freed nodes after awaits (`is_instance_valid`). |
| Data | Tunable data lives in `Resource` subclasses saved as `.tres` (`class_name`, `@export`), not in scattered constants. |
| Autoloads | Sparingly: only truly global services (audio bus helper, scene switcher, settings, save manager). No gameplay state in autoloads that scenes could own. |
| Loop | Physics and movement in `_physics_process`; visuals/UI/input polling in `_process`. Never move bodies in `_process`. |
| Idle cost | Disable what is not needed: `set_physics_process(false)`, `process_mode = Node.PROCESS_MODE_DISABLED`, hide + disable collision shapes for pooled or off-screen things. |
| Animation | `create_tween()` / `AnimationPlayer` over manual lerp in `_process`. Kill or replace a running tween before starting another on the same property. |
| Spawning | Pool frequently spawned nodes (bullets, particles, popups); `queue_free` for rare ones. |
| Node access | No long `get_node("A/B/C/D")` chains. Use `%UniqueName` (same scene), `@export var target: Node`, or groups for cross-scene lookups. |
| Groups | Tag by role (`"enemies"`, `"interactable"`); use `get_tree().call_group` / `get_nodes_in_group` outside hot paths. |
| Input | Define actions in the Input Map; query by action name, never by raw keycode. Keep gamepad + keyboard bound to the same action. |
| Physics | Name layers in Project Settings; set `collision_layer` (what I am) and `collision_mask` (what I detect) deliberately. |

## Project layout

```
res://
  project.godot
  scenes/            # main.tscn, level scenes (or group by feature below)
  entities/player/   # player.tscn + player.gd + player_stats.tres  (keep scene + script together)
  entities/enemies/
  ui/                # hud.tscn, menus, themes
  resources/         # custom Resource scripts (*.gd) and data (*.tres)
  autoload/          # game_events.gd, save_manager.gd ... (only if justified)
  assets/            # art/ audio/ fonts/ (imported files)
  addons/            # third-party plugins
  tests/             # GUT / gdUnit4 tests
```

Conventions: files `snake_case`, node names and `class_name` `PascalCase`, signals/functions `snake_case`,
constants `UPPER_SNAKE`. Commit `.uid` files (4.4+) and `export_presets.cfg`; ignore `.godot/` (it holds cache and export credentials).

## Workflow

1. Restate the feature as scene tree + scripts + data resources before coding.
2. Build the smallest playable slice first (one scene runs with F6); then add systems.
3. Wire via signals and exported references; avoid hidden globals.
4. Run it: `godot --path . --headless --quit-after 60` smoke-checks that scripts parse and the main scene loads
   (flag availability depends on version; check `godot --help`). Open the editor Debugger for errors.
5. Add tests for logic that is not scene-bound (rules, inventory, save migration, damage math).
6. Profile before optimizing (Debugger > Profiler / Monitors); see the performance reference.

## Deliverables (always report these)

- Scene tree for every new or changed scene (indented node list with node types and attached scripts).
- Script paths with one line each on responsibility, plus signals emitted and groups used.
- Input Map actions and physics layer names the feature expects (add them to `project.godot` or list exact edits).
- Resource types and example `.tres` files created.
- Test steps: how to run the scene, what to press, what to observe, plus any automated test command.
- Known limits, version assumptions, and anything **NOT ASSESSED** (e.g. performance on target hardware).

## C# notes (.NET build)

- Classes must be `partial` and match the file name; `using Godot;`. Export with `[Export]`, signals with
  `[Signal] public delegate void DiedEventHandler();` and `EmitSignal(SignalName.Died)`.
- Prefer `GetNode<T>("%Name")`; connect with `node.Died += OnDied;` and unsubscribe in `_ExitTree`.
- Use the same rules above (composition, call down/signal up, Resources via `[GlobalClass] partial class X : Resource`).
- Rebuild after editing C# (editor Build button or `dotnet build`) before running.
- Web export support for C# has been limited in 4.x; check current docs before choosing C# for a web target.
- Mixing GDScript and C# calls works but is slower and type-loose at the boundary; keep the boundary thin.

## Anti-patterns to flag in review

- `get_parent().get_parent()` chains; children mutating parent state.
- Gameplay logic in autoloads; a god `Game` singleton holding player, UI and enemies.
- Polling in `_process` where a signal or `Timer` fits.
- Untyped `var x = ...` in new code; untyped `Array`/`Dictionary` of known shapes.
- Loading `.tres` saves from untrusted sources (resources can embed scripts); use JSON for player saves.
- Creating `Tween`s every frame; connecting the same signal repeatedly (use `is_connected` or `CONNECT_ONE_SHOT`).

## Reference index

Read only what the task needs.

| File | Read when |
|---|---|
| `references/architecture.md` | Structuring scenes, state machines, event bus decisions, save/load and save versioning. |
| `references/gdscript-patterns.md` | Writing typed code: character controllers, coyote time, input, signals, custom Resources, pooling, tweens. |
| `references/performance-and-export.md` | Profiling, MultiMesh, physics layers/masks, export presets, web caveats, GUT/gdUnit4, headless CI export. |
