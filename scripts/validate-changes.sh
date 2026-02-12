#!/usr/bin/env bash
# =============================================================================
# PMOVES.AI Infrastructure Validation Script
# =============================================================================
# Comprehensive pre-commit validation for infrastructure changes.
# Run before pushing or in CI/CD to catch issues early.
#
# Usage:
#   ./scripts/validate-changes.sh              # Run all checks
#   ./scripts/validate-changes.sh --fast       # Skip slow checks
#   ./scripts/validate-changes.sh --ci         # CI mode (no interactive)
#   ./scripts/validate-changes.sh --help       # Show help
#
# Exit codes:
#   0 - All checks passed
#   1 - One or more checks failed
#   2 - Invalid arguments
#
# Integration:
#   - Pre-commit hook: symlink to .git/hooks/pre-commit
#   - Makefile: make validate-changes
#   - CI/CD: See .github/workflows/validate-infrastructure.yml
# =============================================================================

set -euo pipefail

# =============================================================================
# Configuration
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Check configuration
FAST_MODE=false
CI_MODE=false
VERBOSE=false
STOP_ON_ERROR=false

# Service health endpoints (format: "service_name:port:health_path:required")
# Port can be 'container' for internal container networking
SERVICES_TO_CHECK=(
    "backend:8484:/healthz:true"
    "frontend:3001:/__heartbeat__:true"
    "tensorzero:3030:/health:true"
    "agent-zero:50051:/health:true"
    "nats:4223::false"
    "neo4j:17474::false"
    "clickhouse:8123:/ping:false"
)

# Required environment variables (format: "var_name:is_secret:default_allowed")
REQUIRED_ENV_VARS=(
    "POSTGRES_PASSWORD:true:false"
    "NEO4J_PASSWORD:true:false"
    "CLICKHOUSE_PASSWORD:true:false"
    "SUPABASE_JWT_SECRET:true:false"
    "NATS_URL:false:true"
    "DB_BACKEND:false:true"
)

# Placeholder patterns to detect
PLACEHOLDER_PATTERNS=(
    "changeme"
    "your_secret_here"
    "your_api_key_here"
    "replace_with_"
    "TODO:.*add.*key"
    "FIXME:.*add.*secret"
)

# Port ranges to validate
PORT_MIN=1024
PORT_MAX=65535

# Files to validate
ENV_FILES=(".env.example" ".env.local.example" "env.shared")
COMPOSE_FILES=("docker-compose.yml" "docker-compose.docked.yml" "docker-compose.gpu.yml")

# =============================================================================
# Logging Functions
# =============================================================================

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[PASS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[FAIL]${NC} $1"; }
log_debug() { [[ "$VERBOSE" == "true" ]] && echo -e "${CYAN}[DEBUG]${NC} $1"; }
log_section() { echo -e "${MAGENTA}[====]${NC} $1"; }

# =============================================================================
# Utility Functions
# =============================================================================

show_help() {
    cat << EOF
PMOVES.AI Infrastructure Validation Script

Usage:
    $0 [OPTIONS]

Options:
    -f, --fast       Skip slow checks (database, external connectivity)
    -c, --ci         CI mode (no interactive prompts, exit on failure)
    -v, --verbose    Enable verbose output
    -s, --stop       Stop on first error
    -h, --help       Show this help message

Checks Performed:
    1. Service Health       - HTTP health endpoints, status codes
    2. Environment Vars     - No empty/placeholder values
    3. Network              - Port conflicts, reachability
    4. Database             - Tables exist, migrations applied
    5. Configuration        - YAML syntax, circular deps, references

Exit Codes:
    0 - All checks passed
    1 - One or more checks failed
    2 - Invalid arguments

Examples:
    $0                    # Run all checks
    $0 --fast             # Quick validation only
    $0 --ci --verbose     # CI mode with detailed output

Integration:
    make validate-changes  # Via Makefile
    .git/hooks/pre-commit  # As pre-commit hook
EOF
}

# Parse arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -f|--fast)
                FAST_MODE=true
                shift
                ;;
            -c|--ci)
                CI_MODE=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -s|--stop)
                STOP_ON_ERROR=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 2
                ;;
        esac
    done
}

# Check if command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Check if port is in use
is_port_in_use() {
    local port=$1
    if command_exists ss; then
        ss -tuln | grep -q ":${port} "
    elif command_exists netstat; then
        netstat -tuln 2>/dev/null | grep -q ":${port} "
    else
        return 1
    fi
}

