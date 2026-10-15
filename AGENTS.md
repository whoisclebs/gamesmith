# AGENTS.md

This repository is **gamesmith**, a pack of agent skills for building games. It is content, not an app.

- Skills live in `skills/<name>/SKILL.md`, with depth in `references/`, helpers in `scripts/` and `assets/`, and Codex UI metadata in `agents/openai.yaml`.
- Follow `CONTRIBUTING.md` for frontmatter and writing rules. Keep each skill portable across Claude Code, Codex and other Agent Skills clients.
- Run `python scripts/validate.py` before committing. CI runs the same check.
- Plugin manifests: `.claude-plugin/` (Claude Code), `.codex-plugin/` and `.agents/plugins/` (Codex). When you add a skill, the `skills/` folder is picked up automatically; update the README table.
