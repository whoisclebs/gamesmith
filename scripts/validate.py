#!/usr/bin/env python3
"""Validate gamesmith skills and plugin manifests. Standard library only (Python 3.9+)."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALLOWED_KEYS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
KEY_RE = re.compile(r"^([A-Za-z0-9_-]+):(.*)$")
LINK_RE = re.compile(r"\]\(((?:references|assets|scripts)/[^)\s]+)\)")
MANIFESTS = [
    ".claude-plugin/plugin.json",
    ".claude-plugin/marketplace.json",
    ".codex-plugin/plugin.json",
    ".agents/plugins/marketplace.json",
]
problems = []  # (level, path, message)


def report(level, path, msg):
    problems.append((level, path, msg))


def rel(path):
    return path.relative_to(ROOT).as_posix()


def unquote(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def parse_frontmatter(text):
    """Return (top-level fields, body) for SKILL.md text. Raises ValueError if malformed."""
    lines = text.splitlines()
    if not lines or lines[0].rstrip() != "---":
        raise ValueError("line 1 must be '---'")
    end = next((i for i in range(1, len(lines)) if lines[i].rstrip() == "---"), None)
    if end is None:
        raise ValueError("missing closing '---'")
    fields = {}
    for line in lines[1:end]:
        if not line.strip() or line[0] in " \t#":
            continue  # blank, comment, or nested block content
        match = KEY_RE.match(line)
        if match:
            fields[match.group(1)] = unquote(match.group(2))
    return fields, "\n".join(lines[end + 1:])


def check_skill(folder):
    md = folder / "SKILL.md"
    if not md.is_file():
        report("ERROR", rel(folder), "missing SKILL.md")
        return
    path = rel(md)
    try:
        fields, body = parse_frontmatter(md.read_text(encoding="utf-8-sig"))
    except ValueError as exc:
        report("ERROR", path, str(exc))
        return
    for key in fields:
        if key not in ALLOWED_KEYS:
            report("ERROR", path, f"unknown top-level key '{key}'")
    for key in ("name", "description"):
        if not fields.get(key):
            report("ERROR", path, f"missing or empty '{key}'")
    name = fields.get("name", "")
    if name:
        if not NAME_RE.match(name) or len(name) > 64:
            report("ERROR", path, f"name '{name}' must match {NAME_RE.pattern} and be <=64 chars")
        if name != folder.name:
            report("ERROR", path, f"name '{name}' does not match folder '{folder.name}'")
    desc = fields.get("description", "")
    if desc:
        if len(desc) > 500:
            report("ERROR", path, f"description is {len(desc)} chars (max 500)")
        if "use when" not in desc.lower():
            report("ERROR", path, "description must contain 'Use when'")
    lines = len(body.splitlines())
    if lines > 500:
        report("ERROR", path, f"body is {lines} lines (max 500)")
    elif lines > 300:
        report("WARN", path, f"body is {lines} lines (over 300)")
    for target in LINK_RE.findall(body):
        if not (folder / target.split("#")[0]).exists():
            report("ERROR", path, f"broken link '{target}'")
    openai = folder / "agents" / "openai.yaml"
    if not openai.is_file() or "display_name" not in openai.read_text(encoding="utf-8-sig"):
        report("ERROR", rel(openai), "missing, or lacks 'display_name'")


def check_manifest(name):
    path = ROOT / name
    if not path.is_file():
        report("WARN", name, "missing, skipped")
        return
    try:
        json.loads(path.read_text(encoding="utf-8-sig"))
    except ValueError as exc:
        report("ERROR", name, f"invalid JSON: {exc}")


def self_test():
    fields, body = parse_frontmatter(
        '---\nname: demo\ndescription: "Does x. Use when y."\nmetadata:\n  owner: a\n---\n# Body\n')
    assert fields == {"name": "demo", "description": "Does x. Use when y.", "metadata": ""}, fields
    assert body == "# Body", repr(body)
    fields, _ = parse_frontmatter("---\ndescription: 'a: b'\n# note\n  nested: 1\nname: y\n---\n")
    assert fields == {"description": "a: b", "name": "y"}, fields
    fields, body = parse_frontmatter("---\r\nname: z\r\n---\r\nbody")
    assert fields == {"name": "z"} and body == "body", (fields, body)
    for bad in ("name: x\n---\n", "---\nname: x\n"):
        try:
            parse_frontmatter(bad)
        except ValueError:
            continue
        raise AssertionError(f"expected ValueError for {bad!r}")
    assert NAME_RE.match("pixel-art-2d") and not NAME_RE.match("Bad--name")
    assert not NAME_RE.match("-lead") and not NAME_RE.match("Upper")


def main(argv):
    if "--self-test" in argv:
        self_test()
        print("self-test ok")
        return 0
    folders = sorted(p for p in (ROOT / "skills").glob("*") if p.is_dir())
    for folder in folders:
        check_skill(folder)
    for name in MANIFESTS:
        check_manifest(name)
    for level, path, msg in problems:
        print(f"{level} {path}: {msg}")
    errors = sum(1 for level, _, _ in problems if level == "ERROR")
    warns = sum(1 for level, _, _ in problems if level == "WARN")
    print(f"{len(folders)} skills, {errors} errors, {warns} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
