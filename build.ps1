# SPDX-License-Identifier: GPL-3.0-only
param([string]$Python = '.\.venv\Scripts\python.exe')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
& .\scripts\build-sonar.ps1
& .\scripts\build-combat.ps1
& $Python -m PyInstaller --noconfirm --clean strigoi.spec
if ($LASTEXITCODE -ne 0) { throw 'Build falhou' }
Write-Host 'Pronto: dist\StrigoiAetherMap\StrigoiAetherMap.exe'
