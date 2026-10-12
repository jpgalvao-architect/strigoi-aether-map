# SPDX-License-Identifier: GPL-3.0-only
param([string]$VsDevCmd = '')
$ErrorActionPreference = 'Stop'
$projectDirectory = Split-Path -Parent $PSScriptRoot
if (-not $VsDevCmd) {
    $vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
    $installation = & $vswhere -latest -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
    if (-not $installation) { throw 'Instale as ferramentas C++ do Visual Studio.' }
    $VsDevCmd = Join-Path $installation 'Common7\Tools\VsDevCmd.bat'
}
$binaryDirectory = Join-Path $projectDirectory 'app\assets\sonar'
New-Item -ItemType Directory -Path $binaryDirectory -Force | Out-Null
$objectDirectory = Join-Path $projectDirectory 'build\sonar'
New-Item -ItemType Directory -Path $objectDirectory -Force | Out-Null
$sourceFile = Join-Path $projectDirectory 'native\sonar_capture.cpp'
$exeFile = Join-Path $binaryDirectory 'sonar-capture.exe'
$objectFile = Join-Path $objectDirectory 'sonar_capture.obj'
$compileFile = Join-Path $objectDirectory 'compile.cmd'
$compileCommand = '@call "{0}" -arch=x64 -host_arch=x64 >nul{4}@if errorlevel 1 exit /b 1{4}@cl /nologo /std:c++17 /EHsc /O2 /MT /D_WIN32_WINNT=0x0A00 "{1}" /Fo"{2}" /Fe"{3}" /link Ole32.lib Mmdevapi.lib{4}' -f $VsDevCmd,$sourceFile,$objectFile,$exeFile,[Environment]::NewLine
Set-Content -LiteralPath $compileFile -Value $compileCommand -Encoding ascii
& $env:ComSpec /d /c $compileFile
if ($LASTEXITCODE -ne 0) { throw 'Falha ao compilar a captura de áudio.' }
