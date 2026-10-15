---
name: gamesmith-roblox
description: Builds Roblox experiences in Luau with server-authoritative networking, session-locked player data, safe monetization, Rojo/Wally tooling, mobile-first performance and Roblox Studio MCP workflows. Use when the user is making or fixing a Roblox game, writing Luau scripts, wiring RemoteEvents, saving player data, selling game passes or developer products, setting up Rojo, or driving Roblox Studio from an agent.
license: MIT
metadata:
  pack: gamesmith
  engine: roblox
---

# Gamesmith Roblox

Ship Roblox features that are secure by default, testable in Studio and organized as modules.

Defer to sibling skills:

- **gamesmith**: GDD, core loop, prototyping, game feel, balancing, playtesting process.
- **gamesmith-blender**: modeling, UVs, rigs, export of meshes and animations. Import results with
  Studio's 3D Importer; this skill covers what happens after import (collision, LOD, streaming).

## Step 1: detect the project mode (before writing anything)

Inspect the working tree first. Never generate files blind.

| Signal | Mode | Where edits go |
| --- | --- | --- |
| `default.project.json` (or `*.project.json`) plus `src/` | Rojo, file-based | Files on disk. Studio is a sync target; never edit synced scripts inside Studio (the next sync overwrites them). |
| No project file; only a `.rbxl`/`.rbxlx` or a live Studio session | Studio-only | Through Studio MCP if available, otherwise paste-ready scripts with exact Explorer paths. |
| Project file maps only part of the tree, or Studio Script Sync folders exist | Hybrid | Code on disk, map/UI/instances in the place. Confirm which side owns each subtree. |

Checklist:

1. List the tree: project file, `rokit.toml` / `aftman.toml` / `foreman.toml`, `wally.toml`, `wally.lock`,
   `selene.toml`, `stylua.toml`, `.luaurc`, `src/` layout, tests.
2. Read the project file and map every `$path` to its DataModel location.
3. Check whether Roblox Studio MCP tools are available in this session. If yes, read
   `references/studio-mcp.md` before calling any of them.
4. Read the existing modules the feature touches. Match their conventions (framework such as Knit,
   networking library, naming, folder layout) instead of introducing a parallel style.
5. If the mode is ambiguous or two sources could both own a script, ask the user.

## Core rules

