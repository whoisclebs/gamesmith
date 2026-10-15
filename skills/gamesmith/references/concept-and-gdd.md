# Concept and Game Design Document

Turn an idea into a one-page pitch, then into per-system design docs that a programmer
can build and a tester can verify.

## Brainstorm flow

Run these steps in order. Offer 2-3 options at each step; the user picks.

1. **Player fantasy.** One sentence: what does the player get to *be* or *feel*?
   "A tiny courier dodging rooftop traffic", not "a platformer with deliveries".
2. **Core loop at three scales.** Write each as verb chains.

   | Scale | Question | Example (roguelite courier) |
   |---|---|---|
   | ~30 seconds | What does the player do moment to moment? | Run, jump gaps, dodge drones, grab parcel |
   | ~5 minutes | What goal ties moments together? | Finish a delivery route before the timer, earn coins |
   | Session (30-60 min) | Why come back / keep going? | Unlock a new district, upgrade the bike, beat best time |

   If the 30-second loop is not fun alone, the larger loops will not save it.
3. **Pillars (3-5).** Short, testable statements every feature must serve.
   Good: "Every jump is a decision." Bad: "Fun gameplay."
4. **Anti-pillars (2-4).** What the game deliberately is not. These kill scope creep.
   "No crafting. No dialogue trees. No open world."
5. **Target player.** Who, where, how long per session, what they play now, what device.
   "Commuters on phones, 5-10 minute sessions, play Subway Surfers and Downwell."
6. **References.** 2-4 existing games, each with what to take and what to avoid.
7. **Scope class.** Pick one and say it out loud:

   | Class | Team / time | Content budget |
   |---|---|---|
   | Jam | 1-3 people, 2-7 days | 1 mechanic, 1 level or endless mode |
   | Small | 1-3 people, 1-3 months | 1 core mechanic + 2 twists, 10-20 levels or 1 run structure |
   | Medium | 3-10 people, 6-18 months | Several systems, full meta progression |
   | Large | More | Out of scope for a first project; cut down |

8. **Riskiest assumption.** The one thing that, if false, kills the game. This becomes
   the first prototype question (see `prototyping.md`).

## One-page pitch template

```markdown
# <Title> — one-page pitch

**Hook (1 sentence):** <fantasy + twist>
**Genre / camera / platform:** <e.g. 2D side-scroller / mobile + web>
**Target player:** <who, session length, comparable games>
**Scope class:** <jam / small / medium>, <team>, <deadline>

## Core loop
- 30 s: <verbs>
- 5 min: <goal>
- Session: <reason to return>

## Pillars
1. <pillar>  2. <pillar>  3. <pillar>

## Anti-pillars
- <not this>  - <not this>

## Unique selling point
<what a player would tell a friend>

## MVP (smallest playable that proves the loop)
- <feature> - <feature> - <feature>

## Cut list (not in MVP)
- <idea>

## Riskiest assumption -> first prototype question
<question>

## Business (if commercial)
Price model: <premium / F2P / ads>. Comparable titles: <names>. Revenue data: NOT ASSESSED unless sourced.
```

## GDD: one doc per system

Write a doc only for systems that are in the MVP or slice. Keep each one to what is
needed to build and test it. File per system: `docs/gdd/<system>.md`.

```markdown
# System: <name>
Priority: MVP | Slice | Full        Owner: <name>        Status: draft | agreed | built

## Summary
<2-3 sentences: what it does and why it exists. Which pillar it serves.>

## Player fantasy
<What the player should feel when using it.>

## Rules
1. <Rule as a testable statement.>
2. ...

## States
| State | Enter when | Exit when | Player can | Feedback |
|---|---|---|---|---|
| Idle | spawn, land | input move | move, jump | idle anim |
| Dash | dash pressed, cooldown ready | 0.2 s elapsed | nothing | trail, whoosh |

## Formulas
| Name | Formula | Variables (range) | Example |
|---|---|---|---|
| Damage | `base * (1 + 0.1*level) * crit` | base 5-50, level 1-20, crit 1 or 2 | 10*(1.5)*1 = 15 |

## Edge cases
- <What happens at 0, at max, on simultaneous events, on disconnect, on pause, on death mid-action.>

## Dependencies
- Needs: <systems/data this reads>
- Feeds: <systems that read this>
- Events emitted: <EventName(payload)>

## Tuning knobs
| Knob | Default | Safe range | Effect when raised |
|---|---|---|---|
| dashCooldownSec | 1.0 | 0.4-2.0 | less dashing, slower pace |

## Acceptance criteria
- [ ] <Observable, pass/fail statement a tester can check.>
- [ ] <e.g. Dash covers 3 tiles +/- 0.1 at any frame rate 30-144.>

## Open questions
- <question> (decide by <date/stage>)
```

## Writing rules for system docs

- Every rule must be testable. "Feels good" goes in Player fantasy, not Rules.
- Every number lives in Tuning knobs or Formulas with a range, never only in prose.
- Ranges are design intent. Real values come from playtests; until then mark them
  "initial guess".
- Edge cases list: zero, max, overflow, simultaneity, interruption, network loss,
  save/load mid-state.
- States table must cover every state the code will have. If code adds a state, the doc
  is updated in the same change.
- Dependencies reveal build order. Build the systems with no "Needs" first.
- Priority decides inclusion. Slice and Full items do not get built during MVP work.

## Review checklist for a GDD (gate: Design)

| Check | Verdict |
|---|---|
| Every MVP system has a doc | PASS / FAIL |
| Each doc names the pillar it serves | PASS / CONCERNS |
| Formulas have variable ranges and a worked example | PASS / CONCERNS |
| States table matches the rules | PASS / CONCERNS |
| Acceptance criteria are pass/fail | PASS / CONCERNS |
| No system contradicts an anti-pillar | PASS / FAIL |
| Total MVP fits the scope class | PASS / CONCERNS / NOT ASSESSED (no estimate yet) |
