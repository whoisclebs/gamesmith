# Game Feel

Game feel is how the game answers the player's hands. Fix responsiveness first, then add
feedback, then add flourish. Never let flourish hide information.

## Order of work

1. **Responsiveness**: input reaches gameplay fast and reliably.
2. **Forgiveness**: the game reads intent, not frame-perfect timing.
3. **Feedback**: every action has a visible and audible answer.
4. **Flourish**: shake, particles, squash, tweens that add weight.
5. **Restraint**: tune down until nothing obscures the play space.

## Juice checklist

| Item | Target / guideline | Check |
|---|---|---|
| Input latency | Act on input the same frame it is read; avoid waiting for animation to start the gameplay effect | Record at high fps, count frames from press to motion |
| Coyote time | ~0.05-0.15 s to still jump after leaving a ledge | Run off ledges and jump late |
| Jump buffering | ~0.1-0.15 s: a jump pressed just before landing fires on landing | Mash jump while falling |
| Variable jump height | Release early cuts upward velocity | Tap vs hold gives clearly different heights |
| Hit-stop | Freeze or slow attacker+target ~2-6 frames on strong hits | Heavy hits feel heavier than light ones |
| Screen shake | Trauma model (below), capped, decays fast | Disable toggle works |
| Easing / tweens | UI and object motion use ease-out for arrivals, ease-in for departures; avoid linear for anything organic | No popping in or out |
| Squash and stretch | Stretch on take-off along velocity, squash on landing; preserve rough volume | Character reads as springy, not rubbery |
| Particles | Short-lived bursts at contact points; direction follows the impact | Hits, landings, pickups all emit something |
| Sound layering | Each key sound = transient (click/snap) + body (thump) + tail (debris/reverb); random pitch +/- a few % | Repeated sounds do not machine-gun |
| Camera lead | Camera looks ahead in movement/aim direction | Player sees threats before reaching them |
| Camera smoothing | Critically damped follow or lerp by `1 - exp(-k*dt)`; dead zone for small moves | No jitter, no seasickness |
| Feedback for every action | Press, success, failure, blocked, cooldown-ready all communicated | Mute audio: still readable? Turn off color: still readable? |
| Readability over noise | Enemy tells, projectiles and the player always visible above effects | Screenshot at peak chaos: can you find the player in 1 s? |
| Accessibility toggles | Screen shake scale, flash reduction, motion blur off, hit-stop off, colorblind-safe palette, subtitle size | All reachable from the pause menu |

Values above are starting points; tune them in playtests and record final values in the
system doc's tuning knobs.

## Trauma-based screen shake

Events add trauma; shake strength is trauma squared so small hits barely move the camera
and big ones spike. Smooth noise beats per-frame random for a less jittery look.

```
# tunables
maxOffset = 12        # pixels or world units
maxAngle  = 3         # degrees
decayPerSec = 1.5
shakeScale = settings.shakeScale   # 0..1 accessibility slider

trauma = 0            # 0..1

addTrauma(amount):
  trauma = min(1, trauma + amount)

update(dt):
  trauma = max(0, trauma - decayPerSec * dt)
  s = trauma * trauma * shakeScale
  t = time * noiseFrequency
  camera.offset.x = maxOffset * s * noise(seedX, t)   # noise returns -1..1
  camera.offset.y = maxOffset * s * noise(seedY, t)
  camera.angle    = maxAngle  * s * noise(seedA, t)
```

Typical amounts: light hit 0.2, heavy hit 0.4, explosion 0.6-0.8. Apply the offset on
top of the follow position, never into it, or the camera drifts.

## Coyote time and jump buffering

```
coyoteTime = 0.1      # seconds
bufferTime = 0.12
coyoteTimer = 0
bufferTimer = 0

update(dt):
  if isGrounded: coyoteTimer = coyoteTime
  else:          coyoteTimer -= dt

  if input.jumpPressed: bufferTimer = bufferTime
  else:                 bufferTimer -= dt

  if bufferTimer > 0 and coyoteTimer > 0:
    velocity.y = jumpVelocity
    bufferTimer = 0
    coyoteTimer = 0          # prevents double jump from the same window

  if input.jumpReleased and velocity.y > 0:   # variable jump height (y up)
    velocity.y *= jumpCutMultiplier          # e.g. 0.5
```

Read input in the render/update loop and consume the buffered flag in the fixed physics
step, so presses between physics ticks are not lost.

## Hit-stop

```
hitStop(duration):
  hitStopTimer = max(hitStopTimer, duration)   # do not stack, take the longest

gameplayUpdate(dt):
  if hitStopTimer > 0:
    hitStopTimer -= realDt
    return                                  # freeze gameplay; keep UI, audio, shake running
  ...
```

Scale duration with hit strength. Keep it off for rapid-fire weapons or it becomes stutter.

## Camera rules

- Separate target (where the camera wants to be) from position (where it is). Smooth the
  position toward the target with a frame-rate independent factor.
- Lead = velocity or aim direction times a small distance, itself smoothed.
- Use a dead zone so small corrections do not move the camera.
- Clamp to level bounds after shake is added only if shake must stay in-bounds.
- 2D pixel art: snap the final camera position to whole pixels to avoid shimmering.

## Feedback mapping table

Fill one row per player action in the system doc.

| Action | Visual | Audio | Haptic | Camera | UI |
|---|---|---|---|---|---|
| Jump | stretch, dust | whoosh | none | none | none |
| Land hard | squash, dust ring | thud | light | trauma 0.15 | none |
| Hit enemy | flash white 1-2 frames, particles | layered impact | medium | hit-stop + trauma 0.2 | damage number |
| Blocked action | shake icon | dull click | none | none | cooldown highlight |

## Common feel bugs

| Symptom | Likely cause |
|---|---|
| Floaty jump | Gravity too low or same on rise and fall; use higher fall gravity |
| Jump sometimes ignored | Input read in fixed step only, or no buffer |
| Mushy controls | Acceleration too low, or animation gates movement |
| Camera jitter | Camera updated before target moved, or physics not interpolated |
| Effects hide enemies | No draw-order or opacity rule for effects vs threats |
