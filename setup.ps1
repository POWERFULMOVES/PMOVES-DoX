# LMS Analyst - Quick Setup Script for Windows
# Run this script in PowerShell to set up both backend and frontend

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "LMS Analyst - Setup Script" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# Prepare sample fixtures
Write-Host "Preparing sample fixtures..." -ForegroundColor Yellow
$samples = Join-Path $PSScriptRoot 'samples'
if (-not (Test-Path $samples)) { New-Item -ItemType Directory -Path $samples | Out-Null }
if (-not (Test-Path (Join-Path $samples 'sample.csv'))) {
    @(
        'date,channel,spend,revenue,conversions,clicks,impressions',
        '2025-09-22,Search,1250.50,5200.00,85,4200,85000',
        '2025-09-23,Social,800.00,2100.00,30,3500,60000',
        '2025-09-24,Display,450.00,900.00,12,2100,120000',
        '2025-09-25,Search,1325.25,5400.00,90,4300,87000',
        '2025-09-26,Social,775.75,2300.00,35,3600,61000'
    ) | Set-Content -Path (Join-Path $samples 'sample.csv') -Encoding UTF8
}
if (-not (Test-Path (Join-Path $samples 'sample.pdf'))) {
    Write-Host "Downloading sample PDF..." -ForegroundColor Yellow
    try {
        Invoke-WebRequest -Uri "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf" -OutFile (Join-Path $samples 'sample.pdf') -UseBasicParsing
    } catch {
        Write-Host "Could not download sample PDF (network issue). You can still upload your own PDFs." -ForegroundColor DarkYellow
    }
}

# Check Python
Write-Host "Checking Python installation..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Python found: $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "✗ Python not found. Please install Python 3.10+ first." -ForegroundColor Red
    exit 1
}

# Check Node.js
Write-Host "Checking Node.js installation..." -ForegroundColor Yellow
$nodeVersion = node --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Node.js found: $nodeVersion" -ForegroundColor Green
} else {
    Write-Host "✗ Node.js not found. Please install Node.js first." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Setting up Backend..." -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan

# Setup Backend
Set-Location backend

Write-Host "Copying .env.example -> .env (if missing)..." -ForegroundColor Yellow
if (-not (Test-Path .env) -and (Test-Path .env.example)) { Copy-Item .env.example .env }

Write-Host "Creating virtual environment..." -ForegroundColor Yellow
python -m venv venv

Write-Host "Activating virtual environment..." -ForegroundColor Yellow
.\venv\Scripts\Activate.ps1

Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Backend dependencies installed successfully" -ForegroundColor Green
} else {
    Write-Host "✗ Failed to install backend dependencies" -ForegroundColor Red
    exit 1
}

Set-Location ..

Write-Host ""
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Setting up Frontend..." -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan

# Setup Frontend
Set-Location frontend

Write-Host "Copying .env.local.example -> .env.local (if missing)..." -ForegroundColor Yellow
if (-not (Test-Path .env.local) -and (Test-Path .env.local.example)) { Copy-Item .env.local.example .env.local }

Write-Host "Installing npm dependencies..." -ForegroundColor Yellow
npm install

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Frontend dependencies installed successfully" -ForegroundColor Green
} else {
    Write-Host "✗ Failed to install frontend dependencies" -ForegroundColor Red
    exit 1
}

Set-Location ..

Write-Host ""
Write-Host "==================================" -ForegroundColor Green
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Green
Write-Host ""
Write-Host "To start the application:" -ForegroundColor Cyan
Write-Host ""
Write-Host "Backend (Terminal 1):" -ForegroundColor Yellow
Write-Host "  cd backend" -ForegroundColor White
Write-Host "  .\venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "  python -m app.main" -ForegroundColor White
Write-Host ""
Write-Host "Frontend (Terminal 2):" -ForegroundColor Yellow
Write-Host "  cd frontend" -ForegroundColor White
Write-Host "  npm run dev" -ForegroundColor White
Write-Host ""
Write-Host "Then open http://localhost:3000 in your browser" -ForegroundColor Cyan
Write-Host ""
