#!/usr/bin/env bash
# =============================================================================
# PMOVES-DoX Environment Bootstrap (v5)
# =============================================================================
# Fetches credentials from multiple sources with active fetching support
#
# Full Documentation: ../../docs/SECRETS_MANAGEMENT.md
#
# MODES:
#   DOCKED MODE:   Loads from parent PMOVES.AI
#   STANDALONE:    Active Fetcher -> GitHub Secrets -> Parent -> Manual
#
# Usage: source scripts/bootstrap_env.sh    # Loads functions only
#        ./scripts/bootstrap_env.sh         # Runs full bootstrap
#
# Platforms: Linux, macOS, WSL2, Git Bash (Windows)
#
# Credential Sources (tried in order):
#   1. Active Fetcher - Python module calling GitHub/Docker APIs (new in v5)
#   2. GitHub Secrets - Environment variables in GitHub Actions/Codespaces
#   3. Parent PMOVES.AI - env.shared or .env (docked/standalone)
#   4. Manual setup - User creates .env.local manually
# =============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}ℹ${NC} $1"; }
log_success() { echo -e "${GREEN}✓${NC} $1"; }
log_warning() { echo -e "${YELLOW}⚠${NC} $1"; }
log_error() { echo -e "${RED}✗${NC} $1"; }
log_mode() { echo -e "${CYAN}▶${NC} $1"; }

DOX_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_LOCAL="${DOX_ROOT}/.env.local"
PARENT_REPO="${DOX_ROOT}/../PMOVES.AI"

log_mode "PMOVES-DoX Environment Bootstrap (v5)"
echo ""

# =============================================================================
# Detect Mode: Docked vs Standalone
# =============================================================================

is_docked_mode() {
    # Check if parent PMOVES.AI exists and has env files
    [[ -d "$PARENT_REPO" ]] && \
    [[ -f "$PARENT_REPO/pmoves/env.shared" || -f "$PARENT_REPO/pmoves/.env" ]]
}

# =============================================================================
# Load Credentials from Active Fetcher (via parent repo)
# =============================================================================

load_from_active_fetcher() {
    local output_file="${1:-.env.bootstrap}"

    log_info "Attempting active credential fetching..."

    # Check if parent repo has the credential fetcher
    local fetcher_module="${PARENT_REPO}/pmoves/tools/credential_fetcher.py"

    if [[ ! -f "$fetcher_module" ]]; then
        log_info "  Parent credential fetcher not found at: $fetcher_module"
        return 1
    fi

    # Check for GitHub credentials
    local github_owner="${GITHUB_OWNER:-POWERFULMOVES}"
    local github_repo="${GITHUB_REPO:-PMOVES-DoX}"
    local github_pat="${GITHUB_PAT:-}"

    if [[ -n "$github_pat" ]] || [[ -f "$HOME/.github-pat" ]]; then
        log_info "  GitHub credentials found - fetching from ${github_owner}/${github_repo}"
    fi

    # Execute the parent's credential fetcher
    local temp_output="${output_file}.active"

    if PYTHONPATH="${PARENT_REPO}:${PYTHONPATH:-}" python3 "$fetcher_module" fetch \
        --github-owner "$github_owner" \
        --github-repo "$github_repo" \
        --output "$temp_output" \
        ${GITHUB_PAT:+--github-token "$GITHUB_PAT"} \
        2>/dev/null; then

        # Merge with output
        if [[ -f "$temp_output" ]]; then
            local var_count=$(grep -c '^[A-Z_]=' "$temp_output" 2>/dev/null || echo "0")
            cat "$temp_output" >> "$output_file"
            rm -f "$temp_output"
            log_success "  Fetched $var_count credentials via active fetcher"
            return 0
        fi
    fi

    log_info "  Active fetcher completed but no credentials found"
    rm -f "$temp_output"
    return 1
}

# =============================================================================
# Load Credentials from GitHub Secrets (CI/CD env vars)
# =============================================================================

