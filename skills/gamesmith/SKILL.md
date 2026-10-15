---
name: gamesmith
description: Engine-agnostic core for building games end to end. Runs a gated pipeline from concept and design doc through prototype, vertical slice, production, polish, release and post-launch, with game-feel, balancing and playtesting guidance, and routes engine work to gamesmith-roblox, gamesmith-godot, gamesmith-unity, gamesmith-web or gamesmith-blender. Use when the user wants to design, plan, prototype, balance, playtest, scope or ship a game, or starts a game project of any kind.
license: MIT
metadata:
  pack: gamesmith
  role: core-router
---

# Gamesmith

Take a game from idea to shipped build, one gated stage at a time. This skill owns the
engine-agnostic process and gameplay rules. Engine specifics live in sibling skills.

## 1. First response: detect, then route

Before proposing anything, find out what exists and where the user is.

**Inspect the working directory** (do not ask what files can answer):

| Signal found | Engine | Route to |
|---|---|---|
| `default.project.json`, `*.rbxl`, `*.rbxlx`, `aftman.toml`, `rokit.toml`, `wally.toml` | Roblox (Rojo/Luau) | `gamesmith-roblox` |
| `project.godot`, `*.tscn`, `*.gd`, `export_presets.cfg` | Godot | `gamesmith-godot` |
| `ProjectSettings/`, `Assets/` + `Packages/manifest.json`, `*.unity`, `*.asmdef` | Unity | `gamesmith-unity` |
| `package.json` depending on `phaser`, `three`, `pixi.js`, `babylonjs`, `kaboom`/`kaplay`, or a `<canvas>` game page | Web | `gamesmith-web` |
| `*.blend`, Blender add-on `__init__.py` with `bl_info`, asset-pipeline folders | Blender (assets) | `gamesmith-blender` |
| Nothing game-related | Idea only | stay here, start at Concept |

Several signals can coexist (Unity project plus `.blend` sources): route code work to the
engine skill and asset work to `gamesmith-blender`.

**Then establish the stage.** Ask at most three short questions, only for what files
could not tell you:

1. What is the game in one sentence, and who is it for?
2. What exists already (doc, prototype, playable build, live game)?
3. What is the target (jam, portfolio, commercial, live service) and the deadline?

Map the answers to a stage in section 2 and say it back: "You are at *Prototype*. The
gate to leave it needs X and Y. Missing: Y." Then propose the next concrete step.

If no engine is chosen yet, recommend one from the constraints, then let the user decide:

| Constraint | Lean toward |
|---|---|
| Wants a built-in audience, multiplayer, young players | Roblox |
| 2D or small 3D, free and open source, light install | Godot |
| Mobile/console reach, large asset ecosystem, 3D heavy | Unity |
| Instant play in a browser link, jams, tiny downloads | Web (Phaser / three.js) |
| Only needs models, rigs, animation or renders | Blender |

## 2. Stage pipeline with gates

Each stage ends at a gate. A gate is checked, not assumed. For every required artifact
give a verdict:

- **PASS**: artifact exists and meets the bar.
- **CONCERNS**: exists but has named gaps; list them and the risk of moving on anyway.
- **FAIL**: missing or contradicts the goal; do not advance.
- **NOT ASSESSED**: no evidence available (no data, no playtest, file not shown). Never
  fill this with a guess or an invented number.

The user may choose to advance on CONCERNS. Record the decision and the open risks.

| Stage | Goal | Gate artifacts | Read |
|---|---|---|---|
| Concept | Decide what the game is and is not | One-page pitch, core loop at 3 scales, 3-5 pillars + anti-pillars, target player, scope class | `references/concept-and-gdd.md` |
| Design (GDD) | Specify systems enough to build | System docs for MVP systems with rules, states, formulas, acceptance criteria, MVP/slice/full priority | `references/concept-and-gdd.md` |
| Prototype | Answer the riskiest question cheaply | One question per prototype, timebox met, PROCEED / PIVOT / KILL verdict with evidence | `references/prototyping.md` |
| Vertical slice | Prove the full experience at final quality in a small piece | Playable slice, 3+ external playtests, feel pass, production estimate | `references/prototyping.md`, `references/game-feel.md`, `references/playtesting.md` |
| Production | Build all content and systems | Milestone plan, risk register, feature-complete build, balance sheet | `references/production-and-release.md`, `references/balancing.md` |
| Polish | Remove friction, raise quality, hit performance | Polish checklist done, no open blocker/critical bugs, perf target met on min spec | `references/production-and-release.md`, `references/game-feel.md` |
| Release | Ship a build people can buy or play | Release checklist done, store page live, crash reporting and analytics verified, save compatibility tested | `references/production-and-release.md` |
| Post-launch | Learn, patch, decide what's next | Telemetry review, patch notes, post-mortem with actions | `references/production-and-release.md`, `references/balancing.md` |

Gate report format:

