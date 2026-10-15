# C# patterns for Unity

Snippets target Unity 6 with the new Input System package; notes mark 2022 LTS differences. Verify unfamiliar
APIs against the manual for the project's version.

## New Input System: CharacterController movement

Create an Input Actions asset (`PlayerControls.inputactions`) with a Player map: `Move` (Value, Vector2),
`Jump` (Button). Reference actions by `InputActionReference` so wiring is visible in the inspector.

```csharp
using UnityEngine;
using UnityEngine.InputSystem;

[RequireComponent(typeof(CharacterController))]
public class CharacterMover : MonoBehaviour
{
    [SerializeField] private InputActionReference move;
    [SerializeField] private InputActionReference jump;
    [SerializeField] private float speed = 6f;
    [SerializeField] private float jumpHeight = 1.5f;
    [SerializeField] private float gravity = -20f;
    [SerializeField] private Transform cameraTransform;   // movement relative to camera

    private CharacterController _cc;
    private float _verticalVelocity;
    private bool _jumpQueued;

    private void Awake() => _cc = GetComponent<CharacterController>();

    private void OnEnable()  { move.action.Enable(); jump.action.Enable(); jump.action.performed += OnJump; }
    private void OnDisable() { jump.action.performed -= OnJump; jump.action.Disable(); move.action.Disable(); }

    private void OnJump(InputAction.CallbackContext _) => _jumpQueued = true;

    private void Update()                         // CharacterController is not physics-driven: Update is correct
    {
        Vector2 input = move.action.ReadValue<Vector2>();
        Vector3 forward = Vector3.ProjectOnPlane(cameraTransform.forward, Vector3.up).normalized;
        Vector3 right = Vector3.ProjectOnPlane(cameraTransform.right, Vector3.up).normalized;
        Vector3 horizontal = (forward * input.y + right * input.x) * speed;

        if (_cc.isGrounded && _verticalVelocity < 0f) _verticalVelocity = -2f;   // keep grounded
        if (_jumpQueued && _cc.isGrounded) _verticalVelocity = Mathf.Sqrt(jumpHeight * -2f * gravity);
        _jumpQueued = false;
        _verticalVelocity += gravity * Time.deltaTime;

        _cc.Move((horizontal + Vector3.up * _verticalVelocity) * Time.deltaTime);
    }
}
```

Alternatives: `PlayerInput` component, or a generated C# class (`new PlayerControls()`). Always enable/disable the actions you
use. Legacy `Input.GetAxisRaw` works only if the old system is active.

## Rigidbody movement (FixedUpdate)

```csharp
[RequireComponent(typeof(Rigidbody))]
public class RigidbodyMover : MonoBehaviour
{
    [SerializeField] private InputActionReference move;
    [SerializeField] private float speed = 7f;
    [SerializeField] private float acceleration = 40f;
    private Rigidbody _rb;
    private Vector2 _input;

    private void Awake() => _rb = GetComponent<Rigidbody>();
    private void OnEnable()  => move.action.Enable();
    private void OnDisable() => move.action.Disable();
    private void Update()    => _input = move.action.ReadValue<Vector2>();   // read input per frame

    private void FixedUpdate()                                              // apply physics per fixed step
    {
        Vector3 target = new Vector3(_input.x, 0f, _input.y) * speed;
        Vector3 vel = _rb.linearVelocity;                  // Unity 6; use _rb.velocity on 2022 LTS
        Vector3 horizontal = Vector3.MoveTowards(new Vector3(vel.x, 0f, vel.z), target, acceleration * Time.fixedDeltaTime);
        _rb.linearVelocity = new Vector3(horizontal.x, vel.y, horizontal.z);
    }
}
```

Set Interpolation = Interpolate on player/camera targets; move with `MovePosition`/velocity, not `transform`.
Ground check: `Physics.CheckSphere(feet.position, 0.2f, groundMask, QueryTriggerInteraction.Ignore)`.
Coyote time and jump buffering: keep two float timers refreshed on grounded/press, decremented by `Time.deltaTime`.

