# SPDX-License-Identifier: GPL-3.0-only
param(
  [Parameter(Mandatory=$true)][string]$Payload,
  [string]$Output = "$PSScriptRoot\..\dist\StrigoiAetherMap-Setup-0.10.0-beta.7.exe",
  [string]$Python = "$PSScriptRoot\..\.venv\Scripts\python.exe",
  [string]$Compiler = "${env:ProgramFiles(x86)}\NSIS\makensis.exe"
)
$ErrorActionPreference = 'Stop'
& $Python "$PSScriptRoot\prepare-installer.py" --payload $Payload --output $Output --compiler $Compiler
if ($LASTEXITCODE -ne 0) { throw 'Installer build failed' }
