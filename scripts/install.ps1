# Copy gamesmith skills into Claude Code and Codex skill folders.
# Usage: scripts\install.ps1 [-Project DIR]   (default: user-level ~\.claude\skills and ~\.agents\skills)
param([string]$Project = $HOME)
$ErrorActionPreference = 'Stop'
$src = Join-Path (Split-Path $PSScriptRoot -Parent) 'skills'
foreach ($dest in @((Join-Path $Project '.claude\skills'), (Join-Path $Project '.agents\skills'))) {
  New-Item -ItemType Directory -Force $dest | Out-Null
  foreach ($skill in Get-ChildItem $src -Directory) {
    $target = Join-Path $dest $skill.Name
    if (Test-Path $target) { Remove-Item -Recurse -Force $target }
    Copy-Item -Recurse $skill.FullName $target
  }
  Write-Host "Installed $((Get-ChildItem $src -Directory).Count) skills into $dest"
}
Write-Host 'Restart Claude Code / Codex to load them.'
