# SPDX-License-Identifier: GPL-3.0-only
# Downloads from the publisher for this user; never redistributes Npcap.
param(
    [ValidateSet('pt_BR','en_US')][string]$Language='pt_BR',
    [switch]$CheckOnly,
    [switch]$VerifyOnly
)
$ErrorActionPreference='Stop'
function Test-NpcapAvailable {
    return (Test-Path -LiteralPath (Join-Path $env:SystemRoot 'System32\Npcap\wpcap.dll'))
}
if ($CheckOnly) {
    if (Test-NpcapAvailable) { Write-Output 'NPCAP_ALREADY_AVAILABLE'; exit 0 }
    Write-Output 'NPCAP_NOT_INSTALLED'; exit 42
}
if (-not $VerifyOnly -and (Test-NpcapAvailable)) { Write-Output 'NPCAP_ALREADY_AVAILABLE'; exit 0 }
$npcapUrl='https://npcap.com/dist/npcap-1.89.exe'
$npcapHash='8aed85e900d783d1308506e919587d3e540451947af8a82f2d04f819e44305cc'
$npcapTempBase=[IO.Path]::GetFullPath([IO.Path]::GetTempPath())
$npcapStage=[IO.Path]::GetFullPath((Join-Path $npcapTempBase ('strigoi-npcap-'+[Guid]::NewGuid().ToString('N'))))
if (-not $npcapStage.StartsWith($npcapTempBase,[StringComparison]::OrdinalIgnoreCase)) { throw 'Invalid staging directory' }
$npcapExe=Join-Path $npcapStage 'npcap-1.89.exe'
$npcapClient=$null
$npcapCancellation=[Threading.CancellationTokenSource]::new([TimeSpan]::FromSeconds(120))
$npcapResult=1
try {
    New-Item -ItemType Directory -Path $npcapStage | Out-Null
    Add-Type -AssemblyName System.Net.Http
    [Net.ServicePointManager]::SecurityProtocol=[Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    $npcapHandler=[Net.Http.HttpClientHandler]::new()
    $npcapHandler.AllowAutoRedirect=$false
    $npcapClient=[Net.Http.HttpClient]::new($npcapHandler)
    $npcapClient.Timeout=[TimeSpan]::FromSeconds(90)
    $npcapResponse=$npcapClient.GetAsync($npcapUrl,[Net.Http.HttpCompletionOption]::ResponseHeadersRead,$npcapCancellation.Token).GetAwaiter().GetResult()
    $npcapResponse.EnsureSuccessStatusCode() | Out-Null
    $npcapInput=$npcapResponse.Content.ReadAsStreamAsync().GetAwaiter().GetResult()
    $npcapOutput=[IO.File]::Create($npcapExe)
    try {
        $npcapChunk=New-Object byte[] 65536
        $npcapBytes=0
        while(($npcapRead=$npcapInput.ReadAsync($npcapChunk,0,$npcapChunk.Length,$npcapCancellation.Token).GetAwaiter().GetResult()) -gt 0) {
            $npcapBytes+=$npcapRead
            if ($npcapBytes -gt 33554432) { throw 'Download exceeds the component size limit' }
            $npcapOutput.Write($npcapChunk,0,$npcapRead)
        }
    } finally { $npcapOutput.Dispose(); $npcapInput.Dispose(); $npcapResponse.Dispose() }
    if ((Get-FileHash -LiteralPath $npcapExe -Algorithm SHA256).Hash.ToLowerInvariant() -ne $npcapHash) { throw 'Component hash does not match' }
    $npcapSignature=Get-AuthenticodeSignature -LiteralPath $npcapExe
    if ($npcapSignature.Status -ne 'Valid' -or $npcapSignature.SignerCertificate.Subject -notmatch '(?:^|, )O=Nmap Software LLC(?:,|$)') { throw 'Invalid publisher signature' }
    Write-Output 'NPCAP_DOWNLOAD_VERIFIED'
    if ($VerifyOnly) { $npcapResult=0 }
    else {
        # The user explicitly chose the publisher's visible installation wizard.
        # No /S, forced licence acceptance or changes to Npcap options.
        $npcapInstaller=Start-Process -FilePath $npcapExe -WindowStyle Normal -Wait -PassThru
        if ($npcapInstaller.ExitCode -eq 3010) { $npcapResult=3010 }
        elseif ($npcapInstaller.ExitCode -eq 0 -and (Test-NpcapAvailable)) { $npcapResult=0 }
        else { Write-Output 'NPCAP_INSTALL_NOT_COMPLETED'; $npcapResult=43 }
    }
} catch {
    Write-Output 'NPCAP_DOWNLOAD_OR_VERIFICATION_FAILED'
    $npcapResult=44
} finally {
    if ($npcapClient) { $npcapClient.Dispose() }
    $npcapCancellation.Dispose()
    # Only this invocation's individually named file and empty directory.
    if (Test-Path -LiteralPath $npcapExe) { Remove-Item -LiteralPath $npcapExe -Force }
    if (Test-Path -LiteralPath $npcapStage) { Remove-Item -LiteralPath $npcapStage }
}
exit $npcapResult
