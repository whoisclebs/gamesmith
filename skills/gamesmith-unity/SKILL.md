---
name: gamesmith-unity
description: Build and review Unity games (Unity 6 and 2022 LTS+, C#) - component design, ScriptableObject data and events, Input System, pooling, saves, profiling, builds, tests and CI. Use when a project has ProjectSettings/ProjectVersion.txt, Assets/ with .cs/.unity/.prefab files, or the user asks to make, fix, refactor, optimize, test or build a Unity game.
license: MIT
metadata:
  author: gamesmith
  engine: unity
  version: "1.0"
---

# gamesmith-unity

Engine skill for Unity (Unity 6 / 6000.x and 2022.3 LTS or newer). Design, scope, game feel, balancing and
release process live in the `gamesmith` skill; 3D asset creation and export live in `gamesmith-blender`.
This skill covers how to build the game inside Unity correctly.

## Step 0 - detect the project and pin the version

1. Read `ProjectSettings/ProjectVersion.txt`: `m_EditorVersion: 6000.x` is Unity 6; `2022.3.x` is 2022 LTS;
   older than 2021.3 is out of scope (say so).
2. Render pipeline: read `Packages/manifest.json`.
   - `com.unity.render-pipelines.universal` = URP, `com.unity.render-pipelines.high-definition` = HDRP,
     neither = Built-in. Confirm the assigned asset in `ProjectSettings/GraphicsSettings.asset`.
   - Shaders and materials must match the pipeline; never mix Built-in shaders into URP/HDRP.
3. Input: `com.unity.inputsystem` in the manifest = new Input System; check `activeInputHandler` in
   `ProjectSettings/ProjectSettings.asset` (0 legacy, 1 new, 2 both). Use whichever the project uses; do not
   switch silently. Legacy `Input.GetAxis` throws when only the new system is active.
4. Look for `.asmdef` files, `Addressables`, `Cinemachine`, `TextMeshPro`, UI Toolkit vs uGUI, and a test
   framework package before suggesting anything that depends on them.
5. Version-pin warning: your Unity API knowledge may lag the project's version. Before using an API you are not
   sure exists in that version, check the Unity manual/scripting API for that version or the project's code.
   Known moving parts: `Rigidbody.linearVelocity` (Unity 6) vs `velocity` (2022); `Awaitable` (Unity 6 only,
   not 2022 LTS); `FindFirstObjectByType` / `FindObjectsByType` replacing `FindObjectOfType`; Build Profiles
   (Unity 6); `UnityEngine.Pool` (2021.1+); Unity UI / TMP packaging changes. Do not guess.

## Core rules

| Area | Rule |
|---|---|
| Data | Tunable and shared data in `ScriptableObject` assets (stats, items, waves, config). Do not mutate shared SO assets at runtime unless intended: in the editor changes persist after play, in builds they do not. |
| Fields | `[SerializeField] private` over `public` fields. Expose read-only state via properties. Rename serialized fields with `[FormerlySerializedAs]`. |
| Caching | Never `Find*`, `GetComponent*`, `Camera.main` lookups, or `tag ==` in `Update`. Cache in `Awake`/`Start`; prefer `TryGetComponent`, `CompareTag`. |
| Loops | `Update` for input/visuals/non-physics; `FixedUpdate` for Rigidbody forces and velocity; `LateUpdate` for cameras that follow. Inside `Update` scale by `Time.deltaTime`; do not scale by it in `FixedUpdate` for forces (use fixed step). |
| Events | Decouple with C# `event Action<T>`, `UnityEvent` for designer wiring, or SO event channels. Subscribe in `OnEnable`, unsubscribe in `OnDisable`. |
| State | No global singletons for game state. If a service must be global (audio, save, scene loader), scope it, expose an interface, and reset statics (domain reload may be off). |
| Spawning | Pool frequently created objects with `UnityEngine.Pool.ObjectPool<T>`; do not `Instantiate`/`Destroy` per bullet. |
| Async | Unity 6: `Awaitable` with `destroyCancellationToken`. 2022 LTS: coroutines (or `Task` + `destroyCancellationToken` carefully). Coroutines die with the disabled/destroyed object; async code must be cancelled. |
| Structure | Assembly definitions (`.asmdef`) per module (Runtime, Editor, Tests) for compile time and enforced dependencies. |
| Content | Addressables for large or on-demand content; always release handles. Small games can use direct references. |
| Allocations | No LINQ, string concatenation, boxing, or closure allocation in hot paths; reuse lists and arrays. |
| Physics | Name layers; configure the Layer Collision Matrix; use `LayerMask` serialized fields; prefer non-alloc queries. |
| Editor | Keep inspector wiring explicit with `[Header]`, `[Tooltip]`, `[Range]`, `[RequireComponent]`, `OnValidate` checks. Commit `.meta` files. |

## Project layout

```
Assets/
  _Project/
    Scripts/
      Runtime/      # Game.Runtime.asmdef : Player/, Enemies/, UI/, Core/
      Editor/       # Game.Editor.asmdef (editor-only tools, custom inspectors)
      Tests/EditMode/  Tests/PlayMode/   # test asmdefs
    Scenes/         # Bootstrap.unity, MainMenu.unity, Level_01.unity
    Prefabs/  ScriptableObjects/  Art/  Audio/  Settings/ (input actions, URP assets)
  Plugins/  Resources/ (avoid; use Addressables or direct references)
```

Conventions: `PascalCase` types, methods, properties; `_camelCase` private fields; one MonoBehaviour per file with a
matching file name (required by Unity). Version control: ignore `Library/`, `Temp/`, `Obj/`, `Logs/`, `UserSettings/`,
build output; commit `Assets/`, `Packages/`, `ProjectSettings/`, and all `.meta` files (force text serialization).

## Workflow

1. Restate the feature as GameObject/prefab hierarchy + scripts + ScriptableObjects before coding.
2. Make the smallest playable slice in one scene; add systems after it runs.
3. Wire dependencies through serialized references and event channels, not `Find`.
4. Compile-check: recompile in the editor or run a batchmode build/test (see performance reference); fix every
   console error and warning you introduced.
5. Test logic with EditMode tests, behavior over frames with PlayMode tests.
6. Profile before optimizing, on a development build on target hardware where possible.

## Deliverables (always report these)

- Script paths (one line each: responsibility, serialized fields, events raised/consumed).
- Scene and prefab setup steps: which GameObjects to create, components to add, tags/layers, prefab variants.
- Inspector wiring: every serialized field to assign and the expected value or asset.
- ScriptableObject assets to create (menu path under Create, example values).
- Project settings changes: layers, Input Actions asset, physics matrix, scenes in Build Settings/Profiles.
- Test steps: how to enter Play mode, controls, what to observe, plus automated test commands.
- Known limits, version assumptions, and anything **NOT ASSESSED** (e.g. frame time on target device).

## Anti-patterns to flag in review

- `public` fields everywhere; logic in a god `GameManager` singleton; `static` mutable state.
- `GameObject.Find("Name")` or string-based `SendMessage`/`Invoke("Method")` in gameplay code.
- Physics via `transform.position` on Rigidbody objects; Rigidbody movement in `Update`.
- Subscribing to events without unsubscribing; async methods that outlive their GameObject.
- Mutating SO assets for per-instance runtime state (all instances share it); use a runtime copy
  (`Instantiate(so)`) or a plain runtime class.
- `Resources.Load` as the default content path; per-frame `new` allocations; `BinaryFormatter` for saves.
- Editing generated code or Library files; committing `Library/`.

## Reference index

Read only what the task needs.

| File | Read when |
|---|---|
| `references/architecture.md` | Component design, SO-based events and variables, state machines, save system and versioning, scene management. |
| `references/csharp-patterns.md` | Writing code: Input System movement (CharacterController and Rigidbody), pooling, SO config, event channel, cancellation-safe async. |
| `references/performance-and-build.md` | Profiler/Frame Debugger, GC avoidance, batching and LOD, physics layers, build profiles, Unity Test Framework, batchmode CI and game-ci. |
