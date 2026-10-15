# Unity architecture

## Component design

- A GameObject is a bag of small components. One responsibility per MonoBehaviour (`Health`, `Mover`,
  `Weapon`, `Interactor`); the prefab is the composition.
- Compose with `[RequireComponent(typeof(X))]` and cached `GetComponent` in `Awake`. Cross-object references go
  through serialized fields assigned in the inspector or injected by a spawner (`Init(deps)`).
- Order: `Awake` (own setup, cache components) -> `OnEnable` (subscribe) -> `Start` (use other objects, they
  have run `Awake`). Do not depend on `Awake` order between objects; use script execution order only as a last resort.
- Keep plain C# for pure logic (damage calculation, inventory, rules) and let MonoBehaviours be thin adapters;
  plain classes are unit-testable in EditMode without scenes.
- Prefab workflow: nested prefabs for reusable parts, prefab variants for enemy types, overrides kept minimal.
- Interfaces (`IDamageable`, `IInteractable`) for cross-cutting contracts; query with `TryGetComponent<IDamageable>`.
- Inheritance only for a shallow real "is-a"; otherwise add components or swap a strategy ScriptableObject.

## ScriptableObject patterns

SOs are data assets: shared, serialized, referenced from prefabs and scenes.

| Pattern | Use |
|---|---|
| Config/definition | `EnemyDef`, `ItemDef`, `WeaponStats`: authored data, read-only at runtime |
| Event channel | decoupled broadcast (`VoidEventChannel`, `IntEventChannel`) - see `csharp-patterns.md` |
| Runtime variable/set | `FloatVariable` or `RuntimeSet<T>` that HUD and gameplay both reference |
| Strategy | `MovementBehaviour : ScriptableObject` with `Tick(...)`, swapped per enemy type |
| Database | one SO listing definitions, keyed by id, for save/load lookups |

Rules and traps:
- Edits to SO fields in Play mode persist in the editor (not in builds). Reset runtime values in `OnEnable`, or
  keep mutable state in a runtime copy (`var rt = Instantiate(def)`) or a plain class.
- With Enter Play Mode Options (domain reload disabled), SO and static state survive between plays; reset explicitly.
- SOs have no scene lifecycle; do not store scene object references in them (they would not serialize).
- Give every definition a stable string/GUID `id` field for save files; never save asset names or instance ids.
- Use `[CreateAssetMenu(fileName = "...", menuName = "Game/...")]` so designers can create assets.

## Communication choices

| Mechanism | Pros | Cons / use |
|---|---|---|
| C# `event Action<T>` | fast, typed, no alloc, refactor-safe | code wiring only; always unsubscribe |
| `UnityEvent` | designer wiring in inspector | allocs on invoke, harder to trace; use for UI/one-shot hooks |
| SO event channel | cross-scene, no direct references, inspector-assignable | hides flow if overused; keep a small set |
| Direct reference (`[SerializeField]`) | simplest, traceable | couples prefabs; fine inside one prefab |
| Static event / singleton | convenient | lifetime and domain-reload bugs; avoid for game state |

Default: direct reference or C# event inside a prefab; SO channel across prefabs/scenes (damage dealt, score
changed, level completed, player died).

## State machines

- Small: `enum State` + `switch` in one script, with `Enter/Exit` helper methods on transitions.
- Medium/large: plain C# state classes implementing `IState { Enter(); Tick(); Exit(); }` owned by a
  `StateMachine` (not MonoBehaviours, so they are testable and allocation-free); transitions as explicit
  condition tables or `ChangeState<T>()`.
- Animation-driven: Animator state machine with parameters set from code (`Animator.StringToHash` once, cached);
  keep gameplay truth in code, not in Animator states, unless using StateMachineBehaviours deliberately.
- For AI/behavior: start with a state machine; move to behavior trees/utility AI only when states explode.
- Debug: expose current state in the inspector (`[SerializeField] private State _debugState` or custom gizmo label).

## Save system

- Persist plain serializable data classes, never scene objects or SO references.
- `Application.persistentDataPath` for saves (never `Assets/` or `StreamingAssets`, which are read-only in builds).
- `JsonUtility` is fast and built in but: no dictionaries, no polymorphism, no nullable/top-level arrays, needs
  `[Serializable]` and public/`[SerializeField]` fields. Use Newtonsoft (`com.unity.nuget.newtonsoft-json`) when
  you need dictionaries or complex shapes. Never use `BinaryFormatter` (insecure, removed in recent .NET).

```csharp
using System; using System.Collections.Generic;

[Serializable] public class SaveData
{
    public int version = CurrentVersion;
    public const int CurrentVersion = 2;
    public string sceneId;
    public int coins;                       // v1 called this "gold"
    public List<string> unlockedIds = new();
}

public static class SaveSystem
{
    static string Path(int slot) => System.IO.Path.Combine(Application.persistentDataPath, $"slot{slot}.json");

    public static void Save(int slot, SaveData data)
    {
        string tmp = Path(slot) + ".tmp";
        System.IO.File.WriteAllText(tmp, JsonUtility.ToJson(data, prettyPrint: false));
        if (System.IO.File.Exists(Path(slot))) System.IO.File.Replace(tmp, Path(slot), Path(slot) + ".bak");
        else System.IO.File.Move(tmp, Path(slot));
    }

    public static SaveData Load(int slot)
    {
        try
        {
            var data = JsonUtility.FromJson<SaveData>(System.IO.File.ReadAllText(Path(slot)));
            return data == null ? null : Migrate(data);
        }
        catch (Exception e) when (e is System.IO.IOException or ArgumentException) { return null; }
    }

    static SaveData Migrate(SaveData d)
    {
        // d.version < 2: map old fields forward here, one block per version bump
        d.version = SaveData.CurrentVersion;
        return d;
    }
}
```

Checklist: version field and one migration step per bump; write temp file then replace (no half-written
saves); keep a `.bak`; handle missing/corrupt files by returning null and letting the game start fresh;
keep old-version fixtures in tests; autosave at safe points; PlayerPrefs is for settings only. WebGL saves live in
browser IndexedDB and need a flush before the tab closes (check current docs for the platform behavior).

## Scene management

- Pattern: a tiny `Bootstrap` scene (always first in Build Settings) loads services, then loads the menu/level.
- Use `SceneManager.LoadSceneAsync(name, LoadSceneMode.Additive)` for persistent layers (UI, audio) plus level
  content; unload old levels with `UnloadSceneAsync`. Set the active scene to the level for lighting/spawning.
- Never rely on `DontDestroyOnLoad` for many objects; one persistent services root is enough. Guard against
  duplicates when a scene is opened directly in the editor.
- Pass data between scenes via a scoped carrier (SO "session" asset, or a service on the persistent root), not
  statics.
- Reference scenes by Addressables key, a build-index enum, or a serialized scene-name SO; avoid raw string
  literals scattered in code.
- Loading screen: `allowSceneActivation = false` until progress reaches 0.9, then activate.
- Every scene should be playable alone in the editor (a dev-only `SceneBootstrapper` can load missing services).
