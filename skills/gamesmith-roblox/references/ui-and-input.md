# UI and input

UI and input are client-side. They express intent to the server and render server state; they never
decide outcomes.

## Structure

```
StarterGui
  HUD            ScreenGui  ResetOnSpawn=false  ScreenInsets=CoreUISafeInsets
    Currency     Frame (reads player attributes / leaderstats)
  Shop           ScreenGui  Enabled=false       ResetOnSpawn=false
    Window       Frame + UIAspectRatioConstraint + UIScale
StarterPlayerScripts/Client/Controllers
  HudController.luau, ShopController.luau
```

- One ScreenGui per independent screen; toggle `Enabled` to open and close it.
- A controller module owns each screen: binds buttons, listens to server state, plays tweens.
- `ResetOnSpawn = false` unless the UI really belongs to one life.
- Declarative UI libraries (React for Roblox, Fusion, Vide) are fine if the project already uses one;
  do not introduce one for a single screen.
- Text a player typed that others will see is filtered on the server first (see `networking-security.md`).
- Display prices from `MarketplaceService:GetProductInfoAsync` (cached, in `pcall`), never hardcoded.

## Scaling across devices

| Need | Tool |
| --- | --- |
| Layout proportional to screen | `Size`/`Position` with Scale (`UDim2.fromScale`) |
| Fixed padding, borders, icon size | Offset, or `UIPadding` |
| Keep a shape (square button, card) | `UIAspectRatioConstraint` |
| Clamp size on huge or tiny screens | `UISizeConstraint` |
| Scale a whole window | `UIScale` (also ideal for open/close tweens) |
| Readable text | `TextScaled` + `UITextSizeConstraint` (max size), or fixed `TextSize` with `AutomaticSize` |
| Lists and grids | `UIListLayout`, `UIGridLayout`, flex options, `AutomaticSize` on containers |
| Centering | `AnchorPoint = Vector2.new(0.5, 0.5)` with `Position = UDim2.fromScale(0.5, 0.5)` |
| Notches and system bars | `ScreenGui.ScreenInsets` (`CoreUISafeInsets`); do not overlap Roblox's top bar |

Check every screen in the Device Emulator: small phone portrait and landscape, tablet, desktop, and a
console view (text read from across a room). Keep touch targets thumb-sized and away from the default
thumbstick (bottom left) and jump button (bottom right).

## Input: pick the API

| Need | Use |
| --- | --- |
| Gameplay actions with keyboard, gamepad and an optional on-screen touch button | `ContextActionService:BindAction` |
| Raw input, global shortcuts, input-type detection | `UserInputService` |
| Declarative cross-device bindings | Input Action System (`InputContext` / `InputAction` / `InputBinding`); check current docs |
| World interactions ("press E to open") | `ProximityPrompt` |

```luau
--!strict
-- Client: sprint intent. The server decides the actual WalkSpeed.
local ContextActionService = game:GetService("ContextActionService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Remotes = require(ReplicatedStorage.Shared.Remotes) -- add SetSprint to the registry

local function onSprint(_actionName: string, state: Enum.UserInputState, _input: InputObject): Enum.ContextActionResult
	if state == Enum.UserInputState.Begin then
		Remotes.SetSprint:FireServer(true)
	elseif state == Enum.UserInputState.End or state == Enum.UserInputState.Cancel then
		Remotes.SetSprint:FireServer(false)
	end
	return Enum.ContextActionResult.Sink
end

ContextActionService:BindAction("Sprint", onSprint, true, Enum.KeyCode.LeftShift, Enum.KeyCode.ButtonL3)
ContextActionService:SetTitle("Sprint", "Run")
```

```luau
local UserInputService = game:GetService("UserInputService")

UserInputService.InputBegan:Connect(function(input: InputObject, gameProcessed: boolean)
	if gameProcessed then
		return -- typing in chat or clicking UI
	end
	if input.KeyCode == Enum.KeyCode.Tab or input.KeyCode == Enum.KeyCode.ButtonSelect then
		toggleScoreboard()
	end
end)
```

## Device parity checklist

- Every action reachable with mouse+keyboard, touch and gamepad.
- Show glyphs for the active input. Track it with `UserInputService.PreferredInput` where available, or
  `LastInputTypeChanged`; `UserInputService:GetImageForKeyCode` returns gamepad button images.
- Do not infer "phone" from `TouchEnabled` alone (touch laptops exist); adapt to the input in use.
- Gamepad menus: set `GuiService.SelectedObject` when a menu opens, make buttons `Selectable`, tune
  `NextSelection*` where automatic navigation guesses wrong, and let ButtonB close the menu.
- Never require hover; touch has none.

## Tweens

```luau
local TweenService = game:GetService("TweenService")

local POP = TweenInfo.new(0.18, Enum.EasingStyle.Back, Enum.EasingDirection.Out)

local function popIn(window: GuiObject)
	local scale = window:FindFirstChildOfClass("UIScale") or Instance.new("UIScale")
	scale.Parent = window
	scale.Scale = 0.85
	window.Visible = true
	TweenService:Create(scale, POP, { Scale = 1 }):Play()
end
```

- Tween on the client only. Server-side tweens replicate every step.
- Keep UI motion short; respect the reduced-motion setting (`GuiService.ReducedMotionEnabled` where available).
- Juice and feel decisions (timing, easing choices, feedback layering) come from **gamesmith**.

## ProximityPrompt

- Parent to a BasePart or Attachment. Set `ActionText`, `ObjectText`, `HoldDuration`,
  `MaxActivationDistance`, `RequiresLineOfSight`. Keyboard, gamepad and touch work automatically.
- `Triggered` fires on the server with the player. Still validate: cooldown, state, ownership, and
  distance with a little tolerance.

```luau
--!strict
local function promptPosition(prompt: ProximityPrompt): Vector3?
	local parent = prompt.Parent
	if parent and parent:IsA("Attachment") then
		return parent.WorldPosition
	elseif parent and parent:IsA("BasePart") then
		return parent.Position
	end
	return nil
end

prompt.Triggered:Connect(function(player: Player)
	local character = player.Character
	local root = character and character:FindFirstChild("HumanoidRootPart") :: BasePart?
	local target = promptPosition(prompt)
	if not root or not target then
		return
	end
	if (root.Position - target).Magnitude > prompt.MaxActivationDistance + 5 then
		return
	end
	openChest(player) -- server-side: checks cooldown and ownership, then grants
end)
```

- For a custom look set `Style = Custom` and draw it in a client controller via
  `ProximityPromptService.PromptShown` / `PromptHidden`.

## UI test plan

1. Device Emulator: every screen on the smallest phone, both orientations; nothing clipped or overlapped.
2. Gamepad only: open, navigate and close every menu without touching the mouse.
3. Touch only: every action reachable; buttons do not cover thumbstick or jump.
4. Respawn: HUD persists; open menus behave as designed.
5. Server rejects the action (no coins, cooldown): UI shows the honest failure.
