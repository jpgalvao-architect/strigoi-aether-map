# SPDX-License-Identifier: GPL-3.0-only
$ErrorActionPreference='Stop'
$combatRoot=Split-Path -Parent $PSScriptRoot
$combatOutput=Join-Path $combatRoot 'build/combat'
& dotnet publish (Join-Path $combatRoot 'native/combat/Strigoi.Combat.csproj') -c Release -o $combatOutput
if ($LASTEXITCODE -ne 0) { throw 'Combat helper build failed' }
$combatAssets=Join-Path $combatRoot 'app/assets/combat'
New-Item -ItemType Directory -Path $combatAssets -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $combatOutput 'strigoi-combat.exe') -Destination $combatAssets
& (Join-Path $combatAssets 'strigoi-combat.exe') --self-test
if ($LASTEXITCODE -ne 0) { throw 'Combat helper self-test failed' }
