param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$buildPython = Join-Path $projectRoot 'work\desktop-build-env\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $buildPython)) {
    & $Python -m venv (Join-Path $projectRoot 'work\desktop-build-env')
    if ($LASTEXITCODE -ne 0) { throw 'Cannot create build environment.' }
}
& $buildPython -m ensurepip --upgrade --default-pip
if ($LASTEXITCODE -ne 0) { throw 'Cannot prepare build package manager.' }
& $buildPython -m pip install --disable-pip-version-check -r packaging/requirements-build.txt
if ($LASTEXITCODE -ne 0) { throw 'Cannot install build dependencies.' }
& $buildPython -m PyInstaller --noconfirm --distpath dist --workpath work/pyinstaller packaging/ChaoxingAI.spec
if ($LASTEXITCODE -ne 0) { throw 'Windows bundle build failed.' }
& $buildPython packaging/verify_windows.py
if ($LASTEXITCODE -ne 0) { throw 'Bundled executable verification failed.' }
& $buildPython packaging/package_release.py
if ($LASTEXITCODE -ne 0) { throw 'Release packaging failed.' }
