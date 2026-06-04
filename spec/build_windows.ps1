$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$SpecRoot = Join-Path $ProjectRoot 'spec'
$BuildRoot = Join-Path $SpecRoot 'build'
$DistRoot = Join-Path $SpecRoot 'dist'
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

New-Item -ItemType Directory -Force -Path $BuildRoot | Out-Null
New-Item -ItemType Directory -Force -Path $DistRoot | Out-Null

& $Python -m PyInstaller --noconfirm --clean --workpath $BuildRoot --distpath $DistRoot (Join-Path $SpecRoot 'MeowTool.spec')
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed with exit code $LASTEXITCODE"
}

Write-Host "Build complete: $(Join-Path $DistRoot 'MeowTool\MeowTool.exe')"
