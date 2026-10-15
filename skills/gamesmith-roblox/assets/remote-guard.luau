--!strict
-- RemoteGuard: validate untrusted remote arguments and rate-limit players.
-- Place on the server, e.g. src/server/Lib/RemoteGuard.luau -> ServerScriptService.Server.Lib.RemoteGuard
--
-- Usage:
--   local allow = Guard.limiter(5, 2) -- burst of 5, refills 2 tokens per second
--   Guard.onServerEvent(Remotes.RequestBuy, allow, function(player, itemId)
--       local id = Guard.oneOf(itemId, Items)
--       if not id then return end -- drop silently
--       ...
--   end)

local Players = game:GetService("Players")

local Guard = {}

local function isFinite(n: number): boolean
	return n == n and n ~= math.huge and n ~= -math.huge
end
Guard.isFinite = isFinite

-- Number in [min, max]; rejects NaN and infinities.
function Guard.number(value: unknown, min: number, max: number): number?
	if typeof(value) ~= "number" then
		return nil
	end
	local n = value :: number
	if not isFinite(n) or n < min or n > max then
		return nil
	end
	return n
end

-- Whole number in [min, max].
function Guard.integer(value: unknown, min: number, max: number): number?
	local n = Guard.number(value, min, max)
	if n == nil or math.floor(n) ~= n then
		return nil
	end
	return n
end

-- Valid UTF-8 string, at most maxBytes long (checked before any decoding work).
function Guard.str(value: unknown, maxBytes: number): string?
	if typeof(value) ~= "string" then
		return nil
	end
	local s = value :: string
	if #s > maxBytes or utf8.len(s) == nil then
		return nil
	end
	return s
end

-- String that is a key of an allow-list table (item ids, action names...).
function Guard.oneOf(value: unknown, allowed: { [string]: any }): string?
	if typeof(value) ~= "string" then
		return nil
	end
	local key = value :: string
	if #key > 100 or allowed[key] == nil then
		return nil
	end
	return key
end

function Guard.boolean(value: unknown): boolean?
	if typeof(value) ~= "boolean" then
		return nil
	end
	return value :: boolean
end

-- Vector3 with finite components and bounded magnitude.
function Guard.vector3(value: unknown, maxMagnitude: number): Vector3?
	if typeof(value) ~= "Vector3" then
		return nil
	end
	local v = value :: Vector3
	if not (isFinite(v.X) and isFinite(v.Y) and isFinite(v.Z)) or v.Magnitude > maxMagnitude then
		return nil
	end
	return v
end

-- Instance of className, optionally required to live under ancestor (blocks spoofed references).
function Guard.instance(value: unknown, className: string, ancestor: Instance?): Instance?
	if typeof(value) ~= "Instance" then
		return nil
	end
	local inst = value :: Instance
	if not inst:IsA(className) then
		return nil
	end
	if ancestor and not inst:IsDescendantOf(ancestor) then
		return nil
	end
	return inst
end

type Bucket = { tokens: number, last: number }

-- Per-player token bucket. Returns allow(player) -> boolean. State is dropped on PlayerRemoving.
function Guard.limiter(capacity: number, refillPerSecond: number): (Player) -> boolean
	local buckets: { [Player]: Bucket } = {}
	Players.PlayerRemoving:Connect(function(player: Player)
		buckets[player] = nil
	end)

	return function(player: Player): boolean
		local now = os.clock()
		local bucket = buckets[player]
		if bucket == nil then
			if player.Parent ~= Players then
				return false -- already leaving; do not recreate state
			end
			bucket = { tokens = capacity, last = now }
			buckets[player] = bucket
		end
		bucket.tokens = math.min(capacity, bucket.tokens + (now - bucket.last) * refillPerSecond)
		bucket.last = now
		if bucket.tokens < 1 then
			return false
		end
		bucket.tokens -= 1
		return true
	end
end

-- Connects a handler that only runs when the limiter allows it. Errors are logged server-side,
-- never echoed to the client (silent mitigation).
function Guard.onServerEvent(
	remote: RemoteEvent | UnreliableRemoteEvent,
	allow: (Player) -> boolean,
	handler: (Player, ...unknown) -> ()
): RBXScriptConnection
	return remote.OnServerEvent:Connect(function(player: Player, ...: unknown)
		if not allow(player) then
			return
		end
		local ok, err = pcall(handler, player, ...)
		if not ok then
			warn(`[RemoteGuard] {remote.Name} from {player.UserId}: {err}`)
		end
	end)
end

return Guard
