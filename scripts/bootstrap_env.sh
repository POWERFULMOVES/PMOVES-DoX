#!/usr/bin/env bash
# PMOVES-DoX Environment Bootstrap
# Copies credentials from parent PMOVES.AI repo for standalone mode

set -euo pipefail

DOX_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_LOCAL="${DOX_ROOT}/.env.local"

echo "=== PMOVES-DoX Environment Bootstrap ==="
echo ""

# Possible parent locations (check multiple paths)
PARENT_PATHS=(
    "${DOX_ROOT}/../../PMOVES.AI/pmoves/.env"
    "${DOX_ROOT}/../PMOVES.AI/pmoves/.env"
    "$HOME/Documents/GitHub/PMOVES.AI/pmoves/.env"
    "$HOME/OneDrive/Documents/GitHub/PMOVES.AI/pmoves/.env"
    "/c/Users/russe/OneDrive/Documents/GitHub/PMOVES.AI/pmoves/.env"
)

PARENT_ENV=""
for path in "${PARENT_PATHS[@]}"; do
    if [[ -f "$path" ]]; then
        PARENT_ENV="$path"
        break
    fi
done

if [[ -n "$PARENT_ENV" ]]; then
    echo "Found parent PMOVES.AI environment: $PARENT_ENV"
    echo ""

    # Keys to copy from parent
    KEYS_TO_COPY=(
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

    echo "Copying credentials to .env.local..."
    for key in "${KEYS_TO_COPY[@]}"; do
        value=$(grep "^${key}=" "$PARENT_ENV" 2>/dev/null | head -1 | cut -d'=' -f2- || true)
        if [[ -n "$value" && "$value" != "" ]]; then
            # Remove existing key if present (use temp file for portability)
            grep -v "^${key}=" "$ENV_LOCAL" > "${ENV_LOCAL}.tmp" 2>/dev/null || true
            mv "${ENV_LOCAL}.tmp" "$ENV_LOCAL" 2>/dev/null || true
            echo "${key}=${value}" >> "$ENV_LOCAL"
            echo "  + ${key}"
        fi
    done
else
    echo "Parent PMOVES.AI environment not found"
    echo "Searched paths:"
    for path in "${PARENT_PATHS[@]}"; do
        echo "  - $path"
    done
    echo ""
    echo "Please manually add keys to .env.local"
    exit 1
fi

echo ""
echo "=== Validation ==="

# Source the env file safely
set +u
source "$ENV_LOCAL" 2>/dev/null || true
set -u

REQUIRED_KEYS=("HF_API_KEY")
OPTIONAL_KEYS=("OPENROUTER_API_KEY" "GOOGLE_API_KEY" "GEMINI_API_KEY")

echo "Required keys:"
MISSING=0
for key in "${REQUIRED_KEYS[@]}"; do
    val="${!key:-}"
    if [[ -z "$val" ]]; then
        echo "  [MISSING] $key"
        MISSING=$((MISSING + 1))
    else
        echo "  [OK] $key"
    fi
done

echo ""
echo "Optional keys:"
for key in "${OPTIONAL_KEYS[@]}"; do
    val="${!key:-}"
    if [[ -z "$val" ]]; then
        echo "  [--] $key (not set)"
    else
        echo "  [OK] $key"
    fi
done

echo ""
if [[ $MISSING -eq 0 ]]; then
    echo "Environment ready! Run: make standalone"
else
    echo "$MISSING required key(s) missing - some features may not work"
fi
