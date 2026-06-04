$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$SpecRoot = Join-Path $ProjectRoot 'spec'
$BuildRoot = Join-Path $SpecRoot '.pyinstaller-build'
$DistRoot = Join-Path $SpecRoot '.pyinstaller-dist'
$FinalExe = Join-Path $SpecRoot 'MeowTool.exe'
$Python = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
$CargoBin = Join-Path $env:USERPROFILE '.cargo\bin'

if (-not (Test-Path $Python)) {
    throw ".venv Python not found: $Python"
}

$env:PATH = "$CargoBin;$env:PATH"

Push-Location (Join-Path $ProjectRoot 'native\http_engine')
& $Python -m maturin develop --release
if ($LASTEXITCODE -ne 0) {
    throw "maturin build failed with exit code $LASTEXITCODE"
}
Pop-Location

& $Python -m pip install pyinstaller
if ($LASTEXITCODE -ne 0) {
    throw "pyinstaller install failed with exit code $LASTEXITCODE"
}

if (Test-Path $BuildRoot) {
    Remove-Item -Recurse -Force $BuildRoot
}
if (Test-Path $DistRoot) {
    Remove-Item -Recurse -Force $DistRoot
}
if (Test-Path $FinalExe) {
    Remove-Item -Force $FinalExe
}

New-Item -ItemType Directory -Force -Path $BuildRoot | Out-Null
New-Item -ItemType Directory -Force -Path $DistRoot | Out-Null

& $Python -m PyInstaller --noconfirm --clean --workpath $BuildRoot --distpath $DistRoot (Join-Path $SpecRoot 'MeowTool.onefile.spec')
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller onefile build failed with exit code $LASTEXITCODE"
}

$BuiltExe = Join-Path $DistRoot 'MeowTool-onefile.exe'
if (-not (Test-Path $BuiltExe)) {
    throw "Built onefile exe not found: $BuiltExe"
}

Move-Item -Force $BuiltExe $FinalExe
Remove-Item -Recurse -Force $BuildRoot
Remove-Item -Recurse -Force $DistRoot

Write-Host "Build complete: $FinalExe"