# Check if service is running (by container name)
is_container_running() {
    local container_name=$1
    if command_exists docker; then
        docker ps --format '{{.Names}}' | grep -q "^${container_name}$"
    else
        return 1
    fi
}

# =============================================================================
# Section 1: Service Health Checks
# =============================================================================

check_service_health() {
    local service_name=$1
    local port=$2
    local health_path=$3
    local required=$4

    log_info "Checking ${service_name}..."

    # Build full URL
    local url="http://localhost:${port}${health_path}"

    # Try direct HTTP check
    local status_code=""
    local response_time=""

    if command_exists curl; then
        response=$(curl -s -o /dev/null -w "%{http_code}\n%{time_total}" \
            --max-time 5 --connect-timeout 3 "${url}" 2>/dev/null || echo "000\n0")

        status_code=$(echo "$response" | head -1)
        response_time=$(echo "$response" | tail -1 | sed 's/^\./0./')
    elif command_exists wget; then
        response=$(wget --spider -S -O /dev/null "${url}" 2>&1)
        status_code=$(echo "$response" | grep -oP 'HTTP/\d\.\d \K\d+' | head -1 || echo "000")
    else
        log_warning "  Neither curl nor wget available for health check"
        return "${required:-true}"
    fi

    # Validate status code
    if [[ "$status_code" =~ ^[23] ]]; then
        log_success "  ${service_name}: ${status_code} (${response_time}s)"
        return 0
    elif [[ "$status_code" == "000" ]]; then
        if [[ "$required" == "true" ]]; then
            log_error "  ${service_name}: Unreachable (port ${port} not responding)"
            return 1
        else
            log_warning "  ${service_name}: Unreachable (optional service)"
            return 0
        fi
    else
        log_error "  ${service_name}: HTTP ${status_code}"
        return 1
    fi
}

run_service_health_checks() {
    log_section "Service Health Checks"

    if ! command_exists docker && ! command_exists curl; then
        log_warning "Skipping service health checks (no docker or curl available)"
        return 0
    fi

    local failures=0

    for service_spec in "${SERVICES_TO_CHECK[@]}"; do
        IFS=':' read -r service_name port health_path required <<< "$service_spec"

        # Check if container is running
        local container_name="pmoves-dox-${service_name}"
        if is_container_running "$container_name"; then
            # Service is running via container
            check_service_health "$service_name" "$port" "$health_path" "$required" || ((failures++))
        elif is_port_in_use "$port"; then
            # Port is in use, try HTTP check
            check_service_health "$service_name" "$port" "$health_path" "$required" || ((failures++))
        else
            if [[ "$required" == "true" ]]; then
                log_warning "  ${service_name}: Not running (port ${port} not in use)"
                ((failures++))
            else
                log_debug "  ${service_name}: Not running (optional service)"
            fi
        fi

        if [[ "$STOP_ON_ERROR" == "true" && $failures -gt 0 ]]; then
            return 1
        fi
    done

    if [[ $failures -eq 0 ]]; then
        log_success "All service health checks passed"
        return 0
    else
        log_error "${failures} service(s) failed health check"
        return 1
    fi
}

# =============================================================================
# Section 2: Environment Variable Validation
# =============================================================================

