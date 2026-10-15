# Performance, build, testing and CI (Unity)

Measure first. Never claim a speedup without a profiler capture; if you could not run the game, mark
performance **NOT ASSESSED**. Profile a Development Build on target hardware, not only the editor.

## Profiling tools

| Tool | Use |
|---|---|
| Profiler (Window > Analysis) | CPU (timeline/hierarchy), GC Alloc column, rendering, physics, audio; connect to a Development Build |
| Deep Profile | exact call costs but heavy overhead; use briefly on a narrowed scope |
| `ProfilerMarker` / `Profiler.BeginSample` | label your own hot code so it appears by name |
| Frame Debugger | step through draw calls; find why batching broke, overdraw, unexpected passes |
| Memory Profiler (package) | snapshots, leaks, texture/mesh memory, managed heap |
| Profile Analyzer (package) | compare captures before/after a change |
| Rendering Debugger (URP/HDRP) | overdraw, lighting, culling views |
| Stats / Game view | quick draw call, batches, SetPass counts |

Workflow: capture 300+ frames of the slow scenario, find the top self-time entries and GC Alloc spikes, decide
CPU vs GPU bound (a long wait in `Gfx.WaitForPresent` or a rendering thread dominating suggests GPU bound),
fix one thing, recapture, compare.

## Avoiding GC allocations

- Per-frame allocation target is zero in gameplay loops; spikes cause hitches. Check the GC Alloc column.
- Avoid: LINQ, `string` concatenation/interpolation in `Update`, `foreach` over non-struct enumerators of
  interfaces, boxing (`object`, non-generic collections), lambdas/closures capturing locals in hot paths,
  `new List<T>()` per frame, `GetComponents` (list-returning), `tag ==`, `Camera.main` in old versions.
- Prefer: cached collections cleared and reused, `List<T>` overloads (`GetComponents(list)`), `StringBuilder`
  or cached strings for UI (update only when values change), `TryGetComponent`, `CompareTag`, struct events,
  non-alloc physics (`Physics.RaycastNonAlloc`, `OverlapSphereNonAlloc`, `Physics.RaycastCommand` for batches).
- Cache `WaitForSeconds`; pool objects (`UnityEngine.Pool`); avoid `Instantiate`/`Destroy` in gameplay.
- Incremental GC (Player Settings) spreads collection cost across frames; it does not remove allocation cost.
- Update loops: do not run per-object `Update` for thousands of simple entities; use one manager iterating
  arrays/structs, Jobs + Burst, or DOTS if scale truly demands it (large investment; justify with data).

## Rendering

- SRP Batcher (URP/HDRP): reduces cost of many materials sharing a shader; requires SRP-compatible shaders
  (properties inside `UnityPerMaterial` CBUFFER) and no per-object MaterialPropertyBlock use. Check the shader
  inspector for "SRP Batcher compatible". Built-in pipeline: use static batching, dynamic batching sparingly,
  GPU instancing.
- GPU instancing / `Graphics.RenderMeshInstanced` / `BatchRendererGroup` for many identical meshes; Static Batching
  for static scenery (costs memory); texture atlases or sprite atlases for 2D.
- LOD: `LODGroup` with 3 levels plus culling; imposters/billboards for distant foliage; check mesh import
  settings (compression, read/write off).
- Culling: occlusion culling for indoor/dense scenes (bake), camera far plane, per-layer cull distances.
- Lighting: bake static lights (lightmaps, Adaptive Probe Volumes where available), limit real-time shadow
  casters and shadow distance, avoid many per-pixel realtime lights on mobile.
- Overdraw: transparent/particle layers, large UI overlays; use Rendering Debugger.
- Textures: correct compression per platform, mipmaps for 3D, power-of-two not required but sizes should be
  block-aligned for compression; limit resolution to what the screen needs; disable Read/Write.
- UI: split canvases (static vs dynamic), avoid rebuilding large layouts each frame, disable raycast target on
  non-interactive graphics, no `GetComponent` in UI update.
- Mobile: lower target frame rate deliberately (`Application.targetFrameRate`), watch thermal throttling and memory.

## Physics

- Name layers, then set the Layer Collision Matrix (Project Settings > Physics / Physics 2D) so unrelated layers
  never test against each other. Query with serialized `LayerMask` fields.
- Prefer primitive colliders; mesh colliders only for static geometry (convex when on Rigidbody).
- Static colliders must not be moved; moving colliders need a Rigidbody (kinematic if script-driven).
- Raise `Time.fixedDeltaTime` only with a measured need (changes feel and cost); set Rigidbody Interpolation for
  followed objects; use Continuous collision detection for fast small objects.
