# gamesmith

**Agent skills for building games end to end** — from the first idea to launch day — for
[Claude Code](https://code.claude.com), [OpenAI Codex](https://developers.openai.com/codex) and any agent
that supports the open [Agent Skills](https://agentskills.io) format.

gamesmith teaches your coding agent how game developers actually work: write a lean design doc, prototype one
question at a time, add game feel, balance with numbers, playtest honestly and ship. Engine skills then cover
the specifics of Roblox, Godot, Unity, web games and Blender asset pipelines.

## Skills

| Skill | What it covers |
|---|---|
| [`gamesmith`](skills/gamesmith/SKILL.md) | Core process and router: concept, GDD, prototyping, game feel, balancing, playtesting, production, release, post-mortem |
| [`gamesmith-roblox`](skills/gamesmith-roblox/SKILL.md) | Roblox + Luau: secure remotes, DataStores/ProfileStore, monetization, Rojo/Wally tooling, performance, Studio MCP |
| [`gamesmith-godot`](skills/gamesmith-godot/SKILL.md) | Godot 4: typed GDScript, scene composition, signals, Resources, performance, export and CI |
| [`gamesmith-unity`](skills/gamesmith-unity/SKILL.md) | Unity 6 / LTS: C# patterns, ScriptableObjects, Input System, pooling, profiling, builds and tests |
| [`gamesmith-web`](skills/gamesmith-web/SKILL.md) | Browser games: Canvas, Phaser, Three.js, fixed-timestep loop, input, shipping to itch.io / Pages |
| [`gamesmith-blender`](skills/gamesmith-blender/SKILL.md) | Game-ready 3D assets with Blender: modeling rules, UVs, validation, per-engine export, headless script |

Each skill keeps a short `SKILL.md` and loads detail from `references/` only when needed, so it stays cheap in context.

## Install

### Claude Code (plugin)

```
/plugin marketplace add whoisclebs/gamesmith
/plugin install gamesmith@gamesmith
```

### Any agent (Claude Code, Codex, Cursor, ...) via the `skills` CLI

```bash
npx skills add whoisclebs/gamesmith -a claude-code -a codex
```

### Codex

```bash
codex plugin marketplace add whoisclebs/gamesmith
```

Or ask Codex: `$skill-installer install https://github.com/whoisclebs/gamesmith/tree/main/skills/gamesmith`
(repeat for each engine skill you want).

### Manual

```bash
git clone https://github.com/whoisclebs/gamesmith
cd gamesmith
./scripts/install.sh                       # user-level: ~/.claude/skills and ~/.agents/skills
./scripts/install.sh --project ../my-game  # or into one project
```

On Windows: `scripts\install.ps1` (or `-Project ..\my-game`). Restart your agent afterwards.

## Usage

Just describe what you want — the skills trigger on their own:

- "I have an idea for a co-op cooking game, help me scope an MVP."
- "Add a secure shop with dev products to my Roblox game."
- "My Godot platformer jump feels floaty — fix the game feel."
- "Export this Blender prop for Roblox and check it is game-ready."

In Claude Code you can also call a skill directly (`/gamesmith:gamesmith-roblox`); in Codex use `$gamesmith-roblox`.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Run `python scripts/validate.py` before opening a PR.

## Credits

Inspired by the ideas in
[rbsmithy-roblox-claude-skill](https://github.com/gogolumo/rbsmithy-roblox-claude-skill),
[roblox-skills](https://github.com/EL4CTEO/roblox-skills),
[blender-skills](https://github.com/kevinbadi/blender-skills),
[Blender-Superskill](https://github.com/powerhouse90/Blender-Superskill) and
[claude-code-game-studios](https://github.com/donchitos/claude-code-game-studios).
All text here is original.

## License

[MIT](LICENSE)