1. **The client is attacker-controlled.** The client sends intent ("buy item `sword`", "activate
   prompt"); the server checks state and decides the outcome. Never accept prices, damage, currency,
   cooldowns, ownership or a "who I am" id from the client. Read `references/networking-security.md`.
2. **Anything replicated is readable.** ModuleScripts in ReplicatedStorage, attributes and values can be
   dumped by exploiters. Server-only logic, tuning that grants rewards, and secrets live in
   ServerScriptService / ServerStorage.
3. `--!strict` at the top of every new script and module. Type remote arguments as `unknown` and narrow.
4. Use `task.wait`, `task.spawn`, `task.defer`, `task.delay`, `task.cancel`. Never `wait`, `spawn`, `delay`.
5. Get services once at the top: `local Players = game:GetService("Players")`.
6. Construct instances fully, then set `Parent` last.
7. Wrap every yielding web call (DataStore, MarketplaceService, HttpService, TeleportService,
   PolicyService, TextService filtering) in `pcall` and handle failure explicitly.
8. Clean up: disconnect connections you own, clear player-keyed tables on `PlayerRemoving`,
   `task.cancel` long-lived threads, `Destroy` instances you created.
9. Text typed by one player and shown to others must pass `TextService` filtering first.
10. No placeholder security. "TODO: validate" is a bug, not a plan.

### Deprecated or legacy → modern

| Avoid | Use |
| --- | --- |
| `wait()`, `spawn()`, `delay()` | `task.wait()`, `task.spawn()`, `task.delay()` |
| `BodyVelocity`, `BodyPosition`, `BodyGyro`, `BodyForce`, `BodyAngularVelocity` | `LinearVelocity`, `AlignPosition`, `AlignOrientation`, `VectorForce`, `AngularVelocity` (with Attachments) |
| Legacy `Chat` service / Lua chat modules | `TextChatService` |
| `workspace:FindPartOnRay*`, `Ray.new` for queries | `workspace:Raycast(origin, direction, RaycastParams)` |
| `Humanoid:LoadAnimation` | `Animator:LoadAnimation` (Animator under Humanoid/AnimationController) |
| `Model:SetPrimaryPartCFrame` | `Model:PivotTo` / `GetPivot` |
| `Instance.new(class, parent)` | `Instance.new(class)`, set properties, then `Parent` |
| `TeleportService:Teleport` | `TeleportService:TeleportAsync` (server) |
| `game.Players`, `game.Workspace` style lookups | `game:GetService(...)`, `workspace` |
| `Player:GetMouse()` for gameplay input | `ContextActionService` / `UserInputService` |
| `RemoteFunction:InvokeClient` | RemoteEvent request/response (see networking reference) |

## Where code lives

| Container | Runs / visibility | Put here |
| --- | --- | --- |
| ServerScriptService | Server only, never replicated | Server entry Script, server services |
| ServerStorage | Server only, never replicated | Templates, server-only assets, `ServerPackages` |
| ReplicatedStorage | Server and client, replicated | Shared modules, remotes, display config, `Packages` |
| ReplicatedFirst | Client, loads first | Loading screen only |
| StarterPlayer > StarterPlayerScripts | Copied once per player | Client entry LocalScript, client controllers |
| StarterPlayer > StarterCharacterScripts | Re-copied every respawn | Only per-life character logic |
| StarterGui | Copied into PlayerGui | ScreenGuis (`ResetOnSpawn = false` unless per-life) |
| Workspace | World, replicated (subject to streaming) | Map and physical objects; keep scripts out |

`Script.RunContext = Client` runs a Script anywhere, including Workspace. Use it only on purpose.

## Architecture

- **One entry script per realm.** `ServerScriptService/Server` (Script) and
  `StarterPlayerScripts/Client` (LocalScript) require modules in an explicit order. Everything else is a
  ModuleScript.
- Layout (Rojo names in parentheses):
  - `ReplicatedStorage/Shared` (`src/shared`): `Remotes`, `Config/*` (items keyed by id), pure utilities.
  - `ServerScriptService/Server` (`src/server`): `init.server.luau`, `Services/*Service.luau`, `Lib/*`.
  - `StarterPlayerScripts/Client` (`src/client`): `init.client.luau`, `Controllers/*Controller.luau`.
- Each service/controller exposes `start()`; it does setup on require and wiring in `start`.
- No circular requires. If A and B need each other, move the shared piece into a third module.
- Behaviour for many instances: CollectionService tags plus attributes, driven by one module, not one
  script per part.

```luau
--!strict
-- src/server/init.server.luau  ->  ServerScriptService.Server (Script)
local Services = script.Services

require(Services.DataService).start()
require(Services.ShopService).start()
```

Handle players who joined before your `PlayerAdded` connection:

```luau
Players.PlayerAdded:Connect(onPlayerAdded)
for _, player in Players:GetPlayers() do
	task.spawn(onPlayerAdded, player)
end
```

## Workflow

1. Detect the mode (Step 1). Read the reference files that match the feature.
2. Write a remote contract before code: name, direction, argument types, validation, rate limit, reply.
3. Implement server first (state, validation, persistence), then client (input, UI, feedback).
4. Run the project's linters/formatters if configured (`selene`, `stylua --check`, `luau-lsp analyze`).
5. Playtest through Studio MCP when available; otherwise hand the user the manual test plan.
6. Deliver using the contract below.

## Every deliverable includes

1. **Files table**: disk path (if Rojo) and DataModel path, realm (Server / Client / Shared), class
   (Script / LocalScript / ModuleScript), new or changed.
2. **Setup steps**: instances, tags, attributes, product/pass IDs to create in Creator Hub, Game
   Settings toggles (for example "Enable Studio Access to API Services" for DataStores in Studio).
3. **Manual test plan in Studio**:
   - Play solo: happy path, Output window clean on server and client.
   - Test tab → Clients and Servers with at least 2 players: replication, late join, one player leaving
     while another acts.
   - Abuse pass: from a client, fire each new remote with wrong types, NaN, huge numbers, long strings,
     foreign instances and spam. Expect silent rejection and no server error.
   - Persistence: change data, leave, rejoin; stop the server mid-session and rejoin.
   - Device Emulator: a small phone, a tablet, and gamepad input.
4. **Likely failure cases** for this feature, for example: `Infinite yield possible` on `WaitForChild`;
   parts missing on the client under StreamingEnabled; DataStore errors because API access is off in
   Studio; wrong product ID; UI vanishing on respawn (`ResetOnSpawn`); character not yet loaded;
   player left during a yield.
5. **Not verified**: say what you could not run or observe.

## Reference index

| File | Read when |
| --- | --- |
| `references/networking-security.md` | Adding or reviewing any RemoteEvent/RemoteFunction, replicated state, anti-exploit, secrets, text filtering. |
| `references/data.md` | Saving player data, leaderboards, cross-server state, migrations, shutdown handling. |
| `references/monetization.md` | Developer products, game passes, receipts, policy-gated features, pricing ethics. |
| `references/tooling.md` | Setting up Rojo, Rokit, Wally, StyLua, Selene, luau-lsp, tests or CI; choosing Script Sync vs Rojo. |
| `references/performance.md` | Lag, memory growth, mobile targets, streaming, many NPCs/parts, profiling. |
| `references/studio-mcp.md` | Studio MCP tools are available, or the user wants the agent to edit or playtest in Studio. |
| `references/ui-and-input.md` | Building ScreenGuis, scaling across devices, input bindings, tweens, ProximityPrompts. |

## Assets

- `assets/remote-guard.luau`: strict-typed argument validators, per-player token-bucket limiter and a
  safe `OnServerEvent` wrapper. Copy into `src/server/Lib/RemoteGuard.luau`.
- `assets/default.project.json`: minimal Rojo layout matching the architecture above.
