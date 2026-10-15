# Balancing

Balance in a spreadsheet or simulation first, in the engine second, with players third.
Every number the player can feel must be traceable to a formula and a tuning knob.

## Spreadsheet-first method

1. List every resource, stat and rate in one sheet (`docs/balance.xlsx` or CSV in repo).
2. Write formulas, not typed numbers, for derived values (cost at level N, DPS, TTK).
3. Add a **time column**: how long a typical player takes to reach each step.
4. Chart the curves. Kinks and cliffs show up instantly in a chart.
5. Export the sheet to the game's data files (CSV/JSON) so the game reads the same
   numbers. Never retype them into code.
6. Simulate where possible: a script that plays N runs with a simple policy and logs
   outcomes. Seed the RNG.
7. Only then tune in-engine, and write changes back to the sheet.

## Economy: faucets and sinks

| Faucets (create currency) | Sinks (remove currency) |
|---|---|
| Kill rewards, quest rewards, daily login, selling items, idle income | Upgrades, consumables, repairs, crafting fees, cosmetics, taxes, rerolls |

Rules:
- Track net flow per hour at each stage of progression: `faucet_rate - sink_rate`.
- If net flow is always positive and sinks are finite, currency inflates and prices stop
  mattering. Add repeatable sinks (consumables, rerolls, cosmetic upgrades).
- If net flow is negative early, new players stall. Early game should be generous.
- Separate soft currency (earned, plentiful) from hard currency (scarce or paid).
- Every faucet needs a cap or a cost in time; otherwise one exploit floods the economy.
- Multiplayer trading: watch for duplication bugs; they are economy-ending events.

## Progression curves

Let `n` be level (or tier), `a` the base, `b` the growth parameter.

| Curve | Formula | Feel | Use for |
|---|---|---|---|
| Linear | `a + b*n` | Steady, predictable | Short games, early levels, flat stat gains |
| Polynomial | `a * n^b` (b ~1.5-2.5) | Gently steepening | XP to level in most RPGs |
| Exponential | `a * b^n` (b ~1.05-1.25) | Explodes late | Idle/incremental costs; pair with exponential income |
| Logistic (S-curve) | `max / (1 + e^(-k*(n - mid)))` | Slow, fast, plateau | Mastery, diminishing returns |
| Diminishing returns | `max * x / (x + c)` | Each point worth less | Armor, crit, speed stacking |

Check:
- Compare **cost growth** to **reward growth**. If cost grows exponentially and income
  linearly, time per level explodes; that wall is either intentional or a bug.
- Compute time-to-next-level at levels 1, 5, 10, max. Write the expected values in the
  sheet; real values come from telemetry (until then: NOT ASSESSED).
- Rounding: round displayed costs to readable numbers after computing (e.g. 2 significant digits).

## Combat sanity: DPS and TTK

```
DPS = damage_per_hit * hits_per_second * hit_chance * (1 + crit_chance * (crit_mult - 1))
effective_HP = HP / (1 - damage_reduction)
TTK (seconds) = effective_HP / DPS
```

- Build a TTK matrix: each weapon/class row vs each enemy/armor column.
- Look for cells far outside the target band (e.g. target 1-3 s for common enemies).
- Shooter rule of thumb: TTK shorter than reaction time removes counterplay; very long TTK
  makes hits feel weak. Choose the band from the pillars, then test.
- Include time-to-reach: melee DPS is lower in practice than on paper.

## Loot and rarity

| Tier | Example weight | Note |
|---|---|---|
| Common | 70 | Always useful as fodder or currency |
| Uncommon | 22 | Small upgrade |
| Rare | 6.5 | Noticeable power or style |
| Epic | 1.3 | Build-defining |
| Legendary | 0.2 | Event moment |

Weights are an example shape, not a recommendation. Drop chance = weight / total weight.

**Pity timer:** guarantee a rare-or-better after N misses, or raise the chance each miss.

```
chance = base + max(0, misses - softStart) * step   # soft pity
if misses >= hardPity: chance = 1                   # hard pity
on hit: misses = 0 else misses += 1
```

Expected pulls to first legendary without pity = 1 / p (geometric). Show this in the
sheet. For paid random items, check current platform and regional rules on disclosure of
odds; they change.

## Difficulty curves

- Shape: rising sawtooth. Ramp up, then a short relief after each spike or boss.
- Introduce one new thing at a time: teach in safety, test with pressure, combine later.
- Keep a difficulty table per level: new element, enemy count, time pressure, expected
  deaths. Compare with playtest deaths.
- Dynamic difficulty: if used, adjust hidden values (spawn rate, aim error) gradually;
  never take control away visibly. Offer explicit difficulty or assist options too.

## Hunting outliers and degenerate strategies

A degenerate strategy is one that is so much better that it erases choice.

- Sort every option by value per cost (DPS per gold, XP per minute). Top outliers are
  suspects.
- Simulate: run the bot policy "always pick X" for each X; any X that beats the field
  by a wide margin needs a nerf or a counter.
- Look for loops: does any action produce more than it costs (infinite money, stun-lock,
  respawn farming)?
- Check stacking: multiplicative bonuses that combine across sources.
- Check boundaries: level 1 with max-tier item, max level with starter item, 0 and
  negative values, fractional rounding exploits.
- Ask playtesters to "break the game" in a dedicated session.

## Telemetry to watch

| Metric | Reveals |
|---|---|
| Funnel: tutorial step completion | Where new players quit |
| Session length, sessions per day | Engagement fit to target player |
| Retention D1 / D7 / D30 | Whether the loop holds |
| Level attempts and deaths per level | Difficulty spikes |
| Time to level N | Progression curve vs plan |
| Currency earned vs spent per hour | Inflation or starvation |
| Item / class pick rate and win rate | Dominant or dead options |
| Store conversion, first purchase timing | Monetization pressure points |

Rules: define events before launch, include build version in every event, compare to
the sheet's expected values, and never report a metric you did not measure; mark it
NOT ASSESSED. Respect platform privacy rules and get consent where required.
