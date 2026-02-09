# LevelUp installer for Windows PowerShell — global (uv tool) or dev (venv + editable).
#
# Usage:
#   .\install.ps1              # Global install via uv tool
#   .\install.ps1 -Dev         # Dev install (venv + editable + dev deps)
#   .\install.ps1 -GUI         # Global install with GUI (PyQt6)
#   .\install.ps1 -Dev -GUI    # Dev install with GUI

param(
    [switch]$Dev,
    [switch]$GUI
)

$ErrorActionPreference = "Stop"

# ── Helpers ──────────────────────────────────────────────────────────────────
function Info($msg)  { Write-Host "==> $msg" -ForegroundColor Cyan }
function Ok($msg)    { Write-Host "==> $msg" -ForegroundColor Green }
function Err($msg)   { Write-Host "Error: $msg" -ForegroundColor Red }

# ── Check Python 3.11+ ──────────────────────────────────────────────────────
$PythonCmd = $null
foreach ($candidate in @("python", "python3")) {
    try {
        $ver = & $candidate -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        if ($ver) {
            $parts = $ver.Split(".")
            $major = [int]$parts[0]
            $minor = [int]$parts[1]
            if ($major -ge 3 -and $minor -ge 11) {
                $PythonCmd = $candidate
                break
            }
        }
    } catch {}
}

if (-not $PythonCmd) {
    Err "Python 3.11+ is required but not found."
    Write-Host "Install Python from https://www.python.org/downloads/"
    exit 1
}
$pyVersion = & $PythonCmd --version
Info "Using Python: $PythonCmd ($pyVersion)"

# ── Check uv ─────────────────────────────────────────────────────────────────
try {
    $uvVersion = & uv --version 2>$null
} catch {
    $uvVersion = $null
}

if (-not $uvVersion) {
    Err "uv is required but not found."
    Write-Host "Install uv: https://docs.astral.sh/uv/getting-started/installation/"
    Write-Host "  powershell -ExecutionPolicy ByPass -c `"irm https://astral.sh/uv/install.ps1 | iex`""
    exit 1
}
Info "Using uv: $uvVersion"

# ── Resolve source directory ─────────────────────────────────────────────────
$SourceDir = $PSScriptRoot
$LevelUpDir = Join-Path $env:USERPROFILE ".levelup"
$MetaFile = Join-Path $LevelUpDir "install.json"

if (-not (Test-Path $LevelUpDir)) {
    New-Item -ItemType Directory -Path $LevelUpDir -Force | Out-Null
}

# ── Detect git remote URL ───────────────────────────────────────────────────
$RepoUrl = $null
try {
    $RepoUrl = & git -C $SourceDir remote get-url origin 2>$null
    if ($LASTEXITCODE -ne 0) { $RepoUrl = $null }
} catch {
    $RepoUrl = $null
}

# ── Install ──────────────────────────────────────────────────────────────────
if ($Dev) {
    Info "Installing in dev mode (venv + editable)..."

    # Create venv if needed
    $VenvDir = Join-Path $SourceDir ".venv"
    if (-not (Test-Path $VenvDir)) {
        Info "Creating virtual environment..."
        & uv venv $VenvDir
    }

    $VenvPython = Join-Path $VenvDir "Scripts\python.exe"
    if (-not (Test-Path $VenvPython)) {
        # Try Unix-style path (e.g. Git Bash venv)
        $VenvPython = Join-Path $VenvDir "bin\python"
        if (-not (Test-Path $VenvPython)) {
            Err "Could not find Python in .venv"
            exit 1
        }
    }

    # Build extras string
    if ($GUI) {
        $Extras = ".[dev,gui]"
    } else {
        $Extras = ".[dev]"
    }

    Info "Installing: uv pip install -e `"$Extras`" ..."
    & uv pip install -e $Extras --python $VenvPython

    # Write install metadata
    $meta = @{
        method = "editable"
        source_path = $SourceDir
    }
    if ($GUI) { $meta["extras"] = @("gui") }
    if ($RepoUrl) { $meta["repo_url"] = $RepoUrl }
    $json = $meta | ConvertTo-Json
    [System.IO.File]::WriteAllText($MetaFile, $json)

    Ok "Dev install complete!"
    Write-Host ""
    Write-Host "Activate the virtual environment:"
    Write-Host "  $VenvDir\Scripts\Activate.ps1"
    Write-Host ""
    Write-Host "Then run:"
    Write-Host "  levelup --version"

} else {
    Info "Installing globally via uv tool..."

    # Build install target
    if ($GUI) {
        $InstallTarget = "$SourceDir[gui]"
    } else {
        $InstallTarget = $SourceDir
    }

    & uv tool install --force $InstallTarget --python $PythonCmd

    # Write install metadata
    $meta = @{
        method = "global"
        source_path = $SourceDir
    }
    if ($GUI) { $meta["extras"] = @("gui") }
    if ($RepoUrl) { $meta["repo_url"] = $RepoUrl }
    $json = $meta | ConvertTo-Json
    [System.IO.File]::WriteAllText($MetaFile, $json)

    Ok "Global install complete!"
    Write-Host ""
    Write-Host "Run from anywhere:"
    Write-Host "  levelup --version"
}
