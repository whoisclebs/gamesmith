# Networking and security

The server is the only authority. Every value arriving from a client is hostile until proven otherwise.
The `player` argument the engine passes to `OnServerEvent` / `OnServerInvoke` is the only trustworthy
identity; never accept a player, UserId or name argument as "who I am".

## Pick the channel

| Need | Use | Notes |
| --- | --- | --- |
| Client asks the server to do something (buy, attack, interact) | `RemoteEvent:FireServer` | Server validates, acts, optionally replies with `FireClient`. |
| Server tells one / all clients something happened | `RemoteEvent:FireClient` / `FireAllClients` | Clients only render; they decide nothing. |
| High-frequency, losable cosmetic data (aim direction, VFX hints) | `UnreliableRemoteEvent` | May drop or arrive out of order. Small payload cap (about 1 KB; check current docs). Never for state that must arrive. |
| Client needs a value back (catalog page, quote) | `RemoteFunction:InvokeServer` | Keep the server handler fast; client wraps the call in `pcall`. |
| Server needs a value from a client | Never `InvokeClient` | A client can yield forever or error, hanging the server thread. Use a RemoteEvent request plus a reply event with a timeout. |
| Persistent replicated state (round phase, health, team, owned plot) | Attributes on instances, `leaderstats`, ValueObjects | Late joiners get it automatically. Read with `GetAttribute`, react with `GetAttributeChangedSignal`. |
| Server module to server module | Direct function calls or a Signal module | BindableEvents only when decoupling across scripts. |
| Across servers | MessagingService / MemoryStore | See `data.md`. |

Client-side writes to attributes or properties of server-owned instances do not replicate. Exception:
the client owns physics of its own character (network ownership), so position is client-reported data
and must be sanity-checked, not trusted.

## Validation checklist (every argument, every handler)

- **Type**: `typeof(x)` (knows Roblox types like `Vector3` and `Instance`), not `type(x)`.
- **Numbers**: reject NaN (`x ~= x`), `math.huge` / `-math.huge`, out of range; require integers for
  counts, indices and slots. NaN passes naive `<`/`>` checks because every comparison with NaN is false.
- **Strings**: cap byte length with `#s` first, then require valid UTF-8 (`utf8.len(s) ~= nil`), then
  allow-list ids via a lookup table. Never pass client text to `loadstring` or use it as a DataStore key.
- **Tables**: avoid them in remote signatures. If needed, check type, cap element count, validate each
  field; metatables are stripped and non-string keys can be mangled in transit.
- **Instances**: `typeof(x) == "Instance"`, `x:IsA("Class")`, `x:IsDescendantOf(expectedContainer)`, and
  ownership (this plot belongs to this player). Client-only instances arrive as `nil`.
- **Spatial**: distance from the character, line of sight via server raycast, speed between updates.
- **State**: alive, cooldown elapsed, has the item, round phase allows it, enough currency on the server.
- **Rate**: per-player limiter on every remote (see below). Cheap checks first, expensive ones last.

## Server-authoritative values

Prices, damage, rewards and stats are looked up by id in server config. The client copy of
`Shared/Config/Items` exists only for display; the server reads its own copy and ignores client numbers.

```luau
--!strict
-- src/server/Services/ShopService.luau -> ServerScriptService.Server.Services.ShopService
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Remotes = require(ReplicatedStorage.Shared.Remotes)
local Items = require(ReplicatedStorage.Shared.Config.Items) -- { [string]: { price: number } }
local Guard = require(script.Parent.Parent.Lib.RemoteGuard)
local DataService = require(script.Parent.DataService)

local ShopService = {}

function ShopService.start()
	local allow = Guard.limiter(5, 2)
	Guard.onServerEvent(Remotes.RequestBuy, allow, function(player, rawItemId)
		local itemId = Guard.oneOf(rawItemId, Items)
		if not itemId then
			return -- impossible input: drop silently
		end
		local profile = DataService.get(player)
		if not profile then
			return
		end
		local data = profile.Data
		local price = Items[itemId].price
		if data.coins < price or table.find(data.inventory, itemId) then
			Remotes.Notify:FireClient(player, "CannotBuy") -- honest failure: tell the player
			return
		end
		data.coins -= price
		table.insert(data.inventory, itemId)
		Remotes.Notify:FireClient(player, "Bought", itemId)
	end)
end

return ShopService
```