## Object pool (UnityEngine.Pool)

```csharp
using UnityEngine;
using UnityEngine.Pool;

public class BulletSpawner : MonoBehaviour
{
    [SerializeField] private Bullet prefab;
    private ObjectPool<Bullet> _pool;

    private void Awake()
    {
        _pool = new ObjectPool<Bullet>(
            createFunc: () => { var b = Instantiate(prefab); b.Init(_pool); return b; },
            actionOnGet: b => b.gameObject.SetActive(true),
            actionOnRelease: b => b.gameObject.SetActive(false),
            actionOnDestroy: b => Destroy(b.gameObject),
            collectionCheck: true,          // editor-only double-release detection
            defaultCapacity: 32, maxSize: 256);
    }

    public void Fire(Vector3 pos, Quaternion rot) { var b = _pool.Get(); b.transform.SetPositionAndRotation(pos, rot); b.Launch(); }
}

public class Bullet : MonoBehaviour
{
    private IObjectPool<Bullet> _pool;
    public void Init(IObjectPool<Bullet> pool) => _pool = pool;
    public void Launch() { /* reset velocity/timers/trails here */ }
    private void OnCollisionEnter(Collision _) => _pool.Release(this);
}
```

Also `ListPool<T>.Get(out var list)` / `CollectionPool` for temporary collections (dispose via `using`).
Reset all runtime state on Get; guard against releasing twice.

## ScriptableObject config

```csharp
[CreateAssetMenu(fileName = "EnemyDef", menuName = "Game/Enemy Definition")]
public class EnemyDef : ScriptableObject
{
    [field: SerializeField] public string Id { get; private set; }
    [field: SerializeField, Min(1)] public int MaxHealth { get; private set; } = 3;
    [field: SerializeField] public float MoveSpeed { get; private set; } = 2.5f;
    [field: SerializeField] public GameObject Prefab { get; private set; }
}
```

Runtime state (current health) lives in the consuming MonoBehaviour (`_health = def.MaxHealth` in `OnEnable`), not in the SO.

## Event channel (SO)

```csharp
using System;
using UnityEngine;

[CreateAssetMenu(menuName = "Events/Int Event")]
public class IntEventChannel : ScriptableObject
{
    public event Action<int> Raised;
    public void Raise(int value) => Raised?.Invoke(value);
}

public class ScoreLabel : MonoBehaviour
{
    [SerializeField] private IntEventChannel scoreChanged;
    [SerializeField] private TMPro.TMP_Text label;
    private int _total;
    private void OnEnable()  => scoreChanged.Raised += OnScore;
    private void OnDisable() => scoreChanged.Raised -= OnScore;
    private void OnScore(int delta) { _total += delta; label.text = _total.ToString(); }
}
```

Create one asset per event (e.g. `ScriptableObjects/Events/ScoreChanged.asset`), assign the same asset to emitter and
listener, and call `scoreChanged.Raise(n)` from the emitter. Always unsubscribe in `OnDisable`, especially with domain reload off.

## Async and coroutines

```csharp
private async Awaitable FlashRoutine()      // Unity 6 Awaitable; pass destroyCancellationToken so it stops with the object
{
    for (int i = 0; i < 3; i++) { sprite.enabled = !sprite.enabled; await Awaitable.WaitForSecondsAsync(0.1f, destroyCancellationToken); }
}

// 2022 LTS and general: coroutine; cache yield instructions.
private static readonly WaitForSeconds Wait01 = new(0.1f);
private IEnumerator Flash() { for (int i = 0; i < 3; i++) { sprite.enabled = !sprite.enabled; yield return Wait01; } }
```

Start with `StartCoroutine(Flash())`. A token makes awaits throw `OperationCanceledException` when the object is destroyed;
prefer `async Awaitable` over `async void`, and never touch Unity APIs off the main thread.
