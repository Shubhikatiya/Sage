<#
.SYNOPSIS
    Start Sage with Ollama LLM backend.
    Updates .env with your Ollama URL and restarts the Sage backend.
#>

$ErrorActionPreference = "Stop"

# ─── Paths ────────────────────────────────────────────────────────────
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $ScriptDir "backend"
$EnvFile = Join-Path $BackendDir ".env"
$VenvPython = Join-Path $BackendDir "venv\Scripts\python.exe"

function Write-Info    { param($msg) Write-Host "[INFO]  $msg" -ForegroundColor Cyan }
function Write-Ok     { param($msg) Write-Host "[OK]    $msg" -ForegroundColor Green }
function Write-Warn   { param($msg) Write-Host "[WARN]  $msg" -ForegroundColor Yellow }
function Write-Error  { param($msg) Write-Host "[ERROR] $msg" -ForegroundColor Red }

Write-Info "Sage + Ollama Startup Script"
Write-Info "Backend dir: $BackendDir"

if (-not (Test-Path $VenvPython)) {
    Write-Error "Sage Python venv not found at: $VenvPython"
    Write-Error "Make sure you're running this from the 05_implementation directory."
    exit 1
}

# ─── Step 1: Get Ollama URL ───────────────────────────────────────────
Write-Info "Determining Ollama endpoint..."

$FinalOllamaUrl = ""

# Check if there's an existing OLLAMA_BASE_URL in .env
if (Test-Path $EnvFile) {
    $existingLines = Get-Content $EnvFile
    $existingUrlLine = $existingLines | Select-String "^OLLAMA_BASE_URL=(.+)"
    if ($existingUrlLine) {
        $existingUrl = $existingUrlLine.Matches.Groups[1].Value.Trim()
        if ($existingUrl -and ($existingUrl -notlike "#*")) {
            Write-Info "Found existing OLLAMA_BASE_URL in .env: $existingUrl"
            $response = Read-Host "Use this URL? (Y/n, or type a new URL)"
            if ($response -eq "" -or $response.ToLower() -eq "y" -or $response.ToLower() -eq "yes") {
                $FinalOllamaUrl = $existingUrl
            }
            elseif ($response -and ($response -notlike "n*")) {
                $FinalOllamaUrl = $response
            }
        }
    }
}

# If still no URL, prompt user
if (-not $FinalOllamaUrl) {
    Write-Host ""
    Write-Warn "No Ollama URL configured."
    Write-Info "Options:"
    Write-Host "  1. Enter your Ollama tunnel URL (e.g., https://xxx.ngrok-free.app)"
    Write-Host "  2. Enter http://localhost:11434 if Ollama is running locally"
    Write-Host ""
    $userUrl = Read-Host "Enter your Ollama URL"
    if (-not $userUrl) {
        Write-Error "No URL provided. Exiting."
        exit 1
    }
    $FinalOllamaUrl = $userUrl
}

Write-Ok "Using Ollama URL: $FinalOllamaUrl"

# ─── Step 2: Update .env ──────────────────────────────────────────────
Write-Info "Updating .env with Ollama URL..."

$EnvContent = @"
# Sage LLM Configuration
# OLLAMA IS THE PRIMARY PROVIDER
OLLAMA_BASE_URL=$FinalOllamaUrl
OLLAMA_MODEL=minimax

# Fallback providers (disabled so Ollama is always used)
# GROQ_API_KEY=
# ANTHROPIC_API_KEY=
# OPENAI_API_KEY=

LLM_PROVIDER=ollama
"@

Set-Content -Path $EnvFile -Value $EnvContent -Encoding UTF8
Write-Ok ".env updated"

# ─── Step 3: Stop existing Sage backend ───────────────────────────────
Write-Info "Stopping any existing Sage backend processes..."

Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {
    $_.Path -like "*sage-core*"
} | ForEach-Object {
    Stop-Process -Id $_.Id -Force
    Write-Ok "Stopped PID $($_.Id)"
}

Start-Sleep -Seconds 2

# Also kill any process using port 8000
$SagePort = 8000
$PortInUse = Get-NetTCPConnection -LocalPort $SagePort -ErrorAction SilentlyContinue | Select-Object -First 1
if ($PortInUse) {
    try {
        Stop-Process -Id $PortInUse.OwningProcess -Force
        Write-Ok "Killed process using port $SagePort"
        Start-Sleep -Seconds 2
    }
    catch { Write-Warn "Could not kill process on port $SagePort" }
}

# ─── Step 4: Start Sage v4 backend ───────────────────────────────────────
Write-Info "Starting Sage v4 backend on port $SagePort..."
Write-Info "This will take ~10-20 seconds for the embedding model to load."
Write-Host ""

Start-Process -FilePath $VenvPython `
    -ArgumentList "-m","uvicorn","main_v4:app","--host","0.0.0.0","--port",$SagePort `
    -WorkingDirectory $BackendDir

Start-Sleep -Seconds 3

# ─── Step 5: Wait for startup ─────────────────────────────────────────
Write-Info "Waiting for Sage backend to start..."
$maxWait = 60
$started = $false

for ($i = 0; $i -lt $maxWait; $i++) {
    try {
        $test = Invoke-RestMethod -Uri "http://localhost:$SagePort/api/debug" -TimeoutSec 2
        $started = $true
        break
    }
    catch { Start-Sleep -Seconds 1 }
}

if ($started) {
    Write-Ok "Sage backend is running on http://localhost:$SagePort"
    Write-Ok "Ollama URL: $FinalOllamaUrl"
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  SAGE + OLLAMA ARE READY" -ForegroundColor Green
    Write-Host "  Backend: http://localhost:$SagePort" -ForegroundColor Green
    Write-Host "  Ollama:  $FinalOllamaUrl" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Open your frontend and start chatting!" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Press any key to stop the backend..." -ForegroundColor Yellow
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

    # Stop backend on key press
    Write-Info "Stopping Sage backend..."
    Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {
        $_.Path -like "*sage-core*"
    } | ForEach-Object { Stop-Process -Id $_.Id -Force }
    Write-Ok "Sage backend stopped."
}
else {
    Write-Error "Sage backend failed to start within ${maxWait}s."
    Write-Error "Check the terminal output above for errors."
    exit 1
}