load_from_github_secrets() {
    local output_file="${1:-.env.bootstrap}"

    # Check if running in GitHub Actions or Codespaces
    if [[ -z "${GITHUB_ACTIONS:-}" ]] && [[ -z "${CODESPACES:-}" ]]; then
        return 1
    fi

    log_info "Loading from GitHub Secrets environment..."

    local secrets=(
        "OPENROUTER_API_KEY"
        "GOOGLE_API_KEY"
        "GEMINI_API_KEY"
        "ANTHROPIC_API_KEY"
        "OPENAI_API_KEY"
        "HF_API_KEY"
        "NEO4J_PASSWORD"
        "SUPABASE_ANON_KEY"
        "SUPABASE_SERVICE_KEY"
    )

    local found=0
    for secret in "${secrets[@]}"; do
        local value="${!secret:-}"
        if [[ -n "$value" ]]; then
            echo "${secret}=${value}" >> "$output_file"
            log_info "  Loaded $secret"
            ((found++))
        fi
    done

    if [[ $found -gt 0 ]]; then
        log_success "  Loaded $found credentials from GitHub Secrets"
        return 0
    else
        return 1
    fi
}

# =============================================================================
# Load Credentials from Parent PMOVES.AI
# =============================================================================

load_from_parent() {
    local parent_env="$1"

    if [[ ! -f "$parent_env" ]]; then
        return 1
    fi

    log_info "Loading from parent PMOVES.AI..."

    # Keys to copy from parent
    local keys_to_copy=(
        "OPENROUTER_API_KEY"
        "GOOGLE_API_KEY"
        "GEMINI_API_KEY"
        "POSTMAN_API_KEY"
        "HF_API_KEY"
        "ANTHROPIC_API_KEY"
        "OPENAI_API_KEY"
        "SUPABASE_ANON_KEY"
        "SUPABASE_SERVICE_KEY"
        "SUPABASE_SERVICE_ROLE_KEY"
        "SUPABASE_JWT_SECRET"
        "NEO4J_PASSWORD"
        "MEILI_MASTER_KEY"
        "DISCORD_WEBHOOK_URL"
    )

    local loaded=0
    for key in "${keys_to_copy[@]}"; do
        local value=$(grep "^${key}=" "$parent_env" 2>/dev/null | head -1 | cut -d'=' -f2- || true)
        if [[ -n "$value" && "$value" != "" ]]; then
            echo "${key}=${value}" >> "$ENV_LOCAL"
            log_info "  + ${key}"
            ((loaded++))
        fi
    done

    log_success "  Loaded $loaded credentials from parent"
    return 0
}

# =============================================================================
# Find Parent PMOVES.AI
# =============================================================================

find_parent_pmoves() {
    local parent_dirs=(
        "${DOX_ROOT}/../../PMOVES.AI"
        "${DOX_ROOT}/../PMOVES.AI"
        "$HOME/Documents/GitHub/PMOVES.AI"
        "$HOME/OneDrive/Documents/GitHub/PMOVES.AI"
        "/c/Users/russe/OneDrive/Documents/GitHub/PMOVES.AI"
    )

    for parent_dir in "${parent_dirs[@]}"; do
        if [[ -d "$parent_dir" ]]; then
            local env_file="${parent_dir}/pmoves/.env"
            local shared_file="${parent_dir}/pmoves/env.shared"

            if [[ -f "$env_file" ]] || [[ -f "$shared_file" ]]; then
                echo "$parent_dir"
                return 0
            fi
        fi
    done

    return 1
}

# =============================================================================
# Main Bootstrap Flow
# =============================================================================

