# Evidrava Local Comprehensive Verification Script
# Runs all unit tests, design integrity checks, screening batch verification,
# predecessor report refresh, CLI smokes, and seed simulation.

$ErrorActionPreference = "Stop"

Write-Host "=== 1. Running Unit & Integration Tests (196 tests) ===" -ForegroundColor Cyan
& .\.venv-pilot\Scripts\python.exe -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw "Unit tests failed!" }

Write-Host "`n=== 2. Running Design Integrity Checker ===" -ForegroundColor Cyan
& .\.venv-design\Scripts\python.exe scripts/check_design.py
if ($LASTEXITCODE -ne 0) { throw "Design check failed!" }

Write-Host "`n=== 3. Verifying Screening Batch Integrity ===" -ForegroundColor Cyan
& .\.venv-pilot\Scripts\python.exe scripts/prepare_screening_batch.py --verify-existing
if ($LASTEXITCODE -ne 0) { throw "Screening batch verification failed!" }

Write-Host "`n=== 4. Verifying Predecessor Source Reports ===" -ForegroundColor Cyan
& .\.venv-pilot\Scripts\python.exe scripts/capture_predecessors.py --refresh-report pilot/sources/predecessors-2026-11-15
& .\.venv-pilot\Scripts\python.exe scripts/capture_predecessors.py --refresh-report pilot/sources/predecessors-supplement-2026-11-15
& .\.venv-pilot\Scripts\python.exe scripts/capture_predecessors.py --refresh-report pilot/sources/predecessors-date-supplement-2026-11-15
if ($LASTEXITCODE -ne 0) { throw "Predecessor reports verification failed!" }

Write-Host "`n=== 5. Running CLI Smoke Checks ===" -ForegroundColor Cyan
& .\.venv-pilot\Scripts\python.exe -m evidrava --help | Out-Null
& .\.venv-pilot\Scripts\python.exe -m evidrava check-workbook --help | Out-Null
& .\.venv-pilot\Scripts\python.exe -m evidrava frame-check --help | Out-Null
& .\.venv-pilot\Scripts\python.exe -m evidrava draw-sample --help | Out-Null
& .\.venv-pilot\Scripts\python.exe -m evidrava screening-queue --help | Out-Null
& .\.venv-pilot\Scripts\python.exe -m evidrava screening-report --help | Out-Null
& .\.venv-pilot\Scripts\python.exe -m evidrava simulate-seeds --help | Out-Null
& .\.venv-pilot\Scripts\python.exe -m evidrava check-market-data --help | Out-Null
Write-Host "All CLI smokes passed." -ForegroundColor Green

Write-Host "`n=== 6. Running Seed Sensitivity Simulation Smoke Check ===" -ForegroundColor Cyan
& .\.venv-pilot\Scripts\python.exe scripts/simulate_seeds.py --frame fixtures/frame/candidate-frame-synthetic.csv --target 4 --seeds 10
if ($LASTEXITCODE -ne 0) { throw "Seed simulation check failed!" }

Write-Host "`n=== 7. Running Market Data Validation Smoke Check ===" -ForegroundColor Cyan
$tmpMarket = "runs/smoke-market"
if (Test-Path $tmpMarket) { Remove-Item -Recurse -Force $tmpMarket }
& .\.venv-pilot\Scripts\python.exe -m evidrava check-market-data --data fixtures/market/sample_market_data.csv --out $tmpMarket
if ($LASTEXITCODE -ne 0) { throw "Market data smoke check failed!" }
Remove-Item -Recurse -Force $tmpMarket

Write-Host "`n>>> ALL VERIFICATIONS COMPLETED SUCCESSFULLY! <<<" -ForegroundColor Green
