# SPDX-License-Identifier: GPL-3.0-only
param(
    [int[]] $Participants = @(100, 250, 500, 750, 1000, 1500, 2000),
    [ValidateRange(1,8)] [int] $Generators = 4,
    [ValidateSet('abrupt','graceful')] [string] $Close = 'abrupt',
    [ValidateRange(1,25)] [int] $Stride = 5,
    [ValidateRange(1,3)] [int] $ReconnectAttempts = 3,
    [ValidateRange(1024,65535)] [int] $Port = 8990
)
$ErrorActionPreference = 'Stop'
$destination = Join-Path $PSScriptRoot ('.wrangler/load/' + [guid]::NewGuid())
New-Item -ItemType Directory -Path $destination -Force | Out-Null
$node = (Get-Command node).Source
$env:LIVE_SYNC_TEST_URL = "http://127.0.0.1:$Port"
$env:LIVE_SYNC_LOAD_CLOSE = $Close
$env:LIVE_SYNC_LOAD_STRIDE = "$Stride"
$env:LIVE_SYNC_LOAD_ATTEMPTS = "$ReconnectAttempts"
$env:WRANGLER_SEND_METRICS = 'false'
Push-Location $PSScriptRoot
try {
    & $node node_modules/wrangler/bin/wrangler.js deploy --dry-run --outdir .wrangler/bench-bundle
    if ($LASTEXITCODE) { throw 'The Worker bundle failed to build.' }
    foreach ($count in $Participants) {
        if ($count -notin @(100,250,500,750,1000,1500,2000)) { throw "Invalid scenario $count." }
        if (Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue) {
            throw "The benchmark port $Port is already in use."
        }
        $server = Start-Process -FilePath $node -ArgumentList @('serve-local.mjs', $Port) -WindowStyle Hidden -PassThru -RedirectStandardOutput "$destination/$count.server.log" -RedirectStandardError "$destination/$count.server.err"
        $workerId = $null
        try {
            for ($attempt = 0; $attempt -lt 30; $attempt++) {
                try {
                    $health = Invoke-RestMethod "$env:LIVE_SYNC_TEST_URL/v1/health" -TimeoutSec 2
                    if ($health.configured) { break }
                } catch {
                    if ($server.HasExited) { throw "Workerd exited. See $destination." }
                    Start-Sleep -Milliseconds 200
                }
            }
            if (-not $health.configured) { throw "Workerd failed its health check. See $destination." }
            $ownerId = (Get-NetTCPConnection -State Listen -LocalPort $Port).OwningProcess
            $worker = Get-Process -Id $ownerId
            if ($worker.ProcessName -ne 'workerd') { throw 'The listener does not belong to workerd.' }
            $parentId = (Get-CimInstance Win32_Process -Filter "ProcessId=$ownerId").ParentProcessId
            if ($parentId -ne $server.Id) { throw 'The listener does not belong to this benchmark.' }
            $workerId = $ownerId
            $baseline = $worker.CPU
            $maxHandles = $worker.HandleCount
            $client = Start-Process -FilePath $node -ArgumentList @('load.mjs', $count, $Generators) -WindowStyle Hidden -PassThru -RedirectStandardOutput "$destination/$count.load.json" -RedirectStandardError "$destination/$count.load.err"
            while (-not $client.WaitForExit(500)) {
                $maxHandles = [Math]::Max($maxHandles, (Get-Process -Id $workerId).HandleCount)
            }
            $worker = Get-Process -Id $workerId
            $result = Get-Content "$destination/$count.load.json" -Raw | ConvertFrom-Json -AsHashtable
            if (-not $result) { throw "No result for $count. See $destination." }
            $result.WorkerdCpuSeconds = [Math]::Round($worker.CPU - $baseline, 2)
            $result.WorkerdPeakRssMiB = [Math]::Round($worker.PeakWorkingSet64 / 1MB, 1)
            $result.WorkerdPeakSampledHandles = $maxHandles
            $result.LoadExitCode = $client.ExitCode
            $result | ConvertTo-Json -Depth 8 | Tee-Object -FilePath "$destination/$count.json"
        } finally {
            $health = $null
            if ($workerId) { Stop-Process -Id $workerId -ErrorAction SilentlyContinue }
            Stop-Process -Id $server.Id -ErrorAction SilentlyContinue
        }
    }
    Write-Output "Results: $destination"
} finally {
    Pop-Location
}
