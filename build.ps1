# Build yt-dlp GUI: single-file portable exe.
# Usage:  powershell -ExecutionPolicy Bypass -File build.ps1
#        powershell -ExecutionPolicy Bypass -File build.ps1 -NoVersionBump
param(
    [switch]$NoVersionBump
)
$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $project

$py = Join-Path $project '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) {
    Write-Host 'Creating virtual environment...'
    py -3 -m venv .venv
}

Write-Host 'Installing dependencies...'
& $py -m pip install --retries 20 --timeout 60 -r requirements.txt pyinstaller

Write-Host 'Checking bundled binaries...'
foreach ($f in @('bin\yt-dlp.exe', 'bin\ffmpeg.exe')) {
    if (-not (Test-Path $f)) { throw "Missing $f - put yt-dlp.exe and ffmpeg.exe into .\bin" }
}
if (-not (Test-Path 'bin\ffprobe.exe')) {
    Write-Warning 'bin\ffprobe.exe is missing - metadata/thumbnail post-processing will not work in the built app.'
}

if (-not $NoVersionBump) {
    Write-Host 'Bumping patch version...'
    & $py tools\bump_version.py --bump-patch
    if ($LASTEXITCODE -ne 0) {
        throw "Version bump failed with exit code $LASTEXITCODE"
    }
}

$version = (& $py -c "import version; print(version.APP_VERSION)").Trim()

Write-Host 'Building single-file portable exe...'
& $py -m PyInstaller --noconfirm --clean yt_dlp_gui.spec
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE - is the old exe still running?"
}

$exe = Join-Path $project "dist\yt-dlp-gui-portable-v$version.exe"
if (-not (Test-Path $exe)) { throw "Build output not found at $exe" }

Write-Host 'Running self-test...'
$test = Start-Process -FilePath $exe -ArgumentList '--self-test' -Wait -PassThru
if ($test.ExitCode -ne 0) { throw "Self-test failed with exit code $($test.ExitCode)" }
Write-Host ("Single-file: {0} ({1:N1} MiB)" -f $exe, ((Get-Item $exe).Length / 1MB))
