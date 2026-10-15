# Tooling

Pin every tool version in the repo so the whole team and CI run the same binaries. Exact versions
change often: let the tools pin current releases instead of copying numbers from examples.

## Script Sync or Rojo

| Situation | Choose |
| --- | --- |
| Solo or small team, Studio-centric, wants scripts as local files for an editor or agent | Studio Script Sync (built into Studio; check current docs for its status and setup) |
| Git, code review, packages, linting, CI, several programmers | Rojo |
| Large world built in Studio plus code in git | Hybrid: Rojo maps only code folders; the map lives in the place file / Team Create |
| Existing Rojo project | Keep Rojo. Do not mix Script Sync on the same scripts |

Rojo syncs disk → Studio for scripts. Edits made in Studio to synced scripts are overwritten on the next
sync; fix the file instead.

## Rokit (toolchain manager)

Rokit replaces Aftman and Foreman and reads a `rokit.toml` in the repo root.

```bash
rokit init
rokit add rojo-rbx/rojo
rokit add UpliftGames/wally
rokit add JohnnyMorganz/StyLua
rokit add Kampfkarren/selene
rokit add JohnnyMorganz/luau-lsp
rokit add lune-org/lune
rokit install            # teammates and CI: install exactly what rokit.toml pins
```

If the repo already has `aftman.toml` or `foreman.toml`, keep using that manager unless the user agrees to migrate.

## Rojo

```bash
rojo init                                   # new project scaffold
rojo plugin install                         # matching Studio plugin
rojo serve                                  # live sync; connect from the Studio plugin
rojo build default.project.json -o game.rbxl
rojo sourcemap default.project.json -o sourcemap.json   # for luau-lsp
```

File naming:

| On disk | In Studio |
| --- | --- |
| `name.server.luau` | Script |
| `name.client.luau` | LocalScript |
| `name.luau` | ModuleScript |
| folder with `init.luau` / `init.server.luau` / `init.client.luau` | That script, with the folder's other files as children |
| `name.model.json`, `name.rbxm` / `name.rbxmx` | Instances (remotes, configured parts, UI) |
| `name.meta.json` / `init.meta.json` | Extra properties for the matching instance |
| `name.json` | ModuleScript returning the decoded table |

Project file with packages (add the package entries only after `wally install` created the folders,
because Rojo errors on a missing `$path`):

```json
{
  "name": "my-roblox-game",
  "tree": {
    "$className": "DataModel",
    "ReplicatedStorage": {
      "Shared": { "$path": "src/shared" },
      "Packages": { "$path": "Packages" }
    },
    "ServerScriptService": { "Server": { "$path": "src/server" } },
    "ServerStorage": { "ServerPackages": { "$path": "ServerPackages" } },
    "StarterPlayer": { "StarterPlayerScripts": { "Client": { "$path": "src/client" } } }
  }
}
```

## Wally (packages)

```toml
# wally.toml
[package]
name = "yourname/yourgame"
version = "0.1.0"
registry = "https://github.com/UpliftGames/wally-index"
realm = "shared"

[dependencies]          # -> Packages/ (ReplicatedStorage)

[server-dependencies]   # -> ServerPackages/ (ServerStorage), never replicated
# ProfileStore = "<scope>/profilestore@<version>"  # look up the current published name and version

[dev-dependencies]      # -> DevPackages/ (tests only)
```

- `wally install` resolves and writes `wally.lock`. Commit `wally.toml` and `wally.lock`.
- Usually git-ignore `Packages/`, `ServerPackages/`, `DevPackages/` and regenerate in CI.
- Server-only libraries go under `[server-dependencies]` so their code never reaches clients.
- For luau-lsp types through Wally re-export stubs, run `wally-package-types --sourcemap sourcemap.json Packages/`.

## Formatting, linting, types

```toml
# stylua.toml
syntax = "Luau"
column_width = 120
indent_type = "Tabs"
```

```toml
# selene.toml
std = "roblox"
```

`.luaurc` (plain JSON, no comments):

```json
{ "languageMode": "strict" }
```

- `stylua src` formats; `stylua --check src` fails CI on drift.
- `selene src` lints with the Roblox standard library definitions.
- luau-lsp: editor extension or `luau-lsp analyze` in CI. It needs `sourcemap.json` (Rojo) and the
  Roblox type definitions file; see the luau-lsp README for the current flags.
- `--!strict` per file still wins over `.luaurc`; keep it explicit in new files.

## Testing

| Code under test | Runner |
| --- | --- |
| Pure Luau logic (inventory math, formulas, validators) with no engine services | Lune, outside Studio; fast and CI-friendly |
| Code that needs the engine (instances, services, physics) | Jest Lua for Roblox (Jest-style API, a dev dependency) or TestEZ (older, still common), run inside Studio or a cloud runner |
| Full flows (join, buy, save) | Manual multi-client Studio test plan, or Studio MCP playtest |

Keep game rules in pure modules so most tests run in Lune.

```luau
-- tests/inventory.spec.luau   run: lune run tests/inventory.spec
local Inventory = require("../src/shared/Inventory")

local inv = Inventory.new(2)
assert(inv:add("sword") == true, "first item fits")
assert(inv:add("shield") == true, "second item fits")
assert(inv:add("bow") == false, "capacity enforced")
assert(inv:add("") == false, "empty id rejected")
print("inventory.spec ok")
```

```luau
-- Jest Lua for Roblox, e.g. src/shared/Inventory.spec.luau
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local JestGlobals = require(ReplicatedStorage.DevPackages.JestGlobals)
local Inventory = require(script.Parent.Inventory)
local describe, it, expect = JestGlobals.describe, JestGlobals.it, JestGlobals.expect

describe("Inventory", function()
	it("enforces capacity", function()
		local inv = Inventory.new(1)
		expect(inv:add("sword")).toBe(true)
		expect(inv:add("bow")).toBe(false)
	end)
end)
```

Running engine tests headless in CI needs a cloud runner such as Open Cloud Luau execution against a test
place; check current docs and keep its API key in CI secrets, never in the repo.

## CI sketch (GitHub Actions)

```yaml
name: ci
on: [push, pull_request]
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      # Install Rokit with the method its README currently recommends for CI, then:
      - run: rokit install
      - run: wally install
      - run: stylua --check src
      - run: selene src
      - run: rojo sourcemap default.project.json -o sourcemap.json
      # - run: luau-lsp analyze ...   # flags and definitions file per luau-lsp README
      - run: rojo build default.project.json -o build.rbxl
      - run: lune run tests/inventory.spec
```

Publishing to Roblox from CI (Open Cloud place publishing) is a deliberate release step: require a manual
approval and a scoped API key.
