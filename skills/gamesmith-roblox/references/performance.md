# Performance

Most Roblox players are on phones. Design for the weakest device you intend to support, measure on it,
and only optimise what a profiler shows. Frame-time, memory and bandwidth budgets depend on the target
devices: if they have not been measured, report them as **NOT ASSESSED** instead of guessing.

## Measure first

| Tool | Opens with | Tells you |
| --- | --- | --- |
| Developer Console | F9 in game, or `/console` in chat | Client and server logs, memory by category, script activity, network, server stats |
| MicroProfiler | Ctrl+F6, or the console's MicroProfiler tab | Per-frame timeline of engine and script work; spikes and long frames |
| Script Profiler | Studio, View tab | CPU time per function on client or server |
| Luau heap snapshots | Developer Console memory tools | What Luau objects are alive; compare two snapshots to find leaks |
| Device Emulator | Studio, Test tab | Screen sizes and touch layout (not real device speed) |
| A real low-end phone | Publish to a private test | Ground truth for frame rate, heat and memory |

Label your own hot code so it shows in the MicroProfiler:

```luau
debug.profilebegin("NpcUpdate")
updateAllNpcs(dt)
debug.profileend()
```

## Leaks: the usual suspects

- Connections never disconnected (to `RunService`, `Players`, long-lived instances).
- Tables keyed by `Player`, character or instance that are never cleared.
- Threads looping forever after their owner is gone; keep the thread and `task.cancel` it.
- Instances removed with `Parent = nil` but still referenced. `Destroy()` disconnects their connections.
- Player and character objects lingering after leave: check the Workspace
  `PlayerCharacterDestroyBehavior` setting (current docs) so they are destroyed automatically.

```luau
local connectionsByPlayer: { [Player]: { RBXScriptConnection } } = {}

Players.PlayerRemoving:Connect(function(player)
	for _, connection in connectionsByPlayer[player] or {} do
		connection:Disconnect()
	end
	connectionsByPlayer[player] = nil
end)
```

A cleanup helper library (Trove, Janitor, Maid) is fine if the project already uses one.

## Event-driven over polling

- React to `GetAttributeChangedSignal`, `GetPropertyChangedSignal`, `ChildAdded`, CollectionService
  `GetInstanceAddedSignal`/`GetInstanceRemovedSignal` instead of `while true do task.wait() end` checks.
- One `Heartbeat` connection that updates a list of objects beats one connection per object.
- Use the `dt` argument; never assume a fixed frame rate.

```luau
--!strict
-- Client: spin every part tagged "Spinner" from a single connection.
local CollectionService = game:GetService("CollectionService")
local RunService = game:GetService("RunService")

local spinners: { [BasePart]: true } = {}

local function track(instance: Instance)
	if instance:IsA("BasePart") then
		spinners[instance] = true
	end
end

CollectionService:GetInstanceAddedSignal("Spinner"):Connect(track)
CollectionService:GetInstanceRemovedSignal("Spinner"):Connect(function(instance)
	spinners[instance :: BasePart] = nil
end)
for _, instance in CollectionService:GetTagged("Spinner") do
	track(instance)
end

RunService.Heartbeat:Connect(function(dt: number)
	local step = CFrame.Angles(0, math.rad(90) * dt, 0)
	for part in spinners do
		part.CFrame *= step
	end
end)
```

For many moving anchored parts, batch writes with `workspace:BulkMoveTo(parts, cframes)`.

## Staggering expensive work

Spread updates across frames instead of doing everything every frame.

```luau
local BATCH = 10
local cursor = 0

RunService.Heartbeat:Connect(function()
	local count = #npcs
	if count == 0 then
		return
	end
	for _ = 1, math.min(BATCH, count) do
		cursor = cursor % count + 1
		updateNpc(npcs[cursor])
	end
end)
```

Distant NPCs can update less often than near ones; idle ones not at all.

## Hot-path habits

- Cache `RaycastParams`, `OverlapParams` and `TweenInfo` instead of creating them per call.
- Cache service and instance lookups outside loops; avoid `FindFirstChild` chains every frame.
- Prefer `Vector3`/`CFrame` math over creating temporary parts for queries.
- `--!native` (file) or `@native` (function) compiles Luau to native code. It helps CPU-heavy typed math
  loops; it does little for code dominated by engine API calls. Measure before and after.
- Parallel Luau (Actors with `task.desynchronize`) helps embarrassingly parallel work; only engine APIs
  marked safe can run in parallel.

```luau
local groundParams = RaycastParams.new()
groundParams.FilterType = Enum.RaycastFilterType.Exclude
groundParams.FilterDescendantsInstances = { workspace:WaitForChild("Effects") }

local DOWN = Vector3.new(0, -50, 0)

local function groundBelow(position: Vector3): RaycastResult?
	return workspace:Raycast(position, DOWN, groundParams)
end
```

## Streaming

- `Workspace.StreamingEnabled` is on by default in new places. The client only has nearby parts.
- Client code must never assume a world part exists: use tags plus added signals, or `WaitForChild` with a
  timeout and a nil path.
- `Model.ModelStreamingMode`: `Atomic` streams a model as a whole, `Persistent` keeps it always loaded
  (use sparingly: spawn areas, key landmarks).
- Before teleporting a character far away, call `player:RequestStreamAroundAsync(position)` on the server.
- Tune `StreamingTargetRadius` / `StreamingMinRadius` from measurements, not guesses.
- The server sees everything; server code is unaffected.

## World and rendering

- Anchor everything that never moves. Turn off `CanCollide`, `CanTouch` and `CanQuery` on decoration.
- `CollisionFidelity`: `Box` or `Hull` for most meshes; `PreciseConvexDecomposition` only where precise
  collision matters to gameplay.
- Fewer, larger meshes beat thousands of small parts. Merge static detail in the modelling tool
  (see **gamesmith-blender**) and reuse the same mesh and texture ids so the engine can instance them.
- `Model.LevelOfDetail = StreamingMesh` gives far models cheap stand-ins; `RenderFidelity = Automatic` on meshes.
- Size textures for phones; limit overlapping transparency, shadow-casting lights and particle rates.
- Humanoids are expensive. For NPCs, disable unused states with `Humanoid:SetStateEnabled`, or use an
  `AnimationController` rig when the NPC does not need Humanoid movement.

## Network

- Visual effects run on clients. The server sends one event or sets one attribute; each client spawns
  particles, sounds and tweens locally.
- Do not tween or animate replicated properties on the server every frame; it floods replication.
- Use `UnreliableRemoteEvent` for transient high-rate cosmetic hints.
- Watch the Network tab in the Developer Console while the feature runs with several clients.

## Performance report template

1. Target devices and what was measured on each (or **NOT ASSESSED**).
2. Top costs from MicroProfiler / Script Profiler, with the fix for each.
3. Memory trend over a long session (stable or growing).
4. What was not tested (real device, high player count).
