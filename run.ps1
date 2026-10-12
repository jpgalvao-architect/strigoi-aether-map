# SPDX-License-Identifier: GPL-3.0-only
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$pythonPath = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (!(Test-Path -LiteralPath $pythonPath)) {
    throw 'Execute primeiro: py -3.12 -m venv .venv; depois .\.venv\Scripts\python.exe -m pip install -r requirements.txt'
}
& $pythonPath -m app.main @args
exit $LASTEXITCODE
