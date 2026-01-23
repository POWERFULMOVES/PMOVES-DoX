# PMOVES-DoX Universal Credentials Bootstrap Script
# Loads credentials from multiple sources with precedence chain
#
# Precedence (highest to lowest):
#   1. Docker secrets (/run/secrets/) - container runtime
#   2. GitHub Actions secrets (env vars in CI)
#   3. CHIT Vault (HTTP API) - proprietary vault
#   4. Environment variables
#   5. Parent PMOVES.AI repo files (local dev fallback)
#
# Usage:
#   .\bootstrap_env.ps1                    # Auto-detect mode
#   .\bootstrap_env.ps1 -Mode local        # Force local dev mode
#   .\bootstrap_env.ps1 -Mode ci           # Force CI mode
#   .\bootstrap_env.ps1 -Mode docker       # Force Docker mode
#   .\bootstrap_env.ps1 -Validate          # Validate only, don't write

param(
    [ValidateSet("auto", "local", "ci", "docker")]
    [string]$Mode = "auto",
    [switch]$Validate,
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"

# =============================================================================
# Configuration
# =============================================================================

$DOX_ROOT = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$ENV_LOCAL = Join-Path $DOX_ROOT "PMOVES-DoX\.env.local"
$BACKEND_ENV = Join-Path $DOX_ROOT "PMOVES-DoX\backend\.env"

# CHIT Vault configuration
$CHIT_VAULT_ENDPOINT = $env:CHIT_VAULT_ENDPOINT
if (-not $CHIT_VAULT_ENDPOINT) { $CHIT_VAULT_ENDPOINT = "http://chit-vault:8050" }

# Docker secrets path (Linux containers)
$DOCKER_SECRETS_PATH = "/run/secrets"

# All managed credentials
$CREDENTIAL_KEYS = @(
    # LLM API Keys
    "OPENROUTER_API_KEY",
    "GOOGLE_API_KEY",
    "GEMINI_API_KEY",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    # Service API Keys
    "POSTMAN_API_KEY",
    "HF_API_KEY",
    "HUGGINGFACE_HUB_TOKEN",
    # Database
    "NEO4J_PASSWORD",
    "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_KEY",
    # TensorZero
    "TENSORZERO_PROVIDER_OPENROUTER_API_KEY",
    "GOOGLE_AI_STUDIO_API_KEY"
)

# Required for minimal operation
$REQUIRED_KEYS = @("OPENROUTER_API_KEY", "GOOGLE_API_KEY")

# Parent PMOVES.AI repo paths (local dev fallback)
$PARENT_PATHS = @(
    (Join-Path $DOX_ROOT "..\PMOVES.AI\pmoves\.env"),
    (Join-Path $DOX_ROOT "..\PMOVES.AI\pmoves\env.shared"),
    "$HOME\Documents\GitHub\PMOVES.AI\pmoves\.env",
    "$HOME\Documents\GitHub\PMOVES.AI\pmoves\env.shared",
    "$HOME\OneDrive\Documents\GitHub\PMOVES.AI\pmoves\.env",
    "$HOME\OneDrive\Documents\GitHub\PMOVES.AI\pmoves\env.shared"
)

# =============================================================================
# Helper Functions
# =============================================================================

function Write-Status {
    param([string]$Message, [string]$Color = "White")
    if ($Verbose -or $Color -eq "Red") {
        Write-Host $Message -ForegroundColor $Color
    }
}

function Detect-Mode {
    # Check for GitHub Actions
    if ($env:GITHUB_ACTIONS -eq "true") {
        return "ci"
    }
    # Check for Docker secrets path
    if (Test-Path $DOCKER_SECRETS_PATH -ErrorAction SilentlyContinue) {
        return "docker"
    }
    # Check for container indicators
    if ($env:KUBERNETES_SERVICE_HOST -or $env:DOCKER_CONTAINER) {
        return "docker"
    }
    return "local"
}

function Get-DockerSecret {
    param([string]$Key)
    $secretPath = Join-Path $DOCKER_SECRETS_PATH $Key.ToLower()
    if (Test-Path $secretPath -ErrorAction SilentlyContinue) {
        return (Get-Content $secretPath -Raw).Trim()
    }
    return $null
}

function Get-ChitVaultSecret {
    param([string]$Key)
    try {
        $response = Invoke-RestMethod -Uri "$CHIT_VAULT_ENDPOINT/secrets/$Key" -Method Get -TimeoutSec 5 -ErrorAction Stop
        if ($response.value) {
            return $response.value
        }
    } catch {
        Write-Status "  CHIT Vault unreachable for $Key" "Gray"
    }
    return $null
}

function Get-ParentEnvValue {
    param([string]$Key, [string]$ParentEnvPath)
    if (-not $ParentEnvPath) { return $null }

    $content = Get-Content $ParentEnvPath -ErrorAction SilentlyContinue
    if (-not $content) { return $null }

    $match = $content | Where-Object { $_ -match "^$Key=" }
    if ($match) {
        return ($match -split '=', 2)[1]
    }
    return $null
}

function Get-CredentialValue {
    param(
        [string]$Key,
        [string]$RuntimeMode,
        [string]$ParentEnvPath
    )

    $source = $null
    $value = $null

    # Priority 1: Docker secrets (container runtime)
    if ($RuntimeMode -eq "docker") {
        $value = Get-DockerSecret -Key $Key
        if ($value) { $source = "docker-secret"; return @{ Value = $value; Source = $source } }
    }

    # Priority 2: GitHub Actions secrets (exposed as env vars)
    if ($RuntimeMode -eq "ci" -or $RuntimeMode -eq "docker") {
        $envValue = [Environment]::GetEnvironmentVariable($Key)
        if ($envValue) { $source = "github-actions"; return @{ Value = $envValue; Source = $source } }
    }

    # Priority 3: CHIT Vault (proprietary)
    if ($RuntimeMode -ne "local") {
        $value = Get-ChitVaultSecret -Key $Key
        if ($value) { $source = "chit-vault"; return @{ Value = $value; Source = $source } }
    }

    # Priority 4: Environment variables
    $envValue = [Environment]::GetEnvironmentVariable($Key)
    if ($envValue) { $source = "env-var"; return @{ Value = $envValue; Source = $source } }

    # Priority 5: Parent PMOVES.AI repo (local dev fallback)
    if ($RuntimeMode -eq "local" -and $ParentEnvPath) {
        $value = Get-ParentEnvValue -Key $Key -ParentEnvPath $ParentEnvPath
        if ($value) { $source = "parent-repo"; return @{ Value = $value; Source = $source } }
    }

    return @{ Value = $null; Source = $null }
}

# =============================================================================
# Main Logic
# =============================================================================

Write-Host "=== PMOVES-DoX Universal Credentials Bootstrap ===" -ForegroundColor Cyan
Write-Host ""

# Detect runtime mode
$RuntimeMode = if ($Mode -eq "auto") { Detect-Mode } else { $Mode }
Write-Host "Runtime Mode: $RuntimeMode" -ForegroundColor Yellow

# Find parent env file (for local mode fallback)
$PARENT_ENV = $null
foreach ($path in $PARENT_PATHS) {
    if (Test-Path $path) {
        $PARENT_ENV = $path
        Write-Status "Parent env found: $path" "Gray"
        break
    }
}

Write-Host ""
Write-Host "=== Loading Credentials ===" -ForegroundColor Cyan

# Collect credentials
$credentials = @{}
$sources = @{}

foreach ($key in $CREDENTIAL_KEYS) {
    $result = Get-CredentialValue -Key $key -RuntimeMode $RuntimeMode -ParentEnvPath $PARENT_ENV

    if ($result.Value) {
        $credentials[$key] = $result.Value
        $sources[$key] = $result.Source
        Write-Host "  $key" -ForegroundColor Green -NoNewline
        Write-Host " ($($result.Source))" -ForegroundColor Gray
    } else {
        Write-Status "  $key not found" "Yellow"
    }
}

# Write to .env.local (unless validate-only)
if (-not $Validate -and $credentials.Count -gt 0) {
    Write-Host ""
    Write-Host "=== Writing Configuration ===" -ForegroundColor Cyan

    # Read existing .env.local
    $envLocalContent = if (Test-Path $ENV_LOCAL) {
        Get-Content $ENV_LOCAL | Where-Object { $_ -notmatch "^($($CREDENTIAL_KEYS -join '|'))=" }
    } else {
        @()
    }

    # Add credentials
    foreach ($key in $credentials.Keys) {
        $envLocalContent += "$key=$($credentials[$key])"
    }

    # Add source comments for debugging
    $envLocalContent += ""
    $envLocalContent += "# Credential sources (auto-generated):"
    foreach ($key in $sources.Keys) {
        $envLocalContent += "# $key <- $($sources[$key])"
    }

    # Write to file
    $envLocalContent | Set-Content $ENV_LOCAL
    Write-Host "Written to: $ENV_LOCAL" -ForegroundColor Green
}

# Validation
Write-Host ""
Write-Host "=== Validation ===" -ForegroundColor Cyan

$missing = 0
foreach ($key in $REQUIRED_KEYS) {
    if ($credentials.ContainsKey($key)) {
        Write-Host "  [OK] $key" -ForegroundColor Green
    } else {
        Write-Host "  [MISSING] $key" -ForegroundColor Red
        $missing++
    }
}

Write-Host ""
if ($missing -eq 0) {
    Write-Host "Environment ready!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  docker compose up -d" -ForegroundColor White
} else {
    Write-Host "$missing required credential(s) missing" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To resolve:" -ForegroundColor Cyan
    Write-Host "  1. Set environment variables directly" -ForegroundColor White
    Write-Host "  2. Add to parent PMOVES.AI repo .env" -ForegroundColor White
    Write-Host "  3. Configure CHIT Vault at $CHIT_VAULT_ENDPOINT" -ForegroundColor White
    Write-Host "  4. In CI: Add to GitHub repository secrets" -ForegroundColor White
    exit 1
}

# Summary
Write-Host ""
Write-Host "=== Summary ===" -ForegroundColor Cyan
Write-Host "  Total credentials: $($credentials.Count)/$($CREDENTIAL_KEYS.Count)" -ForegroundColor White
$sourceGroups = $sources.Values | Group-Object | Sort-Object Count -Descending
foreach ($group in $sourceGroups) {
    Write-Host "  From $($group.Name): $($group.Count)" -ForegroundColor Gray
}