main() {
    local output_file=".env.bootstrap"
    local source_used=""
    local temp_bootstrap="${DOX_ROOT}/.env.bootstrap.tmp"

    # STANDALONE MODE: Try multiple sources
    local sources_tried=()

    # 1. Try Active Fetcher FIRST (new in v5)
    if is_docked_mode; then
        log_mode "DOCKED MODE - Parent PMOVES.AI detected"
    else
        log_mode "STANDALONE MODE - trying Active Fetcher, GitHub Secrets, Parent"
    fi
    echo ""

    if load_from_active_fetcher "$temp_bootstrap"; then
        source_used="Active Fetcher"
        sources_tried+=("Active Fetcher: success")
    else
        sources_tried+=("Active Fetcher: failed (not configured)")
    fi

    # 2. Try GitHub Secrets
    if [[ ! -s "$temp_bootstrap" ]] || [[ $(grep -c '^' "$temp_bootstrap" 2>/dev/null || echo "0") -lt 2 ]]; then
        if load_from_github_secrets "$temp_bootstrap"; then
            source_used="${source_used:+$source_used + }GitHub Secrets"
            sources_tried+=("GitHub Secrets: success")
        else
            sources_tried+=("GitHub Secrets: skipped (not in GitHub environment)")
        fi
    fi

    # 3. Try Parent PMOVES.AI
    if [[ ! -s "$temp_bootstrap" ]] || [[ $(grep -c '^' "$temp_bootstrap" 2>/dev/null || echo "0") -lt 2 ]]; then
        local parent_dir="$(find_parent_pmoves)"
        if [[ -n "$parent_dir" ]]; then
            # Check for env.shared first, then .env
            local env_shared="${parent_dir}/pmoves/env.shared"
            local parent_env="${parent_dir}/pmoves/.env"

            if [[ -f "$env_shared" ]]; then
                log_info "Found parent env.shared at: $env_shared"
                load_from_parent "$env_shared"
                source_used="${source_used:+$source_used + }Parent (env.shared)"
                sources_tried+=("Parent env.shared: success")
            elif [[ -f "$parent_env" ]]; then
                log_info "Found parent .env at: $parent_env"
                load_from_parent "$parent_env"
                source_used="${source_used:+$source_used + }Parent (.env)"
                sources_tried+=("Parent .env: success")
            else
                sources_tried+=("Parent: not found")
            fi
        else
            sources_tried+=("Parent: not found")
        fi
    fi

    # Move temp file to final location
    if [[ -f "$temp_bootstrap" ]]; then
        mv "$temp_bootstrap" "$output_file"
    fi

    echo ""
    log_info "Sources tried: ${sources_tried[*]}"
    echo ""

    # Validate and report
    echo "=== Validation ==="

    if [[ -f "$output_file" ]]; then
        # Source the bootstrap file
        set +u
        source "$output_file" 2>/dev/null || true
        set -u

        local var_count=$(grep -c '^[A-Z_]=' "$output_file" 2>/dev/null || echo "0")
        log_success "Bootstrapped $var_count variables from: $source_used"
        echo ""

        # Merge into .env.local
        log_info "Merging into .env.local..."

        while IFS= read -r line; do
            [[ -z "$line" ]] && continue
            local key="${line%%=*}"
            local value="${line#*=}"

            # Remove existing key
            grep -v "^${key}=" "$ENV_LOCAL" > "${ENV_LOCAL}.tmp" 2>/dev/null || true
            mv "${ENV_LOCAL}.tmp" "$ENV_LOCAL" 2>/dev/null || touch "$ENV_LOCAL"
            echo "${key}=${value}" >> "$ENV_LOCAL"
        done < <(grep '^[A-Z_]=' "$output_file" 2>/dev/null)

        rm -f "$output_file"
    else
        log_error "No credentials found from any source"
        echo ""
        log_info "Manual setup required:"
        log_info "  1. Set GITHUB_PAT for active fetching"
        log_info "  2. Or set up parent PMOVES.AI credentials"
        log_info "  3. Or manually create .env.local with required keys"
        echo ""
        return 1
    fi

    # Check required keys
    echo ""
    echo "=== Required Keys Check ==="

    local required_keys=("HF_API_KEY")
    local optional_keys=("OPENROUTER_API_KEY" "GOOGLE_API_KEY" "GEMINI_API_KEY")
    local missing=0

    echo "Required:"
    for key in "${required_keys[@]}"; do
        local val="${!key:-}"
        if [[ -z "$val" ]]; then
            echo "  [MISSING] $key"
            ((missing++))
        else
            echo "  [OK] $key"
        fi
    done

    echo ""
    echo "Optional:"
    for key in "${optional_keys[@]}"; do
        local val="${!key:-}"
        if [[ -z "$val" ]]; then
            echo "  [--] $key"
        else
            echo "  [OK] $key"
        fi
    done

    echo ""
    if [[ $missing -eq 0 ]]; then
        log_success "Environment ready!"
        echo ""
        log_info "Next steps:"
        log_info "  make standalone    # Run DoX in standalone mode"
        log_info "  OR"
        log_info "  make dev            # Run with full PMOVES.AI stack (if available)"
        return 0
    else
        log_warning "$missing required key(s) missing"
        echo ""
        log_info "Some features may not work without required keys."
        return 0
    fi
}

# Run main if executed directly
if [[ "${BASH_SOURCE[0]}" = "${0}" ]]; then
    main "$@"
fi
