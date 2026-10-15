# GDScript patterns (Godot 4.x, typed)

Snippets target 4.3+; call out where older minors differ. Verify unfamiliar APIs against the docs for the
project's version.

## Script skeleton and member order

```gdscript
class_name Enemy
extends CharacterBody2D
## One-line doc comment shown in the editor help.

signal died(enemy: Enemy)

@export var stats: EnemyStats
@export_range(0.0, 10.0, 0.1) var aggro_time: float = 2.0

var target: Node2D

@onready var sprite: AnimatedSprite2D = %Sprite
```

Order: signals, enums, constants, `@export`, vars, `@onready`, virtuals, public methods, private methods, `_on_*` callbacks.

## Input map usage

Define actions in Project Settings > Input Map (`move_left`, `move_right`, `move_up`, `move_down`, `jump`, `attack`, `pause`).

```gdscript
var dir: float = Input.get_axis("move_left", "move_right")        # -1..1, analog-aware
var vec: Vector2 = Input.get_vector("move_left", "move_right", "move_up", "move_down") # deadzone + normalized

if Input.is_action_just_pressed("jump"): ...   # polled, fine in _physics_process
func _unhandled_input(event: InputEvent) -> void:  # event-driven; UI gets first chance
	if event.is_action_pressed("pause"):
		get_viewport().set_input_as_handled()
```

Use `_unhandled_input` for gameplay so UI controls consume clicks first. Rebinding at runtime:
`InputMap.action_erase_events(a)` then `InputMap.action_add_event(a, ev)`; persist via `ConfigFile`.

## 2D platformer controller with coyote time and jump buffer

```gdscript
class_name PlayerController
extends CharacterBody2D

signal jumped

@export var speed: float = 220.0
@export var accel: float = 1600.0
@export var jump_velocity: float = -420.0
@export var coyote_time: float = 0.10
@export var jump_buffer_time: float = 0.12
@export_range(0.0, 1.0) var jump_cut: float = 0.5

var _coyote: float = 0.0
var _buffer: float = 0.0

func _physics_process(delta: float) -> void:
	var on_floor: bool = is_on_floor()
	_coyote = coyote_time if on_floor else maxf(_coyote - delta, 0.0)
	_buffer = jump_buffer_time if Input.is_action_just_pressed("jump") else maxf(_buffer - delta, 0.0)

	if not on_floor:
		velocity += get_gravity() * delta          # get_gravity(): 4.3+; older: ProjectSettings default_gravity

	if _buffer > 0.0 and _coyote > 0.0:            # works for both buffered presses and late jumps
		velocity.y = jump_velocity
		_buffer = 0.0
		_coyote = 0.0
		jumped.emit()
	if Input.is_action_just_released("jump") and velocity.y < 0.0:
		velocity.y *= jump_cut                      # variable jump height

	var dir: float = Input.get_axis("move_left", "move_right")
	velocity.x = move_toward(velocity.x, dir * speed, accel * delta)
	move_and_slide()

```

Tuning knobs are `@export` so game feel can change without code edits (see `gamesmith`). Cap falling with `velocity.y = minf(velocity.y, max_fall_speed)`.

## Signals

```gdscript
signal health_changed(current: int, maximum: int)

func _ready() -> void:
	health.health_changed.connect(_on_health_changed)
	button.pressed.connect(_on_start_pressed)
	timer.timeout.connect(func() -> void: queue_free(), CONNECT_ONE_SHOT)

func take_damage(d: int) -> void: hp -= d; health_changed.emit(hp, max_hp)

var body: Node2D = await area.body_entered
await get_tree().create_timer(0.5).timeout
```

Bind extra args with `.bind(x)`; disconnect with `sig.disconnect(callable)`; check `is_connected`.
After any `await`, re-check `is_instance_valid(self)` / `is_inside_tree()` if the node could have been freed.

## Custom Resource for data

```gdscript
# resources/enemy_stats.gd
class_name EnemyStats
extends Resource

@export var display_name: String = "Slime"
@export var max_health: int = 3
@export var move_speed: float = 60.0
@export var loot: Array[ItemData] = []
@export_group("Audio")
@export var hit_sfx: AudioStream
```

Create via FileSystem > New Resource > EnemyStats, save as `res://resources/enemies/slime.tres`, then assign
to an `@export var stats: EnemyStats`. Runtime-mutable copy: `var rt: EnemyStats = stats.duplicate()`.
Typed arrays of resources and `@export_group` need Godot 4.0+; typed `Dictionary[K, V]` needs 4.4+.

## Tween

```gdscript
func pop() -> void:
	if _tween and _tween.is_valid(): _tween.kill()
	_tween = create_tween().set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	_tween.tween_property(sprite, "scale", Vector2.ONE * 1.2, 0.08)
	_tween.tween_property(sprite, "scale", Vector2.ONE, 0.12)
	_tween.parallel().tween_property(sprite, "modulate", Color.WHITE, 0.12)
var _tween: Tween
```

`create_tween()` binds to the node (stops when freed). Use `tween_callback`, `set_loops()`,
`set_parallel(true)`; `tween_method` for non-property values.

## Object pool

```gdscript
class_name Pool
extends Node

@export var scene: PackedScene
@export var prewarm: int = 32
var _free: Array[Node2D] = []   # use Node3D for 3D scenes (plain Node has no show/hide)

func _ready() -> void:
	for i in prewarm: _free.append(_make())

func acquire() -> Node2D:
	var n: Node2D = _free.pop_back() if not _free.is_empty() else _make()
	n.process_mode = Node.PROCESS_MODE_INHERIT
	n.show()
	return n

func release(n: Node2D) -> void:
	_park(n)
	_free.append(n)

func _make() -> Node2D:
	var n: Node2D = scene.instantiate()
	add_child(n)
	_park(n)
	return n

func _park(n: Node2D) -> void:
	n.hide()
	n.process_mode = Node.PROCESS_MODE_DISABLED
```

Reset state in `acquire` consumers (position, velocity, timers, collision on/off). Disable `CollisionShape2D`
via `set_deferred("disabled", true)` when releasing inside physics callbacks.

## Notes

- Top-down 2D: `velocity = Input.get_vector(...) * speed` with `motion_mode = MOTION_MODE_FLOATING`.
- 3D: same as the platformer on `CharacterBody3D`; direction = `global_transform.basis * Vector3(i.x, 0, i.y)`,
  mouse look rotates body on Y and head on X (clamp pitch), capture the mouse.
- Defer changes inside physics callbacks: `call_deferred(...)`, `set_deferred("disabled", true)`.
- `Timer` / `get_tree().create_timer` for cooldowns; `Engine.time_scale` for hit-stop (always restore it).
