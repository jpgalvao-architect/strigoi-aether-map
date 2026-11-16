# SPDX-License-Identifier: GPL-3.0-only
param([Parameter(Mandatory=$true)][string]$Setup)
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true' -or -not $env:RUNNER_TEMP) {
    throw 'Run this check on a disposable GitHub Actions runner.'
}
$install = Join-Path $env:RUNNER_TEMP ('azphelumbra-install-' + [guid]::NewGuid())
$data = Join-Path $env:LOCALAPPDATA 'StrigoiAetherMap'
$registry = 'HKCU:\Software\StrigoiAetherMap'
$uninstallRegistry = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\StrigoiAetherMap'
if ((Test-Path -LiteralPath $data) -or (Test-Path -LiteralPath $registry)) {
    throw 'Expected a clean Windows profile.'
}

function Invoke-CheckedProcess($file, $arguments) {
    $child = Start-Process -FilePath $file -ArgumentList $arguments -WindowStyle Hidden -PassThru
    if (-not $child.WaitForExit(180000)) {
        Stop-Process -Id $child.Id -ErrorAction SilentlyContinue
        throw "Timed out running $file"
    }
    if ($child.ExitCode -ne 0) { throw "$file exited with code $($child.ExitCode)" }
}

$env:QT_QPA_PLATFORM = 'offscreen'
$env:STRIGOI_DATA_DIR = $data
$env:PYTHONPATH = $null
$env:QT_PLUGIN_PATH = $null
$env:PATH = "$env:WINDIR\System32;$env:WINDIR"
$arguments = @('/S', '/ACCEPTTERMS', '/LANG=en_US', ("/D=" + $install))
Invoke-CheckedProcess $Setup $arguments
$exe = Join-Path $install 'StrigoiAetherMap.exe'
$seed = Get-Content -LiteralPath (Join-Path $data 'installation.json') -Raw | ConvertFrom-Json
if ($seed.default_language -ne 'en_US') { throw 'English installer seed missing.' }
if (-not (Get-ChildItem -LiteralPath $install -Recurse -Filter 'Qt6WebSockets.dll')) {
    throw 'Live Sync WebSocket runtime is missing.'
}
Invoke-CheckedProcess $exe @('--smoke-test')
$log = Get-Content -LiteralPath (Join-Path $data 'logs/strigoi.log') -Raw
if ($log -notmatch 'SMOKE_OK: all 15 pages rendered' -or $log -notmatch 'SMOKE_SIEGE_OK') {
    throw 'Application or Siege smoke test did not complete.'
}
$prefs = Join-Path $data 'preferences.json'
$preset = Join-Path $data 'siege-command.json'
$fixture = '{"schema_version":3,"selected_preset":"CI","presets":[{"schema_version":3,"map_id":"lower-reshanta","name":"CI","layers":["CustomMarkers"],"markers":[{"id":"local-ci","name":"CI fixture","position":{"x":0.2,"y":0.4}}],"drawings":[]}]}'
Set-Content -LiteralPath $preset -Value $fixture -Encoding utf8NoBOM
$before = (Get-FileHash -LiteralPath $prefs,$preset).Hash
Invoke-CheckedProcess $Setup $arguments
if (Compare-Object $before (Get-FileHash -LiteralPath $prefs,$preset).Hash) {
    throw 'Installer modified local preferences or presets.'
}
Invoke-CheckedProcess (Join-Path $install 'Uninstall.exe') @('/S')
for ($i = 0; $i -lt 60 -and ((Test-Path -LiteralPath $exe) -or (Test-Path -LiteralPath $registry)); $i++) {
    Start-Sleep -Milliseconds 500
}
if ((Test-Path -LiteralPath $exe) -or (Test-Path -LiteralPath $registry) -or (Test-Path -LiteralPath $uninstallRegistry)) {
    throw 'Uninstall left the executable or its registry entries.'
}
if (Compare-Object $before (Get-FileHash -LiteralPath $prefs,$preset).Hash) {
    throw 'Uninstall modified local preferences or presets.'
}
Write-Output 'Clean Windows install, launch, reinstall, uninstall, and user data preservation passed.'
