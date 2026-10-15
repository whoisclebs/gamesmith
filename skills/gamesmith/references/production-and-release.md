# Production and Release

Plan in milestones, size work honestly, track risks, then polish, ship and learn.

## Milestone plan

Each milestone ends with a playable build and a gate review. Template:

```markdown
# Milestone <n>: <name> — target <date>
Goal (one sentence, player-facing): <e.g. "World 1 playable start to boss">
Exit criteria:
- [ ] <observable, testable item>
Content in: <levels, enemies, items — counts>
Systems in: <list, with GDD priority>
Out (explicitly): <items moved to later or cut list>
Playtest: <date, focus>
Risks touched: <IDs from risk register>
```

Typical sequence for a small game:

| Milestone | Contents |
|---|---|
| M1 Foundation | Project setup, build pipeline, input, save/load stub, core loop greybox |
| M2 Slice | Vertical slice (see `prototyping.md`) |
| M3 Content A | First half of content at slice quality |
| M4 Content B / feature complete | Everything in; no new features after this |
| M5 Polish / beta | Bug fixing, perf, UX, audio, accessibility, localization |
| M6 Release candidate | Release checklist, store, certification if needed |

Feature complete is a hard line. After it, only fixes and tuning.

## Task sizing

| Size | Meaning | Rule |
|---|---|---|
| S | Under half a day, clear approach | Do it |
| M | 1-2 days | Fine |
| L | 3-5 days | Split if possible |
| XL | Over a week or unknown | Must split, or run a spike first |

- A task has a "done when" line that a tester can check.
- Unknown approach means spike first (timeboxed), then size the real task.
- Track estimate vs actual. Multiply future estimates by your measured ratio; until you
  have one, assume work takes longer than planned.
- Include integration, testing and bug fixing in the estimate, not only writing code.

## Risk register

```markdown
| ID | Risk | Likelihood (L/M/H) | Impact (L/M/H) | Mitigation | Owner | Trigger to act | Status |
|---|---|---|---|---|---|---|---|
| R1 | Netcode jitter at 8 players | M | H | Spike in M1 on real network | <name> | >100 ms desync in test | open |
```

Common game risks: core loop not fun, scope larger than team, unproven tech (netcode,
procedural generation), platform certification, content pipeline speed, key person
unavailable, store/platform policy changes, performance on minimum spec.
Review the register at every milestone gate. High/High risks block the gate until mitigated
or accepted by the user.

## Polish pass checklist

**Performance**
- [ ] Frame-time target met on minimum spec (state the target and measured value).
- [ ] No hitches on spawn, level load, first-time effects (pre-warm shaders, pools).
- [ ] Memory stable over a long session (no leaks after 30+ minutes).
- [ ] Load times measured; loading screen shows progress or activity.

**Bugs**
- [ ] Zero open Blocker/Critical. Majors reviewed and accepted or fixed.
- [ ] Soft-lock sweep: every level, every menu, back/escape everywhere.
- [ ] Edge cases: pause during transitions, alt-tab, disconnect, low storage.

**UX**
- [ ] Every screen reachable and escapable with each supported input device.
- [ ] Settings persist. Remapping works if offered.
- [ ] Text readable at minimum resolution and handheld/TV distance.
- [ ] First-five-minutes test passed with fresh players.

**Audio**
- [ ] Every action has a sound; no missing or placeholder clips.
- [ ] Mix: music, SFX, voice sliders; nothing clips at max.
- [ ] Repetitive sounds varied (pitch/variants).

**Accessibility**
- [ ] Shake, flash, motion toggles. Subtitles with size option.
- [ ] Color is never the only signal.
- [ ] Remappable controls or at least alternatives; hold-to-press toggles.
- [ ] Difficulty or assist options if the pillars allow.

**Localization readiness**
- [ ] All player-facing strings in string tables, none hardcoded.
- [ ] UI tolerates ~30-40% longer text and right-to-left if targeted.
- [ ] Fonts cover target character sets.
- [ ] Number, date and plural formatting via locale-aware functions.

## Release checklist

**Store page**
- [ ] Capsule/icon art in every required size (check current store docs).
- [ ] Trailer (gameplay in first seconds), screenshots of real gameplay.
- [ ] Short and long description, tags, age rating questionnaire done.
- [ ] Price, regions, release date, system requirements set.

**Builds**
- [ ] Release build from a clean checkout via a repeatable script.
- [ ] Version number shown in game and attached to logs/analytics.
- [ ] Tested on each target platform and minimum spec, from a fresh install.
- [ ] Debug menus, cheats and dev logging disabled or gated.

**Crash reporting and analytics**
- [ ] Crash reporter sends a test crash that arrives with symbols and build version.
- [ ] Analytics events from `balancing.md` verified in the dashboard.
- [ ] Privacy policy, consent prompts and data deletion path where required.

**Save compatibility**
- [ ] Save files carry a version; migration from every shipped beta version tested.
- [ ] Corrupt or missing save handled without crash; backups kept.
- [ ] Cloud save conflicts handled if supported.

**Launch ops**
- [ ] Rollback plan: previous build can be restored.
- [ ] Support channel and known-issues page ready.
- [ ] Hotfix pipeline tested end to end.

## Patch notes

```markdown
# <Game> <version> — <date>
## Highlights
- <one or two player-facing headlines>
## Changes
- <Area>: <what changed, in player terms> (why, if not obvious)
## Balance
- <Item/ability>: <old> -> <new>
## Fixes
- Fixed <symptom the player saw>.
## Known issues
- <issue> (workaround: <...>)
```

Write for players: describe effects, not code. Always list balance changes with numbers.

## Post-launch loop

1. Week 1: watch crashes, funnel, retention, reviews daily. Hotfix blockers only.
2. Compare telemetry to the balance sheet's expected values; list deviations.
3. Plan patches from evidence (metrics + reports), triaged like playtest findings.
4. Decide: patch, content update, sequel, or close out. Present options to the user.

## Post-mortem template

```markdown
# Post-mortem: <project> — <date>
## Goals vs results
| Goal | Target | Result | Verdict |
|---|---|---|---|
| Ship by | <date> | <date> | PASS / FAIL |
| Units / players / wishlists | <target> | <measured or NOT ASSESSED> | |
| Review score | <target> | <measured or NOT ASSESSED> | |

## What went well
- <thing> — root cause: <why it worked> — keep by: <practice>

## What went poorly
- <thing> — root cause: <why, ask "why" until a process cause appears> — impact: <cost>

## Surprises
- <what nobody predicted>

## Actions for next project
| Action | Owner | When |
|---|---|---|
```

Only record numbers you have. A missing metric is NOT ASSESSED and becomes an action:
"instrument X next time".
