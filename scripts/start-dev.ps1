# start-dev.ps1 — podnosi środowisko dev Aura na Windows (baza, scheduler, API).
#
# Idempotentny: elementy, które już działają, zostawia w spokoju — można
# uruchamiać wielokrotnie. Pomyślany pod autostart po zalogowaniu
# (Harmonogram zadań, zadanie "AuraDev"), żeby restart maszyny nie oznaczał
# nocy bez scrapingu (scheduler musi być procesem trwałym — CLAUDE.md).
#
# Logi: %LOCALAPPDATA%\aura\ (start-dev.log, scheduler.err.log, uvicorn.err.log).
# Rejestracja autostartu (jednorazowo):
#   schtasks /Create /F /TN AuraDev /SC ONLOGON /RL LIMITED /TR
#     "powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File <repo>\scripts\start-dev.ps1"

$repo = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $repo "backend"
$python = Join-Path $backend ".venv\Scripts\python.exe"
$logDir = Join-Path $env:LOCALAPPDATA "aura"
New-Item -ItemType Directory -Force $logDir | Out-Null
$bootLog = Join-Path $logDir "start-dev.log"

function Log([string]$msg) {
    $line = "{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg
    Add-Content -Path $bootLog -Value $line
    Write-Output $line
}

Log "== start-dev: początek =="

# 1. Silnik Dockera — po starcie maszyny Docker Desktop wstaje długo (do kilku minut).
$deadline = (Get-Date).AddSeconds(300)
while ($true) {
    docker info *> $null
    if ($LASTEXITCODE -eq 0) { break }
    if ((Get-Date) -gt $deadline) { Log "BŁĄD: Docker nie wstał w 300 s — koniec"; exit 1 }
    Start-Sleep -Seconds 5
}
Log "Docker działa"

# 2. Kontener bazy (docker start jest idempotentny) + czekanie na gotowość Postgresa.
docker start aura-db-1 *> $null
if ($LASTEXITCODE -ne 0) { Log "BŁĄD: docker start aura-db-1 nie powiódł się — koniec"; exit 1 }
$deadline = (Get-Date).AddSeconds(60)
while ($true) {
    docker exec aura-db-1 pg_isready -U aura *> $null
    if ($LASTEXITCODE -eq 0) { break }
    if ((Get-Date) -gt $deadline) { Log "BŁĄD: Postgres niegotowy po 60 s — koniec"; exit 1 }
    Start-Sleep -Seconds 3
}
Log "Postgres przyjmuje połączenia"

# 3. Scheduler (nocny scraping) — dokładnie jeden egzemplarz.
$scheduler = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match "app\.scheduler" }
if ($scheduler) {
    Log ("scheduler już działa (PID {0})" -f ($scheduler | Select-Object -First 1).ProcessId)
} else {
    Start-Process -FilePath $python -ArgumentList "-u", "-m", "app.scheduler" `
        -WorkingDirectory $backend -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $logDir "scheduler.log") `
        -RedirectStandardError (Join-Path $logDir "scheduler.err.log")
    Log "scheduler wystartowany"
}

# 4. Backend API (uvicorn, port 8000).
$port = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($port) {
    Log "uvicorn już słucha na 8000"
} else {
    Start-Process -FilePath $python -ArgumentList "-u", "-m", "uvicorn", "app.main:app", "--port", "8000" `
        -WorkingDirectory $backend -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $logDir "uvicorn.log") `
        -RedirectStandardError (Join-Path $logDir "uvicorn.err.log")
    Log "uvicorn wystartowany"
}

Log "== start-dev: koniec =="
