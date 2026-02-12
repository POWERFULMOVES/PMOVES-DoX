#!/usr/bin/env bash
# generate-service-docs.sh
#
# Generate standardized service documentation from docker-compose.yml
# Usage: ./scripts/generate-service-docs.sh <service-name> [--output <path>]
#        ./scripts/generate-service-docs.sh --list (list all services)
#        ./scripts/generate-service-docs.sh --all (generate for all services)

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATE="$PROJECT_ROOT/docs/templates/SERVICE_DOCUMENTATION_TEMPLATE.md"
OUTPUT_DIR="${OUTPUT_DIR:-$PROJECT_ROOT/docs/services}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if template exists
check_template() {
  if [[ ! -f "$TEMPLATE" ]]; then
    log_error "Template not found: $TEMPLATE"
    log_info "Run from project root or ensure docs/templates/ exists"
    exit 1
  fi
}

# Parse docker-compose.yml for service info
parse_service() {
  local service=$1
  local compose_file="$PROJECT_ROOT/docker-compose.yml"

  if [[ ! -f "$compose_file" ]]; then
    log_error "docker-compose.yml not found at $compose_file"
    exit 1
  fi

  # Extract service information using yq or grep
  log_info "Parsing service info for: $service"

  # Service name (title case)
  local title_name=$(echo "$service" | sed -r 's/(^|-)(\w)/\U\2/g')

  # Get image
  local image=$(docker compose config 2>/dev/null | grep -A 20 "  $service:" | grep "image:" | awk '{print $2}' || echo "unknown")

  # Get ports
  local ports=$(docker compose config 2>/dev/null | grep -A 50 "  $service:" | grep -A 5 "ports:" | grep "-" | awk '{print $2}' | tr '\n' ',' | sed 's/,$//' || echo "N/A")

  # Get networks
  local networks=$(docker compose config 2>/dev/null | grep -A 50 "  $service:" | grep -A 10 "networks:" | grep -E "^\s+-\s+[a-z]" | awk '{print $2}' | tr '\n' ',' | sed 's/,$//' || echo "N/A")

  # Export variables for template processing
  export SERVICE_NAME="$title_name"
  export SERVICE_NAME_LOWER="$service"
  export SERVICE_IMAGE="$image"
  export SERVICE_PORTS="$ports"
  export SERVICE_NETWORKS="$networks"
  export TODAY_DATE=$(date +%Y-%m-%d)
}

# Generate documentation for a single service
generate_docs() {
  local service=$1
  local output_dir="${2:-$OUTPUT_DIR}"
  local output="$output_dir/${service}.md"

  # Create output directory
  mkdir -p "$output_dir"

  # Parse service info
  parse_service "$service"

  # Check if file already exists
  if [[ -f "$output" ]]; then
    log_warning "File already exists: $output"
    read -p "Overwrite? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
      log_info "Skipping $service"
      return
    fi
  fi

  log_info "Generating documentation for: $service"

  # Copy template
  cp "$TEMPLATE" "$output"

  # Replace placeholders using sed (portable for Linux and macOS)
  # Use a temporary file for macOS compatibility
  local temp_file="${output}.tmp"

  # Simple placeholder replacements
  sed "s/{SERVICE_NAME}/$SERVICE_NAME/g" "$output" > "$temp_file"
  mv "$temp_file" "$output"

  sed "s/{service-name}/$SERVICE_NAME_LOWER/g" "$output" > "$temp_file"
  mv "$temp_file" "$output"

  sed "s/{VERSION}/latest/g" "$output" > "$temp_file"
  mv "$temp_file" "$output"

  sed "s/{DATE}/$TODAY_DATE/g" "$output" > "$temp_file"
  mv "$temp_file" "$output"

  sed "s/{STATUS}/stable/g" "$output" > "$temp_file"
  mv "$temp_file" "$output"

  # Add auto-generated info
  cat >> "$output" << 'EOF'

---
## Auto-Generated Information

*This section was auto-generated from docker-compose.yml. Please review and update.*

### Detected Configuration

| Field | Value |
|-------|-------|
| Service Name | `SERVICE_NAME_LOWER` |
| Docker Image | `SERVICE_IMAGE` |
| Ports | `SERVICE_PORTS` |
| Networks | `SERVICE_NETWORKS` |

EOF

  # Fix the auto-generated variables (portable sed)
  sed "s/SERVICE_NAME_LOWER/$SERVICE_NAME_LOWER/g" "$output" > "$temp_file"
  mv "$temp_file" "$output"

  sed "s|SERVICE_IMAGE|$SERVICE_IMAGE|g" "$output" > "$temp_file"
  mv "$temp_file" "$output"

  sed "s|SERVICE_PORTS|$SERVICE_PORTS|g" "$output" > "$temp_file"
  mv "$temp_file" "$output"

  sed "s|SERVICE_NETWORKS|$SERVICE_NETWORKS|g" "$output" > "$temp_file"
  mv "$temp_file" "$output"

  # Clean up temp file
  rm -f "$temp_file"

  log_success "Created: $output"
  echo ""
  log_info "Next steps:"
  echo "  1. Review and fill in remaining placeholders"
  echo "  2. Remove unused sections (e.g., NATS if not applicable)"
  echo "  3. Add API documentation and troubleshooting"
  echo "  4. Update auto-generated section if needed"
}

# List all services from docker-compose.yml
list_services() {
  local compose_file="$PROJECT_ROOT/docker-compose.yml"

  if [[ ! -f "$compose_file" ]]; then
    log_error "docker-compose.yml not found"
    exit 1
  fi

  log_info "Services in docker-compose.yml:"
  docker compose config --services 2>/dev/null | while read -r service; do
    echo "  - $service"
  done
}

# Show usage
usage() {
  cat << EOF
Usage: $(basename "$0") <service-name> [options]

Generate standardized service documentation from docker-compose.yml.

Arguments:
  <service-name>          Name of the service to document
  --list                  List all services in docker-compose.yml
  --all                   Generate documentation for all services
  --help, -h              Show this help message

Options:
  --output <path>         Output directory (default: docs/services)

Environment:
  OUTPUT_DIR              Override default output directory

Examples:
  # Generate docs for specific service
  $(basename "$0") agent-zero

  # List all available services
  $(basename "$0") --list

  # Generate docs for all services
  $(basename "$0") --all

  # Generate with custom output location
  $(basename "$0") tensorzero --output ./service-docs
EOF
}

# Main script logic
main() {
  check_template

  if [[ $# -eq 0 ]]; then
    usage
    exit 1
  fi

  local service=""
  local output_dir=""

  # Parse arguments
  while [[ $# -gt 0 ]]; do
    case $1 in
      --list)
        list_services
        exit 0
        ;;
      --all)
        log_info "Generating documentation for all services..."
        docker compose config --services 2>/dev/null | while read -r svc; do
          generate_docs "$svc" "$output_dir"
          echo ""
        done
        log_success "All service documentation generated"
        exit 0
        ;;
      --output)
        output_dir="$2"
        shift 2
        ;;
      --help|-h)
        usage
        exit 0
        ;;
      -*)
        log_error "Unknown option: $1"
        usage
        exit 1
        ;;
      *)
        service="$1"
        shift
        ;;
    esac
  done

  if [[ -n "$service" ]]; then
    # Validate service exists
    if ! docker compose config --services 2>/dev/null | grep -q "^${service}$"; then
      log_error "Service '$service' not found in docker-compose.yml"
      log_info "Run '$(basename "$0") --list' to see available services"
      exit 1
    fi

    generate_docs "$service" "$output_dir"
  else
    usage
    exit 1
  fi
}

main "$@"
