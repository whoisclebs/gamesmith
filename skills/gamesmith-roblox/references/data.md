# Player data and persistence

Data loss is unforgivable. Quotas, size limits and shutdown windows change: check current docs before tuning.

## Rules

- **Key per player**: `player_<UserId>`. UserIds never change; names do.
- **Session lock**: only one server may own a player's data at a time, or two servers overwrite each
  other (fast server hops, teleports). Use ProfileStore (loleris, open source; see its docs for current
  install options) for player data. Use raw DataStores only for non-player data or when a library is not allowed.
- **Never overwrite on load failure.** If loading fails, kick with a clear message or keep the player in a
  no-save state. Saving defaults over a profile that failed to load is a data wipe. Hand-rolled saves:
  set `loaded[player] = true` only after a successful read; refuse to save anyone not loaded.
- **UpdateAsync over SetAsync** for any read-modify-write. The transform may run more than once, must be
  pure (no yields, no side effects) and can return `nil` to cancel.
- **Retries and budget**: `pcall` every call, bounded attempts with backoff plus jitter; before bulk work
  wait until `DataStoreService:GetRequestBudgetForRequestType(kind) >= 1`.
- **Save points**: periodic autosave, `PlayerRemoving`, and `game:BindToClose` for every remaining player.
  ProfileStore does all three; with raw DataStores you must.
- **Schema version** in every record plus ordered migrations, run before filling in template defaults.
- **Serializable data only**: numbers, strings, booleans, and tables that are pure arrays or
  string-keyed dictionaries. No Instances, `Vector3`, `CFrame`, `Color3`, EnumItems, NaN/inf, mixed or
  sparse tables. Convert (`{ x = v.X, y = v.Y, z = v.Z }`, enum `.Name`, item ids).
- **Studio**: "Enable Studio Access to API Services" (Game Settings → Security) is needed for DataStores.
  Studio writes hit the real experience data; use a separate store name or a test place.
- **Privacy**: attach the UserId to the key metadata (`AddUserId` in ProfileStore, the `userIds`
  argument of `SetAsync`/`UpdateAsync` for raw stores) so right-to-erasure requests can be honoured.

## ProfileStore service

API names below match current ProfileStore; confirm against the version you install.

```luau
--!strict
-- src/server/Services/DataService.luau -> ServerScriptService.Server.Services.DataService
local Players = game:GetService("Players")
local ServerStorage = game:GetService("ServerStorage")
local ProfileStore = require(ServerStorage.ServerPackages.ProfileStore)

local TEMPLATE = {
	version = 2,
	coins = 0,
	inventory = {} :: { string },
	purchaseIds = {} :: { string }, -- receipt idempotency, see monetization.md
}
export type Data = typeof(TEMPLATE)

local MIGRATIONS: { [number]: (any) -> () } = { -- [N] upgrades version N to N + 1
	[1] = function(data)
		data.coins, data.gold = data.gold or 0, nil
	end,
}

local store = ProfileStore.New("PlayerData", TEMPLATE)
local profiles: { [Player]: any } = {}

local DataService = {}
local function migrate(data: any)
	data.version = data.version or 1
	while MIGRATIONS[data.version] do
		MIGRATIONS[data.version](data)
		data.version += 1
	end
end

local function onPlayerAdded(player: Player)
	local profile = store:StartSessionAsync(`player_{player.UserId}`, {
		Cancel = function()
			return player.Parent ~= Players
		end,
	})
	if profile == nil then
		player:Kick("Your data could not be loaded. Please rejoin.")
		return
	end
	profile:AddUserId(player.UserId)
	migrate(profile.Data) -- before Reconcile, or old records get the new version number unmigrated
	profile:Reconcile()
	profile.OnSessionEnd:Connect(function()
		profiles[player] = nil
		player:Kick("Your data was opened on another server. Please rejoin.")
	end)
	if player.Parent == Players then
		profiles[player] = profile
	else
		profile:EndSession()
	end
end

function DataService.get(player: Player): any
	return profiles[player]
end

-- Requests saves until a completed save satisfies isSaved(profile.LastSavedData). Checking the
-- saved copy (not "some save finished") matters: a save already in flight may predate your change.
function DataService.saveNow(player: Player, isSaved: (savedData: any) -> boolean, timeout: number?): boolean
	local profile = profiles[player]
	if not profile then
		return false
	end
	local deadline = os.clock() + (timeout or 15)
	local nextRequest = 0
	while profile:IsActive() and os.clock() < deadline do
		if isSaved(profile.LastSavedData) then
			return true
		end
		if os.clock() >= nextRequest then
			profile:Save() -- does not yield; one UpdateAsync per call
			nextRequest = os.clock() + 5
		end
		task.wait(0.1)
	end
	return false
end

function DataService.start()
	Players.PlayerAdded:Connect(onPlayerAdded)
	for _, player in Players:GetPlayers() do
		task.spawn(onPlayerAdded, player)
	end
	Players.PlayerRemoving:Connect(function(player)
		local profile = profiles[player]
		if profile then
			profile:EndSession()
		end
	end)
end

return DataService
```

