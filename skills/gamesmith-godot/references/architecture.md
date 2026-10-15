# Godot architecture

## Scene composition

- A scene is a reusable prefab-like unit: root node + children + one script on the root when it needs behavior.
- Split by responsibility, not by visual grouping. Typical entity:

```
Player (CharacterBody2D)            player.gd         <- orchestrates
  Sprite (AnimatedSprite2D)
  CollisionShape2D
  Hurtbox (Area2D)                  hurtbox.gd        <- emits `hit_received(damage)`
  Health (Node)                     health.gd         <- owns hp, emits `changed`, `died`
  StateMachine (Node)               state_machine.gd
  Hitbox (Area2D)
```

- Reusable behavior = small component scene/script (`Health`, `Hurtbox`, `Interactor`) added as a child.
  The parent wires them in `_ready()`; components never reach upward.
- Instance scenes with `preload("res://...tscn")` (constant, load-time) or `load()` (runtime), then
  `instantiate()`, set properties, **then** `add_child()` so `_ready` sees configured state.
- Prefer `@export var scene: PackedScene` over hard-coded paths so designers can swap content.
- Inheritance is fine for a shallow, genuine "is-a" (`Enemy` -> `Slime`); beyond two levels, switch to components.
- Inherited scenes (`New Inherited Scene`) give variants of a base scene; override via exported values.

### Referencing nodes

| Need | Use |
|---|---|
| Child in same scene | `@onready var health: Health = %Health` (set Unique Name in editor) |
| Node set per instance | `@export var target: Node2D` assigned in the inspector |
| Many nodes of a role | groups: `add_to_group("enemies")`, `get_tree().get_nodes_in_group("enemies")` |
| Global service | autoload, or pass a reference in `setup(deps)` |

`@onready` runs just before `_ready`; exported node references are valid in `_ready`. A node in the tree
fires `_ready` children-first, so a parent can safely use its children there.

### Scene switching

- Keep a persistent `Main` scene that holds `World` and `UI` children; swap level children instead of
  `get_tree().change_scene_to_packed()` when you need transitions or persistent HUD.
- `change_scene_to_file()` is fine for simple games (menu -> game). For big levels, load threaded with
  `ResourceLoader.load_threaded_request(path)` and poll `load_threaded_get_status`.

## State machines

Pick the lightest option that fits.

| Option | Use when |
|---|---|
| `enum State` + `match` in one script | <= ~5 states, little per-state data |
| Node-based states (`StateMachine` + child `State` nodes) | many states, per-state logic/exports, designers tweak in editor |
| `AnimationTree` state machine | the states are animation-driven; drive via `travel()` and parameters |

```gdscript
# Node-based: state.gd
class_name State extends Node
signal transition_requested(next_state: StringName)
func enter(_msg: Dictionary = {}) -> void: pass
func exit() -> void: pass
func physics_update(_delta: float) -> void: pass

# state_machine.gd
class_name StateMachine extends Node
@export var initial: State
var current: State

func _ready() -> void:
	for child: State in get_children():
		child.transition_requested.connect(_on_transition_requested)
	await owner.ready              # let owner finish setup
	_change(initial.name)

func _physics_process(delta: float) -> void:
	if current: current.physics_update(delta)

func _on_transition_requested(next_state: StringName) -> void:
	_change(next_state)

func _change(state_name: StringName, msg: Dictionary = {}) -> void:
	if current: current.exit()
	current = get_node(NodePath(state_name)) as State
	current.enter(msg)
```

Rules: states request transitions via signal, the machine performs them; the owner exposes data (velocity,
input) and states act on it. Log transitions in debug builds.

## Event bus caveats

An autoload with global signals (`GameEvents.enemy_died.emit(e)`) decouples distant systems (HUD, audio, score).

- Use it for cross-scene, one-to-many facts: `level_completed`, `score_changed`, `player_died`.
- Do not use it for parent/child or sibling-in-scene traffic: it hides flow, hurts debuggability, and invites
  order-of-connection bugs. Direct signals are traceable in the scene.
- Keep payloads small and typed; do not turn it into a global mutable state bag.
- Disconnect in `_exit_tree` for long-lived listeners if the emitter outlives them (connections to freed
  `Object`s are cleaned up automatically, but lambdas capturing state may not behave as intended).
- Alternative without a singleton: a shared `Resource` containing signals (`EventChannel.tres`) exported into
  emitter and listener; works in the inspector and is testable.

## Saving and loading

| Approach | Use for | Notes |
|---|---|---|
| `ConfigFile` | settings, key bindings | simple INI-style, `user://settings.cfg` |
| `FileAccess` + JSON | player save games | safe to load, human-readable, easy to migrate |
| `ResourceSaver.save(res, "user://x.tres")` | editor data, trusted content | **Do not load `.tres`/`.res` from untrusted places** - resources can embed scripts |

Always write to `user://`, never `res://` (read-only in exported builds).

```gdscript
const SAVE_PATH := "user://save.json"
const SAVE_VERSION := 2

func save_game(state: Dictionary) -> bool:
	state["version"] = SAVE_VERSION
	var tmp := SAVE_PATH + ".tmp"
	var f := FileAccess.open(tmp, FileAccess.WRITE)
	if f == null:
		push_error("save failed: %s" % error_string(FileAccess.get_open_error()))
		return false
	f.store_string(JSON.stringify(state, "\t"))
	f.close()
	DirAccess.rename_absolute(tmp, SAVE_PATH)      # swap in only after a full write
	return true

func load_game() -> Dictionary:
	if not FileAccess.file_exists(SAVE_PATH): return {}
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(SAVE_PATH))
	if typeof(parsed) != TYPE_DICTIONARY: return {}   # corrupt: fall back, maybe keep a backup
	return _migrate(parsed)

func _migrate(d: Dictionary) -> Dictionary:
	var v: int = int(d.get("version", 1))              # JSON numbers load as float
	if v < 2:
		d["coins"] = d.get("gold", 0); d.erase("gold") # example: v1 -> v2 rename
		v = 2
	d["version"] = v
	return d
```

Save-system checklist:
- Persist ids and plain data, not node paths or object references; JSON cannot store `Vector2`, `Color`,
  `Resource` directly - convert (`[v.x, v.y]`) or use `var_to_str` / `str_to_var` carefully.
- Give saveable nodes a group (`"persist"`) and a `save() -> Dictionary` / `load_state(d)` pair; the manager
  iterates the group. Keep stable string ids for each entity.
- Version every save; write one migration step per version bump; keep tests with old fixtures.
- Autosave on safe points, not every frame; handle `NOTIFICATION_WM_CLOSE_REQUEST` for quit.
- Web builds persist `user://` in IndexedDB; it can be cleared by the browser, so offer export/import if saves matter.
- Encrypted saves (`FileAccess.open_encrypted_with_pass`) deter casual editing only; the key ships in the game.

## Data with Resources

Define data types as `Resource` subclasses and instance them as `.tres` (see `gdscript-patterns.md`).
Resources are shared by reference: `duplicate()` (or `duplicate(true)` for subresources) before mutating
per-instance runtime state, otherwise every instance changes together. Keep authored data (stats) separate
from runtime state (current hp).

## Autoload decision

Add an autoload only if: it must exist across scene changes, it has no scene-specific dependencies, and passing
it down would be noisy. Typical: `SceneSwitcher`, `AudioManager`, `SaveManager`, `Settings`, optional `GameEvents`.
Everything else belongs in a scene.