```
Gate: Prototype -> Vertical slice
- Prototype question answered ............ PASS (players found the grapple fun in 4/5 sessions)
- Timebox respected ...................... CONCERNS (took 3 days vs 1; scope crept into art)
- Verdict recorded ....................... PASS (PROCEED)
- Retention signal ....................... NOT ASSESSED (no build shipped to testers yet)
Overall: CONCERNS. Advance only if the user accepts: art time not yet estimated.
```

Small projects (jam, learning, under ~2 weeks) collapse stages: Concept + Design is one
page, Prototype is the game, Polish is the last day. The gates still apply, just lighter.

## 3. Collaboration rules

- **The user owns creative direction.** For big calls (genre, core mechanic, art style,
  monetization, platform, cutting a pillar) present 2-3 options with tradeoffs and a
  recommendation, then wait for the decision. Do not pick silently.
- **Act on small calls.** Variable names, file layout, a tween curve, a placeholder
  color: decide, mention it in one line, move on.
- **Scope discipline.** Small games stay small.
  - Define the MVP as the smallest build that delivers the core loop once, start to end.
  - Keep a written **cut list** from day one. New ideas go there first, not into the build.
  - When asked to add a feature, state its cost in the current milestone and what it
    displaces. Default answer for anything outside the pillars: cut list.
  - Prefer one mechanic with depth over five shallow ones.
- **Evidence over opinion.** "Fun" is claimed from playtests, not from the design doc.
  When there is no evidence, say NOT ASSESSED and propose how to get it.
- **Keep artifacts in the repo** (`docs/pitch.md`, `docs/gdd/<system>.md`,
  `docs/playtests/`, `docs/cutlist.md`) so any agent or teammate can pick up the thread.

## 4. Gameplay code rules (engine-agnostic)

Apply in every engine; the sibling skill shows the idiomatic form.

1. **Data-driven tunables.** Speeds, damage, costs, timers, spawn tables live in data
   (config file, resource, ScriptableObject, ModuleScript table, JSON), not literals in
   logic. Designers tune without touching code. Name units: `jumpHeightTiles`, `cooldownSec`.
2. **Frame-rate independence.** Scale continuous motion by delta time. Run physics and
   anything that must be deterministic on a fixed timestep; interpolate rendering between
   steps. Never assume 60 fps.
3. **Gameplay never references UI.** Gameplay emits events or updates observable state
   (`HealthChanged(current, max)`); UI subscribes. Deleting the HUD must not break the game.
4. **Explicit state machines.** Player, enemy, door, match flow: named states, explicit
   transitions, enter/exit hooks. Replace boolean soup (`isJumping && !isDashing && ...`)
   with one `state` field.
5. **Logic testable apart from presentation.** Rules (damage calc, inventory, scoring,
   turn order, economy) are plain code with no scene, node or render dependency, so they
   run in unit tests and headless simulation.
6. **No global mutable singletons for game state.** Pass state or services explicitly, or
   use one composition root. Stateless helpers and engine-provided services are fine.
   Global mutable state breaks tests, save/load and multiplayer.
7. **Pool hot spawns.** Bullets, particles, damage numbers, pickups: reuse from a pool
   instead of create/destroy per frame. Reset all fields on reuse.
8. **Save data is versioned.** Every save has a `version` field and a migration path from
   day one of production.
9. **Seeded randomness.** Gameplay RNG takes an explicit seed so bugs and balance sims
   are reproducible.

State machine sketch (any language):

```
states = { Idle, Run, Jump, Fall, Hurt }
on update(dt):
  next = current.update(dt, input)        # returns a state or null
  if next and next != current:
    current.exit(); next.enter(); current = next
    emit("StateChanged", current.name)    # UI/audio/animation listen; logic doesn't care
```

## 5. Working loop per task

1. Name the stage and the gate the task serves.
2. For design or creative work: propose options, get a decision, write it to `docs/`.
3. For code: route to the engine skill for idioms; apply section 4 rules here.
4. Verify by running the game or tests. If you cannot run it, say what is unverified.
5. Update the gate checklist and the cut list.

## 6. References index

| File | Read when |
|---|---|
| `references/concept-and-gdd.md` | Starting from an idea, writing the pitch, defining pillars, or writing a system design doc |
| `references/prototyping.md` | Planning or judging a prototype, deciding paper vs greybox vs engine, defining the vertical slice |
| `references/game-feel.md` | Controls feel floaty or unresponsive, adding juice, camera work, hit feedback, accessibility toggles |
| `references/balancing.md` | Designing economy, XP or cost curves, damage/TTK, loot rarity, difficulty, reading telemetry |
| `references/playtesting.md` | Running a playtest, writing the report, turning findings into tasks |
| `references/production-and-release.md` | Milestones, task sizing, risks, polish pass, release checklist, patch notes, post-mortem |

Engine sibling skills: `gamesmith-roblox`, `gamesmith-godot`, `gamesmith-unity`,
`gamesmith-web`, `gamesmith-blender`.