Other services touch `DataService.get(player).Data` only after a nil check; mirror display values via attributes.

## Raw DataStore helpers

```luau
local DataStoreService = game:GetService("DataStoreService")

local function withRetry(attempts: number, fn: () -> any): (boolean, any)
	local ok: boolean, result: any = false, nil
	for attempt = 1, attempts do
		ok, result = pcall(fn)
		if ok or attempt == attempts then
			break
		end
		task.wait(2 ^ attempt + math.random()) -- backoff plus jitter
	end
	return ok, result
end

local globalStats = DataStoreService:GetDataStore("GlobalStats")

local function addVisit(): (boolean, any)
	return withRetry(4, function()
		return globalStats:UpdateAsync("visits", function(old: number?)
			return (old or 0) + 1
		end)
	end)
end
```

Raw `BindToClose`: save all players in parallel (`task.spawn` each) and wait for them within the window.

## Leaderboards: OrderedDataStore

```luau
local winsBoard = DataStoreService:GetOrderedDataStore("Wins")
-- Values must be integers. Write on save, not on every change.
pcall(winsBoard.SetAsync, winsBoard, tostring(player.UserId), wins)
-- Read the top 50 on a timer (minutes), cache it, serve the cache to clients.
local ok, pages = pcall(winsBoard.GetSortedAsync, winsBoard, false, 50)
if ok then
	for rank, entry in pages:GetCurrentPage() do
		print(rank, entry.key, entry.value)
	end
end
```

Resolve names with `Players:GetNameFromUserIdAsync` (in `pcall`, cached).

## Cross-server: MemoryStore and MessagingService

- **MemoryStore**: fast, shared, temporary. Matchmaking queues, live leaderboards, short locks. Every
  write needs an expiration; treat contents as disposable. Quota scales with player count (check docs).
  Queues: `GetQueue`, `AddAsync`, `ReadAsync`, then `RemoveAsync` with the returned id once processed.
- **MessagingService**: best effort, small messages, no delivery or ordering guarantee. Use for nudges
  ("refresh shop", announcements), never as a source of truth; follow up with a store read.

```luau
local MemoryStoreService = game:GetService("MemoryStoreService")
local MessagingService = game:GetService("MessagingService")

local liveScores = MemoryStoreService:GetSortedMap("LiveScores")
pcall(liveScores.SetAsync, liveScores, tostring(player.UserId), score, 300) -- expires in 300 s
pcall(MessagingService.SubscribeAsync, MessagingService, "Announcements", function(message) print(message.Data) end)
pcall(MessagingService.PublishAsync, MessagingService, "Announcements", "Double coins weekend!")
```

## Test plan for data changes

Rejoin after changing data (persists). Leave and rejoin instantly or hop servers (no rollback). Shut
down the server mid-session (`BindToClose` saved). Load a seeded old-format record (migrated, version
bumped). Stub a load failure (player kicked, nothing saved).
