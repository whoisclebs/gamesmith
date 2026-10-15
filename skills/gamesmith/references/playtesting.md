# Playtesting

Playtests replace opinion with evidence. Plan what to learn, watch without helping,
separate what you saw from what you think, then turn it into tasks.

## When and who

| Stage | Testers | Focus |
|---|---|---|
| Prototype | 3-5 people who did not build it | The single prototype question |
| Vertical slice | 5-8 target players | Onboarding, core loop clarity, feel |
| Production | Rolling, 5+ per milestone | New content, difficulty, progression |
| Polish / pre-release | 10+ incl. fresh players | Bugs, UX friction, performance, accessibility |
| Post-launch | Telemetry + community | Retention, balance, live issues |

Fresh eyes matter: anyone who played before cannot test onboarding again.

## Test plan template

```markdown
# Playtest plan: <build/version> — <date>
Goal: <what decision this test informs>
Questions (max 3):
1. <yes/no or measurable question>
Build: <version, platform, known issues list>
Testers: <count, profile, how recruited>
Setup: <device, controls, recording (screen + face/hands if consented)>
Script:
- Intro (read verbatim): "We are testing the game, not you. Please think aloud. I can't
  answer questions during play."
- Task: <e.g. "Play until you want to stop, max 20 min">
- Post-play questions: <list>
Metrics to capture: <time to first success, deaths per level, quit point, ...>
Consent: <recording and data use explained and agreed>
```

## First-five-minutes protocol

The first five minutes decide whether a player stays. Test them on every milestone with
new players.

1. Start the clock at launch, not at the gameplay screen.
2. Log timestamps for: first input, first understood goal (player says it), first
   success, first failure, first moment of delight (laugh, "oh nice"), first confusion.
3. Note every pause longer than ~5 seconds and what was on screen.
4. At 5 minutes ask: "What is the goal of this game?" and "What would you do next?"
   Compare with the pitch's 30-second and 5-minute loop.
5. Pass bar: player states the core goal in their own words and has had at least one
   success. If not, onboarding is a blocker.

## Observe, don't explain

- Do not help, hint, or point. If the player is stuck for long, note the time, then
  offer one neutral nudge ("What do you think you could try?") and mark it as an
  intervention.
- Do not defend the design or explain intent. Every explanation hides a bug in the game.
- Watch hands and face as much as the screen.
- Write what happened, not what it means: "Pressed jump 4 times at wall" not "doesn't
  get wall jump".
- Think-aloud is useful but changes behavior; for feel tests, run some silent sessions.
- Post-play: ask open questions first ("What stood out?"), specific ones later. Ask about
  behavior ("When did you want to stop?") over preference ("Did you like it?").

## Metrics vs observations

| Metrics (numbers) | Observations (behavior) |
|---|---|
| Time to complete level, deaths, retries, quit time, items used | Confusion, frustration, delight, what they tried, what they said |
| Tell you *what* and *where* | Tell you *why* |
| Need enough sessions to trust; small samples only flag | One clear observation can reveal a design flaw |

Rules:
- With fewer than ~5 testers, report counts ("3 of 5"), not percentages.
- Never extrapolate a number that was not measured; write NOT ASSESSED.
- Self-reported fun scores are weak signals; behavior (wanting to play again, playing
  past the time limit) is stronger.

## Report template

```markdown
# Playtest report: <build> — <date>
Testers: <n>, profile: <who>
Questions and answers:
1. <question> -> <answer> (evidence: <counts / quotes / timestamps>)
   or NOT ASSESSED (<why>)

## Key findings (ranked)
| # | Finding (observed) | Evidence | Severity | Suggested fix |
|---|---|---|---|---|
| 1 | 4/5 missed the dash prompt | timestamps, quotes | Major | Trigger tutorial on first gap |

## Positive signals
- <what worked; protect these from changes>

## Metrics
| Metric | Value | Target | Status |
|---|---|---|---|

## Bugs found
- <repro steps, build, platform>

## Decisions needed from the user
- <creative calls the data surfaced>
```

## Triage severity

| Severity | Definition | Action |
|---|---|---|
| Blocker | Cannot progress, crash, data loss, or core loop not understood by most testers | Fix before next test |
| Critical | Breaks a pillar or causes many testers to quit | Fix this milestone |
| Major | Repeated friction or confusion, workaround exists | Schedule this or next milestone |
| Minor | Single-tester annoyance, cosmetic issue | Backlog; batch in polish |
| Note | Opinion or idea with no observed problem | Cut list or ignore |

Frequency raises severity: a minor issue hit by every tester is major.

## Turning findings into tasks

1. Group findings by root cause, not by symptom (three "can't find the door" reports may
   be one lighting problem).
2. For each root cause write one task:
   - **Title**: verb + object ("Make dash prompt appear at first gap").
   - **Why**: link to finding and evidence.
   - **Done when**: observable acceptance ("next test: 4 of 5 testers dash unprompted").
   - **Size** and **severity**.
3. Separate creative decisions from fixes. Present creative ones to the user with options.
4. Add a re-test question to the next playtest plan for every fix.
5. Ideas from testers that are not fixes go to the cut list, not the sprint.
