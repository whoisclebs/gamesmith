# Monetization

Robux prices live in Creator Hub. Grants are decided on the server by product or pass id. The client may
prompt a purchase and render prices; it never decides what was bought or what it is worth.

## Pick the product type

| Type | Use for | Ownership / grant |
| --- | --- | --- |
| Game pass | One-time permanent perk (VIP, extra slot, cosmetic set) | `MarketplaceService:UserOwnsGamePassAsync(userId, passId)` on join and after purchase |
| Developer product | Repeatable consumables (currency packs, revives, boosts) | `MarketplaceService.ProcessReceipt` callback, idempotent |
| Subscription | Recurring monthly benefit | Subscription APIs; check current docs and eligibility rules |
| Private server | Paid private instances | Configure in Creator Hub; detect with `game.PrivateServerId` / `PrivateServerOwnerId` |

Show the live price from `MarketplaceService:GetProductInfoAsync(id, Enum.InfoType.Product)` (or
`Enum.InfoType.GamePass`), cached and wrapped in `pcall`, instead of hardcoding it in UI.

## ProcessReceipt: the only place developer products are granted

Requirements:

- Exactly one script sets `MarketplaceService.ProcessReceipt`.
- Return `PurchaseGranted` only after the grant is durably saved. Otherwise return `NotProcessedYet`;
  Roblox redelivers the receipt later (including on the player's next join).
- Idempotent: the same `PurchaseId` can arrive more than once. Record handled ids in the player's
  session-locked data and skip the grant for repeats, but still confirm the id is saved before
  acknowledging (check ProfileStore's `LastSavedData`, not just "a save happened").
- `PromptProductPurchaseFinished` is a UI signal, never a grant signal.

```luau
--!strict
-- src/server/Services/ReceiptService.luau -> ServerScriptService.Server.Services.ReceiptService
local MarketplaceService = game:GetService("MarketplaceService")
local Players = game:GetService("Players")
local DataService = require(script.Parent.DataService)

local MAX_HISTORY = 50 -- recent purchase ids kept for idempotency

-- productId -> grant. Replace ids with your Creator Hub product ids.
local GRANTS: { [number]: (data: DataService.Data) -> () } = {
	[1111111111] = function(data)
		data.coins += 100
	end,
}

local function processReceipt(info: { [string]: any }): Enum.ProductPurchaseDecision
	local player = Players:GetPlayerByUserId(info.PlayerId)
	if not player then
		return Enum.ProductPurchaseDecision.NotProcessedYet -- redelivered when they rejoin
	end
	local profile = DataService.get(player)
	local loadDeadline = os.clock() + 30
	while not profile and player.Parent == Players and os.clock() < loadDeadline do
		task.wait(0.5) -- receipts can arrive before the profile finishes loading
		profile = DataService.get(player)
	end
	if not profile or not profile:IsActive() then
		return Enum.ProductPurchaseDecision.NotProcessedYet
	end

	local purchaseId: string = info.PurchaseId
	local history: { string } = profile.Data.purchaseIds
	if not table.find(history, purchaseId) then
		local grant = GRANTS[info.ProductId]
		if not grant then
			warn(`[Receipt] unknown product {info.ProductId}`)
			return Enum.ProductPurchaseDecision.NotProcessedYet
		end
		grant(profile.Data)
		table.insert(history, purchaseId)
		if #history > MAX_HISTORY then
			table.remove(history, 1)
		end
	end

	-- Acknowledge only once a completed save contains this id. A repeat delivery whose id is
	-- already in memory (earlier save failed or still in flight) also waits here, never short-circuits.
	local saved = DataService.saveNow(player, function(savedData)
		local savedIds = savedData.purchaseIds
		return savedIds ~= nil and table.find(savedIds, purchaseId) ~= nil
	end)
	return if saved
		then Enum.ProductPurchaseDecision.PurchaseGranted
		else Enum.ProductPurchaseDecision.NotProcessedYet
end

local ReceiptService = {}

function ReceiptService.start()
	MarketplaceService.ProcessReceipt = processReceipt
end

return ReceiptService
```

`DataService` is the ProfileStore service from `data.md`. Do not grant into a store that lacks session
locking: a second server could overwrite the grant.

## Game passes

```luau
local MarketplaceService = game:GetService("MarketplaceService")
local Players = game:GetService("Players")

local VIP_PASS_ID = 2222222222 -- your pass id

local function ownsPass(player: Player, passId: number): boolean
	local ok, owns = pcall(MarketplaceService.UserOwnsGamePassAsync, MarketplaceService, player.UserId, passId)
	return ok and owns == true
end

local function applyVip(player: Player)
	player:SetAttribute("VIP", true) -- replicated flag for UI; server logic reads the same attribute
end

Players.PlayerAdded:Connect(function(player)
	if ownsPass(player, VIP_PASS_ID) then
		applyVip(player)
	end
end)

-- Fires on the server too; grants mid-session without a rejoin.
MarketplaceService.PromptGamePassPurchaseFinished:Connect(function(player, passId, purchased)
	if purchased and passId == VIP_PASS_ID then
		applyVip(player)
	end
end)
```

If the ownership check errors, treat the pass as not owned for now and retry later; never persist
"not owned". Pass benefits are derived at runtime, not saved as currency.

## Prompting from the client

```luau
-- LocalScript: intent only. The server grants through ProcessReceipt / ownership checks.
MarketplaceService:PromptProductPurchase(Players.LocalPlayer, PRODUCT_ID)
MarketplaceService:PromptGamePassPurchase(Players.LocalPlayer, PASS_ID)
```

## Policy-gated features

Some features are restricted by region or age. Query `PolicyService` on the server and default to the
most restrictive answer when the call fails.

```luau
local PolicyService = game:GetService("PolicyService")

local function canOfferPaidRandomItems(player: Player): boolean
	local ok, policy = pcall(PolicyService.GetPolicyInfoForPlayerAsync, PolicyService, player)
	return ok and policy.ArePaidRandomItemsRestricted == false
end
```

Other fields cover paid item trading, allowed external link references and more; read current docs for the
full list. Hide the restricted UI entirely rather than showing a disabled button.

## Ethical design and platform rules

- Paid random items (loot boxes, gacha) must disclose odds and are blocked where policy says so.
- No purchases that can only be understood after paying; show exactly what the player gets.
- No manufactured pressure aimed at children: fake scarcity, countdowns that reset, guilt prompts,
  "pay or lose your progress" flows.
- Keep competitive modes fair. Sell convenience and cosmetics before raw power.
- No links or instructions for buying outside Roblox; no Robux-for-real-value trading schemes.
- Keep the free path complete and fun. Balance and economy tuning belongs to **gamesmith**.
- Check the current Roblox monetization policy and Community Standards before launch; they change.

## Test plan

1. Studio test purchases are simulated (no Robux charged). Buy each product; verify grant and save.
2. Buy twice quickly: two grants, two distinct ids, no duplicate.
3. Temporarily make `saveNow` return `false`: purchase is not acknowledged and is redelivered.
4. Leave right after buying: grant appears on rejoin, exactly once.
5. Pass: buy mid-session, perk applies immediately; rejoin, perk still applied.
6. Restricted-policy path: force `canOfferPaidRandomItems` false, UI hides the offer.