- Triggers for overlap events; non-alloc queries for polling; avoid per-frame `OverlapSphere` on many agents (stagger).

## Build

- Unity 6: **Build Profiles** (File > Build Profiles) hold per-platform scene lists, scripting defines and settings;
  2022 LTS: Build Settings window. Add every scene, bootstrap scene first.
- Scripting backend: IL2CPP for release on iOS/consoles/WebGL (required on some), Mono for iteration. Strip
  engine code carefully; add `link.xml` / `[Preserve]` for reflection-used types.
- Development Build + Autoconnect Profiler for profiling; Release for shipping. Test the player build, not only
  the editor (file paths, `persistentDataPath`, shader variants, input devices, resolution, stripped code).
- Compression and size: Addressables for on-demand content, texture compression per platform, audio load types
  (Streaming for music), strip unused packages. Use the Build Report / Editor.log to find large assets.
- Platform setup (Android SDK/NDK/JDK, iOS signing, WebGL templates and memory) changes with versions; follow the
  manual for the installed editor. WebGL: no threads by default, needs user gesture for audio, memory limits.
- Versioning: set `PlayerSettings.bundleVersion` and build numbers from CI, not by hand.

## Unity Test Framework

Package `com.unity.test-framework` (Window > General > Test Runner).

- **EditMode** tests: fast, no Play mode; test plain C# logic, SO validation, editor tools.
- **PlayMode** tests: run in Play mode; use `[UnityTest]` coroutines (`IEnumerator`, `yield return null`) for
  frame-dependent behavior; load a minimal test scene or build objects in code.
- Put tests in dedicated asmdefs (Create > Testing > Test Assembly Folder), referencing your runtime asmdef;
  they reference `nunit.framework` and are excluded from player builds.

```csharp
using NUnit.Framework;
using System.Collections;
using UnityEngine;
using UnityEngine.TestTools;

public class HealthTests
{
    [Test] public void Damage_ClampsAtZero()
    {
        var h = new HealthModel(10);
        h.TakeDamage(99);
        Assert.AreEqual(0, h.Current);
    }

    [UnityTest] public IEnumerator Bullet_ReleasesAfterLifetime()
    {
        var go = new GameObject("test"); var timer = go.AddComponent<LifetimeTimer>();
        timer.Seconds = 0.1f;
        yield return new WaitForSeconds(0.2f);
        Assert.IsTrue(timer == null || !timer.isActiveAndEnabled);   // Unity null semantics
    }
}
```

Tips: keep logic in plain classes so most tests are EditMode; avoid real-time waits where you can drive logic with
explicit ticks; use `LogAssert.Expect` for expected errors; mock via interfaces.

## CI via batchmode

```bash
# run tests (do not add -quit; the test runner exits itself)
"$UNITY" -batchmode -nographics -projectPath . \
  -runTests -testPlatform EditMode -testResults results-editmode.xml -logFile -
"$UNITY" -batchmode -nographics -projectPath . \
  -runTests -testPlatform PlayMode -testResults results-playmode.xml -logFile -

# build via a static editor method
"$UNITY" -batchmode -nographics -projectPath . -quit \
  -buildTarget StandaloneWindows64 -executeMethod BuildScript.Build -logFile -
```

```csharp
// Assets/_Project/Scripts/Editor/BuildScript.cs  (Editor asmdef)
using UnityEditor; using UnityEditor.Build.Reporting;
public static class BuildScript
{
    public static void Build()
    {
        var opts = new BuildPlayerOptions {
            scenes = System.Array.ConvertAll(EditorBuildSettings.scenes, s => s.path),
            locationPathName = "Builds/Win64/Game.exe",
            target = BuildTarget.StandaloneWindows64,
            options = BuildOptions.None };
        BuildReport r = BuildPipeline.BuildPlayer(opts);
        if (r.summary.result != BuildResult.Succeeded) EditorApplication.Exit(1);
    }
}
```

- Exit codes: test failures give a non-zero code; check your Unity version's docs for the exact values.
- Licensing: batchmode needs an activated license (Personal/Pro serial or a licensing service); handle via CI secrets.
- **game-ci** (`game-ci/unity-test-runner`, `game-ci/unity-builder` GitHub Actions, or the `unityci/editor` Docker
  images) wrap this: set `unityVersion` (match `ProjectVersion.txt`), `targetPlatform`, cache `Library/`, and pass
  license secrets. Check their docs for current inputs and the license activation flow.
- Cache `Library/` between runs to avoid full reimports; fail the job on compile errors in the log
  (`error CS`); upload build output and test XML as artifacts; never commit signing keys.
- Android/iOS/console CI needs extra SDKs and signing; mark as **NOT ASSESSED** if you did not run them.
