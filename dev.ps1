<#
    Runs both halves of the site together.

        .\dev.ps1

    Django serves the API on :8000, Vite serves the site on :5173 and proxies
    /api to it. Ctrl+C stops both — Django is started as a child process and
    torn down in the finally block, so it does not survive as an orphan the way
    it would if you had launched it in its own window.
#>
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'

if (-not (Test-Path $python)) {
    Write-Host "No virtualenv at $python" -ForegroundColor Red
    Write-Host "Create it first:  python -m venv .venv; .venv\Scripts\python -m pip install -r requirements.txt"
    exit 1
}

# A stale server on either port silently pushes Vite to 5174 while the old one
# keeps answering on 5173 with cached module transforms, which looks exactly
# like your edits not applying. Refuse to start rather than let that happen.
foreach ($port in 8000, 5173) {
    $busy = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($busy) {
        $procId = $busy[0].OwningProcess
        $name = (Get-Process -Id $procId -ErrorAction SilentlyContinue).ProcessName
        Write-Host "Port $port is already in use by $name (PID $procId)." -ForegroundColor Red
        Write-Host "Stop it first:  taskkill /PID $procId /F"
        exit 1
    }
}

$django = $null
try {
    Write-Host 'Starting Django on http://127.0.0.1:8000 ...' -ForegroundColor Cyan
    $django = Start-Process -FilePath $python `
        -ArgumentList 'manage.py', 'runserver', '8000' `
        -WorkingDirectory (Join-Path $root 'backend') `
        -NoNewWindow -PassThru

    # Vite proxies /api, so give Django a moment to bind before the first paint.
    Start-Sleep -Seconds 2
    if ($django.HasExited) {
        Write-Host "Django exited immediately (code $($django.ExitCode))." -ForegroundColor Red
        exit 1
    }

    Write-Host 'Starting Vite on http://localhost:5173 ...' -ForegroundColor Cyan
    Push-Location (Join-Path $root 'frontend')
    npm run dev
}
finally {
    Pop-Location -ErrorAction SilentlyContinue
    if ($django -and -not $django.HasExited) {
        Write-Host 'Stopping Django ...' -ForegroundColor Cyan
        # kill the tree: runserver's autoreloader spawns a child
        taskkill /PID $django.Id /T /F 2>&1 | Out-Null
    }
}