## Rate limiting

Token bucket per player, state cleared on `PlayerRemoving`. The ready-made version is
`assets/remote-guard.luau` (`Guard.limiter`). Pick capacity and refill per remote from real usage
(a click action needs far less than an aim stream). Engine throttles exist but are not your defence.

## Typed remote registry

One module owns every remote name so typos fail loudly and both realms share the contract.

```luau
--!strict
-- src/shared/Remotes.luau -> ReplicatedStorage.Shared.Remotes
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local EVENTS = { "RequestBuy", "Notify" }
local UNRELIABLE = { "AimHint" }
local FUNCTIONS = { "GetCatalog" }

local folder: Instance
if RunService:IsServer() then
	folder = Instance.new("Folder")
	folder.Name = "Remotes"
	local function make(className: string, names: { string })
		for _, name in names do
			local remote = Instance.new(className)
			remote.Name = name
			remote.Parent = folder
		end
	end
	make("RemoteEvent", EVENTS)
	make("UnreliableRemoteEvent", UNRELIABLE)
	make("RemoteFunction", FUNCTIONS)
	folder.Parent = ReplicatedStorage
else
	folder = ReplicatedStorage:WaitForChild("Remotes")
end

return {
	RequestBuy = folder:WaitForChild("RequestBuy") :: RemoteEvent,
	Notify = folder:WaitForChild("Notify") :: RemoteEvent,
	AimHint = folder:WaitForChild("AimHint") :: UnreliableRemoteEvent,
	GetCatalog = folder:WaitForChild("GetCatalog") :: RemoteFunction,
}
```

Require it from the server entry before any client could need it. Document each remote next to its
name: direction, arguments, validation, limiter.

## Silent mitigation

- Impossible input (wrong type, NaN, unknown id, foreign instance): drop it, log a counter server-side,
  reveal nothing to the sender.
- Honest failure (not enough coins, on cooldown): tell the player so the UI stays truthful.
- Movement and hit checks need tolerance for latency. Correct (snap back, ignore hit) before punishing.
- Kick only on repeated, physically impossible behaviour. Do not auto-ban on a single heuristic.
- Weapons: client sends origin, direction and target; server checks fire rate, distance, raycast line of
  sight and target state, then applies damage it computed itself.

## Text from players

Any player text displayed to other players (pet names, signs, custom messages) must be filtered.
Show nothing if filtering fails.

```luau
local TextService = game:GetService("TextService")

local function filterForEveryone(text: string, fromUserId: number): string?
	local ok, result = pcall(function()
		return TextService:FilterStringAsync(text, fromUserId):GetNonChatStringForBroadcastAsync()
	end)
	return if ok then result else nil
end
```

Chat itself goes through `TextChatService`, which filters for you.

## Secrets

- Never put API keys or webhook URLs in scripts, attributes or replicated containers.
- Store them in the experience's secrets store in Creator Hub and read them on the server with
  `HttpService:GetSecret(name)`. It returns a `Secret` object usable in request headers, not a plain string.
- `HttpService.HttpEnabled` must be on; HTTP is server-only.

```luau
local HttpService = game:GetService("HttpService")

local function postScore(score: number): boolean
	local ok = pcall(function()
		local key = HttpService:GetSecret("scores_api_key")
		HttpService:RequestAsync({
			Url = "https://api.example.com/scores",
			Method = "POST",
			Headers = { ["Content-Type"] = "application/json", Authorization = key:AddPrefix("Bearer ") },
			Body = HttpService:JSONEncode({ score = score }),
		})
	end)
	return ok
end
```

## Review questions for any networked feature

1. What happens if a client fires this remote 1000 times per second with random arguments?
2. Can a client pass another player's instance, plot or id and act on it?
3. Is any number the server uses for rewards or prices coming from the client?
4. Does a yield in the handler let the player leave or the state change before the write?
