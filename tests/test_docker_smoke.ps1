$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "=== EKOS Docker Smoke Test ===" -ForegroundColor Cyan

Write-Host "Starting Docker Compose..." -ForegroundColor Yellow
docker compose up -d
if ($LASTEXITCODE -ne 0) { throw "docker compose up failed" }

try {
    Write-Host "Waiting for API to be ready..." -ForegroundColor Yellow
    $timeout = 60
    $elapsed = 0
    $ready = $false
    while ($elapsed -lt $timeout) {
        try {
            $resp = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5
            if ($resp.StatusCode -eq 200) { $ready = $true; break }
        } catch {}
        Start-Sleep -Seconds 2
        $elapsed += 2
    }
    if (-not $ready) { throw "API did not become ready within ${timeout}s" }
    Write-Host "API is healthy!" -ForegroundColor Green

    $health = Invoke-RestMethod -Uri "http://localhost:8000/health"
    if ($health.status -ne "ok") { throw "Health check returned: $($health.status)" }
    Write-Host "Health: status=$($health.status), version=$($health.version)" -ForegroundColor Green

    $loginResp = Invoke-RestMethod -Uri "http://localhost:8000/v1/auth/token" -Method Post `
        -ContentType "application/json" `
        -Body '{"email":"admin@test.com","password":"admin123"}'
    if (-not $loginResp.access_token) { throw "No access_token in login response" }
    Write-Host "Auth token obtained" -ForegroundColor Green

    $headers = @{ Authorization = "Bearer $($loginResp.access_token)" }
    $wsResp = Invoke-RestMethod -Uri "http://localhost:8000/v1/admin/workspaces" -Headers $headers
    Write-Host "Workspaces: $($wsResp | ConvertTo-Json -Compress)" -ForegroundColor Green

    Write-Host ""
    Write-Host "=== All smoke tests passed! ===" -ForegroundColor Green
} finally {
    Write-Host "Tearing down containers..." -ForegroundColor Yellow
    docker compose down -v
}
