# Prototyping

A prototype is an experiment, not an early version of the game. It exists to answer one
question as cheaply as possible, then it is judged and usually thrown away.

## One question per prototype

Write the question before building anything. It must be answerable yes/no by watching
someone play.

| Weak question | Strong question |
|---|---|
| Is the game fun? | Do players chain grapple swings without being told to? |
| Does combat work? | Can a new player read which enemy attacks next within 1 second? |
| Is the economy OK? | Do players spend coins on upgrades before run 3? |

Pick the question from the riskiest assumption in the pitch. Order prototypes by risk:
core feel first, then core loop, then meta systems, then tech risks (netcode,
performance, procedural generation).

## Timebox

| Kind | Budget | Use for |
|---|---|---|
| Spike | ~4 hours | Tech feasibility: can the engine do X, how fast is Y |
| Concept prototype | ~1 day | One mechanic or loop question |
| Extended prototype | 2-5 days | Loop that needs several parts together; justify the extra time |

When the timebox ends, stop and judge, even if unfinished. An unanswered question at the
end of the box is itself a result: the idea is harder than assumed.

## Choose the medium

| If the question is about... | Use | Why |
|---|---|---|
| Rules, turn structure, economy, card/board logic | Paper (cards, dice, spreadsheet) | Minutes to change a rule, no code |
| Level flow, sightlines, pacing, scale | Greybox in engine (boxes, no art) | Space and movement need real geometry |
| Feel, timing, controls, physics, camera | Engine with real input | Feel cannot be simulated on paper |
| Performance, networking, platform limits | Engine spike on target hardware | Only real hardware answers it |
| Narrative beats, tone | Script or storyboard, read aloud | Cheapest way to hear it |

## Throwaway code rule

- Prototype code lives in its own folder or branch (`prototypes/<question-slug>/`).
- Hacks, globals and hardcoded numbers are allowed here and only here.
- Never promote prototype code into production by copy. Rewrite it with the rules in
  SKILL.md section 4. Keep the learnings and the tuned numbers, not the code.
- Exception: small pure functions (a formula, a curve) may be carried over after review
  and with a test.

## Running the test

1. Build the minimum that lets a player face the question.
2. Play it yourself for 10 minutes; fix only what blocks the question.
3. Put it in front of 3-5 people who did not build it. Do not explain beyond controls.
   See `playtesting.md` for the protocol.
4. Record observations against the question, not general impressions.

## Verdict

| Verdict | When | Next step |
|---|---|---|
| **PROCEED** | Question answered yes with evidence from external players | Write or update the system doc; plan the next riskiest question or the vertical slice |
| **PIVOT** | Partly works; a specific change might fix it | Name the one change, new question, new timebox |
| **KILL** | Answered no, or the fix would break a pillar or scope | Archive with a one-paragraph lesson; go to next idea or back to Concept |

Verdict record (`docs/prototypes/<slug>.md`):

```markdown
# Prototype: <slug>
Question: <yes/no question>
Medium: paper | greybox | engine | spike      Timebox: <planned> / <actual>
Testers: <count, who>
Evidence:
- <observation tied to the question>
Verdict: PROCEED | PIVOT | KILL
Reason: <one paragraph>
Carry forward: <numbers, insights, assets>
```

If testers were not available, the verdict is provisional and the evidence line reads
"external playtest: NOT ASSESSED".

## Three-pivot kill rule

Count pivots on the same core question. After the third PIVOT without a PROCEED, the
default verdict is KILL. The user can override, but the decision is written down with the
reason. This prevents months spent polishing an idea that never clicked.

## Vertical slice

A vertical slice is a small portion of the game built at near-final quality across every
discipline, so the team can see the real experience and estimate the rest.

**Includes:**
- Core loop playable start to finish at least once (one level, one run, one match).
- Final-quality feel: controls, camera, hit feedback, audio (see `game-feel.md`).
- Representative art and audio for that slice, not placeholders.
- UI flow: title, play, pause, fail, success, restart.
- One example of each MVP system working together.
- Target performance on minimum spec hardware.

**Excludes:**
- Breadth: more levels, more enemies, more items.
- Systems tagged Full in the GDD.
- Localization, store assets, platform certification work.

**Gate: Vertical slice -> Production**

| Artifact | Bar |
|---|---|
| Playable slice build | Runs on target platform without dev tools |
| External playtests | 3+ sessions with reports; core loop understood without help |
| Feel pass | Game-feel checklist applied to core actions |
| Performance | Meets frame-time target on min spec, or gap is measured |
| Production estimate | Per-content-unit cost measured from slice (e.g. hours per level) multiplied out to full scope |
| Scope check | Estimate fits deadline, or cut list updated until it does |

If the production estimate is missing, the gate verdict is NOT ASSESSED, not PASS.
