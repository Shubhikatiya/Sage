# Sage Development Starter
# Starts backend + frontend in one go

$backendPath = "c:\Users\katiy\OneDrive\Desktop\sage-core\05_implementation\backend"
$frontendPath = "c:\Users\katiy\OneDrive\Desktop\sage-core\05_implementation\frontend"

Write-Host "=== Starting Sage ===" -ForegroundColor Green

# Check if backend port is in use
$conn = Get-NetTCPConnection -LocalPort 8009 -ErrorAction SilentlyContinue
if ($conn) {
    Write-Host "Killing old backend (PID $($conn.OwningProcess))..." -ForegroundColor Yellow
    taskkill /F /PID $conn.OwningProcess 2>$null
    Start-Sleep 2
}

# Clear Python caches to avoid stale code
Remove-Item -Recurse -Force "$backendPath\__pycache__" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "$backendPath\services\__pycache__" -ErrorAction SilentlyContinue

# Start backend in a hidden window
Write-Host "Starting backend on http://localhost:8009 ..." -ForegroundColor Cyan
$backend = Start-Process -FilePath "$backendPath\venv\Scripts\python.exe" `
    -ArgumentList "-m", "uvicorn", "main:app", "--port", "8009" `
    -WorkingDirectory $backendPath `
    -WindowStyle Hidden -PassThru

# Wait for backend to be ready
Write-Host "Waiting for backend to start..." -NoNewline
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        $resp = Invoke-WebRequest -Uri "http://localhost:8009/health" -Method GET -TimeoutSec 2 -ErrorAction Stop
        if ($resp.StatusCode -eq 200) {
            $ready = $true
            break
        }
    } catch {
        Start-Sleep 1
        Write-Host "." -NoNewline
    }
}
Write-Host ""

if (-not $ready) {
    Write-Host "Backend failed to start. Check terminal for errors." -ForegroundColor Red
    exit 1
}

Write-Host "Backend ready!" -ForegroundColor Green

# Start frontend dev server
Write-Host "Starting frontend dev server..." -ForegroundColor Cyan
$frontend = Start-Process -FilePath "cmd" `
    -ArgumentList "/c", "cd /d `"$frontendPath`" && npx vite --port 5173" `
    -WorkingDirectory $frontendPath `
    -WindowStyle Hidden -PassThru

Write-Host "Opening browser..." -ForegroundColor Cyan
Start-Process "http://localhost:5173"

Write-Host ""
Write-Host "=== Sage is running ===" -ForegroundColor Green
Write-Host "Backend:  http://localhost:8009" -ForegroundColor Gray
Write-Host "Frontend: http://localhost:5173" -ForegroundColor Gray
Write-Host ""
Write-Host "Press any key to stop both servers..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# Cleanup
Write-Host "Stopping servers..." -ForegroundColor Yellow
Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
Stop-Process -Id $frontend.Id -Force -ErrorAction SilentlyContinue
Write-Host "Sage stopped." -ForegroundColor Green
