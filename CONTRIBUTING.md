# Contributing to gamesmith

Every skill must load cleanly in Claude Code, OpenAI Codex and any agent that follows the
[Agent Skills spec](https://agentskills.io/specification). These rules keep it that way.

## Skill layout

```
skills/<name>/
  SKILL.md              # required, under ~300 lines
  references/*.md       # depth, loaded on demand, linked one level deep from SKILL.md
  scripts/              # optional runnable helpers
  agents/openai.yaml    # Codex UI metadata
```

## SKILL.md frontmatter

Only spec fields: `name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools` (we use the first four).
No Claude-only keys (`model`, `disable-model-invocation`, `argument-hint`, ...) — they break claude.ai uploads and are ignored by Codex.

- `name`: lowercase a-z, 0-9, hyphens, no `--`, equal to the folder name.
- `description`: 500 characters max. Start with what it does, then a `Use when ...` trigger clause. No keyword dumps.

## Writing rules

- Original wording only. Reference repos are inspiration, never a copy source.
- Imperative, dense, checklist style. Decision tables beat prose.
- No tool-specific mechanics in the body (no `AskUserQuestion`, no `${CLAUDE_SKILL_DIR}`, no `!` shell injection).
  Say "ask the user", "run", "read `references/x.md`".
- Code samples must be correct for current engine versions; prefer short, complete snippets.
- Never invent numbers: if data is missing, say **NOT ASSESSED**.
- Avoid hardcoding quotas or limits that change often; when you must, say "check current docs".

## Validate

```bash
python scripts/validate.py
```