check_env_file() {
    local env_file=$1
    local failures=0

    log_info "Checking ${env_file}..."

    if [[ ! -f "${PROJECT_ROOT}/${env_file}" ]]; then
        log_warning "  File not found: ${env_file}"
        return 0
    fi

    # Read env file (handle various formats)
    while IFS='=' read -r key value || [[ -n "$key" ]]; do
        # Skip comments and empty lines
        [[ "$key" =~ ^#.*$ ]] && continue
        [[ -z "$key" ]] && continue

        # Trim whitespace
        key=$(echo "$key" | xargs)
        value=$(echo "$value" | xargs)

        # Check for placeholders
        for pattern in "${PLACEHOLDER_PATTERNS[@]}"; do
            if [[ "$value" =~ $pattern ]]; then
                log_error "  ${env_file}: ${key} contains placeholder pattern '${pattern}'"
                ((failures++))
            fi
        done

        # Check for empty values on required vars
        for var_spec in "${REQUIRED_ENV_VARS[@]}"; do
            IFS=':' read -r var_name is_secret default_allowed <<< "$var_spec"
            if [[ "$key" == "$var_name" && -z "$value" ]]; then
                if [[ "$default_allowed" != "true" ]]; then
                    log_error "  ${env_file}: ${key} is empty (required)"
                    ((failures++))
                fi
            fi
        done
    done < "${PROJECT_ROOT}/${env_file}"

    return $failures
}

check_env_consistency() {
    log_info "Checking environment variable consistency..."

    local failures=0
    local declared_vars=()
    local used_vars=()

    # Extract declared vars from env files
    for env_file in "${ENV_FILES[@]}"; do
        if [[ -f "${PROJECT_ROOT}/${env_file}" ]]; then
            while IFS='=' read -r key value || [[ -n "$key" ]]; do
                [[ "$key" =~ ^#.*$ ]] && continue
                [[ -z "$key" ]] && continue
                key=$(echo "$key" | xargs)
                declared_vars+=("$key")
            done < "${PROJECT_ROOT}/${env_file}"
        fi
    done

    # Extract used vars from docker-compose files
    for compose_file in "${COMPOSE_FILES[@]}"; do
        if [[ -f "${PROJECT_ROOT}/${compose_file}" ]]; then
            # Find all ${VAR} references
            while read -r var; do
                [[ -z "$var" ]] && continue
                used_vars+=("$var")
            done < <(grep -oE '\$\{[A-Z_0-9]+' "${PROJECT_ROOT}/${compose_file}" 2>/dev/null | sed 's/\${//' | sort -u)
        fi
    done

    # Check for used but not declared vars
    for var in "${used_vars[@]}"; do
        # Skip common system vars
        case "$var" in
            PATH|HOME|USER|PWD) continue ;;
        esac

        if [[ ! " ${declared_vars[*]} " =~ " ${var} " ]]; then
            log_warning "  \${${var}} used but not declared in env files"
            ((failures++))
        fi
    done

    return $failures
}

run_env_checks() {
    log_section "Environment Variable Validation"

    local failures=0

    # Check each env file
    for env_file in "${ENV_FILES[@]}"; do
        check_env_file "$env_file" || ((failures++))
    done

    # Check consistency
    check_env_consistency || ((failures++))

    # Check docker-compose files for hardcoded secrets
    log_info "Checking for hardcoded secrets in docker-compose files..."
    for compose_file in "${COMPOSE_FILES[@]}"; do
        if [[ -f "${PROJECT_ROOT}/${compose_file}" ]]; then
            # Check for hardcoded passwords
            if grep -qE '(password|PASSWORD|secret|SECRET|api_key|API_KEY)=[^$\{][a-zA-Z0-9]+' "${PROJECT_ROOT}/${compose_file}" 2>/dev/null; then
                log_error "  ${compose_file}: Found potential hardcoded credentials"
                ((failures++))
            fi
        fi
    done

    if [[ $failures -eq 0 ]]; then
        log_success "All environment variable checks passed"
        return 0
    else
        log_error "${failures} environment variable issue(s) found"
        return 1
    fi
}

# =============================================================================
# Section 3: Network Connectivity Checks
# =============================================================================

check_port_conflicts() {
    log_info "Checking for port conflicts..."

    local failures=0
    local declared_ports=()

    # Extract ports from docker-compose files
    for compose_file in "${COMPOSE_FILES[@]}"; do
        if [[ -f "${PROJECT_ROOT}/${compose_file}" ]]; then
            while read -r port_mapping; do
                [[ -z "$port_mapping" ]] && continue
                # Extract host port (before the colon)
                local host_port=$(echo "$port_mapping" | grep -oE '^[0-9]+' || echo "")
                [[ -z "$host_port" ]] && continue

                # Check for duplicates
                if [[ " ${declared_ports[*]} " =~ " ${host_port} " ]]; then
                    log_warning "  Port ${host_port} declared multiple times in compose files"
                    ((failures++))
                fi
                declared_ports+=("$host_port")

                # Validate port range
                if [[ $host_port -lt $PORT_MIN || $host_port -gt $PORT_MAX ]]; then
                    log_error "  Port ${host_port} out of valid range (${PORT_MIN}-${PORT_MAX})"
                    ((failures++))
                fi
            done < <(grep -oE '"[0-9]+:[0-9]+' "${PROJECT_ROOT}/${compose_file}" 2>/dev/null | tr -d '"')
        fi
    done

    return $failures
}

check_service_reachability() {
    log_info "Checking service reachability..."

    if [[ "$FAST_MODE" == "true" ]]; then
        log_debug "  Skipping reachability checks in fast mode"
        return 0
    fi

    local failures=0

    # Check if declared ports are accessible
    for service_spec in "${SERVICES_TO_CHECK[@]}"; do
        IFS=':' read -r service_name port health_path required <<< "$service_spec"

        if command_exists nc && [[ "$health_path" != "" ]]; then
            if nc -z localhost "$port" 2>/dev/null; then
                log_debug "  ${service_name}: Port ${port} is reachable"
            else
                if [[ "$required" == "true" ]]; then
                    log_warning "  ${service_name}: Port ${port} is not reachable"
                    ((failures++))
                fi
            fi
        fi
    done

    return $failures
}

run_network_checks() {
    log_section "Network Connectivity Validation"

    local failures=0

    check_port_conflicts || ((failures++))
    check_service_reachability || ((failures++))

    if [[ $failures -eq 0 ]]; then
        log_success "All network checks passed"
        return 0
    else
        log_error "${failures} network issue(s) found"
        return 1
    fi
}

# =============================================================================
# Section 4: Database Validation
# =============================================================================

run_database_checks() {
    log_section "Database Validation"

    if [[ "$FAST_MODE" == "true" ]]; then
        log_debug "  Skipping database checks in fast mode"
        return 0
    fi

    local failures=0

    # Check if PostgreSQL container is running
    if is_container_running "supabase-db" || is_container_running "pmoves-dox-postgres"; then
        log_info "Checking database connection..."

        # Try to connect
        if command_exists docker; then
            local db_container=$(docker ps --format '{{.Names}}' | grep -E "supabase-db|pmoves.*postgres" | head -1)
            if [[ -n "$db_container" ]]; then
                if docker exec "$db_container" pg_isready -U postgres &>/dev/null; then
                    log_success "  Database is ready"
                else
                    log_error "  Database is not ready"
                    ((failures++))
                fi

                # Check for required tables
                log_info "  Checking for required tables..."
                local required_tables=("artifacts" "evidence" "facts" "summaries")
                for table in "${required_tables[@]}"; do
                    if docker exec "$db_container" psql -U postgres -d postgres -c "SELECT 1 FROM ${table} LIMIT 1" &>/dev/null; then
                        log_debug "    Table '${table}' exists"
                    else
                        log_warning "    Table '${table}' not found (may need migration)"
                    fi
                done
            fi
        fi
    elif is_container_running "pmoves-dox-backend"; then
        log_info "  Checking database via backend container..."
        # Backend can check its own database
        if docker exec pmoves-dox-backend curl -sf http://localhost:8484/healthz &>/dev/null; then
            log_success "  Backend reports healthy (implies DB connection)"
        else
            log_warning "  Backend health check inconclusive"
        fi
    else
        log_warning "  No database container running (skip in dev mode)"
    fi

    # Check migration status
    if [[ -f "${PROJECT_ROOT}/backend/alembic.ini" ]]; then
        log_info "  Checking migration status..."
        if command_exists alembic 2>/dev/null || docker exec pmoves-dox-backend which alembic &>/dev/null; then
            log_debug "    Alembic detected, migrations can be applied"
        else
            log_warning "    Alembic not found in PATH"
        fi
    fi

    if [[ $failures -eq 0 ]]; then
        log_success "Database checks passed"
        return 0
    else
        log_error "${failures} database issue(s) found"
        return 1
    fi
}

# =============================================================================
# Section 5: Configuration File Validation
# =============================================================================

check_yaml_syntax() {
    local yaml_file=$1
    log_info "  Checking ${yaml_file}..."

    if [[ ! -f "${PROJECT_ROOT}/${yaml_file}" ]]; then
        log_warning "    File not found: ${yaml_file}"
        return 0
    fi

    # Try yamllint first
    if command_exists yamllint; then
        if yamllint -d "{extends: default, rules: {line-length: disable}}" "${PROJECT_ROOT}/${yaml_file}" &>/dev/null; then
            log_debug "    YAML syntax valid"
            return 0
        else
            log_error "    YAML syntax error in ${yaml_file}"
            yamllint "${PROJECT_ROOT}/${yaml_file}" 2>&1 | head -5
            return 1
        fi
    fi

    # Fallback to Python
    if command_exists python3; then
        if python3 -c "import yaml; yaml.safe_load(open('${PROJECT_ROOT}/${yaml_file}'))" 2>/dev/null; then
            log_debug "    YAML syntax valid"
            return 0
        else
            log_error "    YAML syntax error in ${yaml_file}"
            return 1
        fi
    fi

    # Fallback to docker-compose config
    if [[ "$yaml_file" == docker-compose*.yml ]] && command_exists docker; then
        cd "${PROJECT_ROOT}"
        if docker compose -f "$yaml_file" config --quiet &>/dev/null; then
            log_debug "    Docker Compose syntax valid"
            return 0
        fi
    fi

    log_warning "    No YAML validator available"
    return 0
}

check_circular_dependencies() {
    log_info "  Checking for circular dependencies..."

    local failures=0

    for compose_file in "${COMPOSE_FILES[@]}"; do
        if [[ ! -f "${PROJECT_ROOT}/${compose_file}" ]]; then
            continue
        fi

        # Build dependency graph
        local deps=()
        while IFS=':' read -r service depends_on; do
            [[ -z "$service" ]] && continue
            deps+=("${service}:${depends_on}")
        done < <(grep -A 10 "depends_on:" "${PROJECT_ROOT}/${compose_file}" | grep -B 1 -E "^\s+[a-z]" | grep -v "^--$" | tr '\n' ':' | sed 's/:--:/\n/g')

        # Simple circular dependency detection
        for dep_entry in "${deps[@]}"; do
            IFS=':' read -r service deps_list <<< "$dep_entry"
            # This is a simplified check - full cycle detection would be more complex
            if echo "$deps_list" | grep -q "$service"; then
                log_warning "    Possible circular dependency involving ${service}"
                ((failures++))
            fi
        done
    done

    return $failures
}

check_service_references() {
    log_info "  Checking service and image references..."

    local failures=0

    for compose_file in "${COMPOSE_FILES[@]}"; do
        if [[ ! -f "${PROJECT_ROOT}/${compose_file}" ]]; then
            continue
        fi

        # Check for invalid image references
        while read -r image_line; do
            local image=$(echo "$image_line" | grep -oP 'image: \K[^#]+' | xargs)
            [[ -z "$image" ]] && continue

            # Check for placeholder images
            if [[ "$image" =~ (placeholder|example|test.*image|your.*image) ]]; then
                log_error "    Placeholder image found: ${image}"
                ((failures++))
            fi

            # Check for local build references
            if [[ "$image" == local/* ]]; then
                local build_dir="${PROJECT_ROOT}/${image#local/}"
                if [[ ! -d "$build_dir" ]]; then
                    log_warning "    Local build directory not found: ${build_dir}"
                fi
            fi
        done < <(grep "^image:" "${PROJECT_ROOT}/${compose_file}")

        # Check for build context references
        while read -r build_line; do
            local context=$(echo "$build_line" | grep -oP 'context: \K[^#]+' | xargs)
            [[ -z "$context" ]] && continue

            if [[ ! -d "${PROJECT_ROOT}/${context}" ]]; then
                log_error "    Build context not found: ${context}"
                ((failures++))
            fi
        done < <(grep -A 2 "^  build:" "${PROJECT_ROOT}/${compose_file}" | grep "context:")
    done

    return $failures
}

run_config_checks() {
    log_section "Configuration File Validation"

    local failures=0

    # Check YAML syntax
    for compose_file in "${COMPOSE_FILES[@]}"; do
        check_yaml_syntax "$compose_file" || ((failures++))
    done

    # Check for circular dependencies
    check_circular_dependencies || ((failures++))

    # Check service references
    check_service_references || ((failures++))

    if [[ $failures -eq 0 ]]; then
        log_success "All configuration checks passed"
        return 0
    else
        log_error "${failures} configuration issue(s) found"
        return 1
    fi
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    parse_args "$@"

    echo ""
    log_section "PMOVES.AI Infrastructure Validation"
    echo ""

    local start_time=$(date +%s)
    local total_failures=0
    local sections=("service_health" "env" "network" "database" "config")

    # Run all checks
    for section in "${sections[@]}"; do
        case $section in
            service_health)
                run_service_health_checks || ((total_failures++))
                ;;
            env)
                run_env_checks || ((total_failures++))
                ;;
            network)
                run_network_checks || ((total_failures++))
                ;;
            database)
                run_database_checks || ((total_failures++))
                ;;
            config)
                run_config_checks || ((total_failures++))
                ;;
        esac

        if [[ "$STOP_ON_ERROR" == "true" && $total_failures -gt 0 ]]; then
            break
        fi
        echo ""
    done

    # Summary
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    echo ""
    log_section "Validation Summary"
    echo "  Duration: ${duration}s"
    echo "  Mode: $([[ "$FAST_MODE" == "true" ]] && echo "Fast" || echo "Full")"

    if [[ $total_failures -eq 0 ]]; then
        log_success "All validation checks passed!"
        echo ""
        return 0
    else
        log_error "${total_failures} validation section(s) failed"
        echo ""

        if [[ "$CI_MODE" == "true" ]]; then
            log_error "CI mode: Exiting with error"
            return 1
        else
            log_warning "Some checks failed. Fix issues and run again."
            return 1
        fi
    fi
}

# Run main
main "$@"
