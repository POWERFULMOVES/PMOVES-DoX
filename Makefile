# PMOVES-DoX Makefile
# Common operations for development and deployment
#
# Usage:
#   make help          - Show available commands
#   make up            - Start services (standalone)
#   make up-docked     - Start services (docked mode)
#   make test          - Run all tests
#   make check-env     - Validate environment configuration

.PHONY: help up up-cpu up-gpu up-docked down build test lint check-env clean logs

# Default target
help:
	@echo "PMOVES-DoX Makefile Commands"
	@echo ""
	@echo "Development:"
	@echo "  make up          - Start services with GPU support"
	@echo "  make up-cpu      - Start services without GPU"
	@echo "  make up-docked   - Start in docked mode (PMOVES.AI integration)"
	@echo "  make down        - Stop all services"
	@echo "  make logs        - Tail service logs"
	@echo "  make build       - Build all Docker images"
	@echo ""
	@echo "Testing:"
	@echo "  make test        - Run backend and frontend tests"
	@echo "  make smoke       - Run smoke tests"
	@echo "  make lint        - Run linters"
	@echo ""
	@echo "Maintenance:"
	@echo "  make check-env   - Validate environment configuration"
	@echo "  make clean       - Remove build artifacts and volumes"
	@echo ""

# Service management
up:
	docker compose up -d

up-cpu:
	docker compose -f docker-compose.cpu.yml up -d

up-gpu:
	docker compose -f docker-compose.gpu.yml up -d

up-docked:
	@$(MAKE) check-env-docked
	docker compose -f docker-compose.docked.yml up -d

down:
	docker compose down
	docker compose -f docker-compose.cpu.yml down 2>/dev/null || true
	docker compose -f docker-compose.gpu.yml down 2>/dev/null || true
	docker compose -f docker-compose.docked.yml down 2>/dev/null || true

logs:
	docker compose logs -f

build:
	docker compose build

# Testing
test: test-backend test-frontend

test-backend:
	@echo "Running backend tests..."
	cd backend && python -m pytest -v

test-frontend:
	@echo "Running frontend tests..."
	cd frontend && npm test

smoke:
	@echo "Running smoke tests..."
	cd backend && python -m pip install -r ../smoke/requirements.txt -q
	python smoke/smoke_backend.py

lint: lint-backend lint-frontend

lint-backend:
	@echo "Linting backend..."
	cd backend && python -m ruff check . || true

lint-frontend:
	@echo "Linting frontend..."
	cd frontend && npm run lint || true

# Environment validation
check-env:
	@echo "Checking environment configuration..."
	@WARNINGS=0; \
	if [ ! -f ".env" ]; then \
		echo "WARNING: No .env file found. Copy .env.example to .env"; \
		WARNINGS=1; \
	fi; \
	if [ -f ".env" ]; then \
		echo "Checking required variables..."; \
		for var in COMPOSE_PROJECT_NAME; do \
			if ! grep -q "^$$var=" .env 2>/dev/null; then \
				echo "  WARNING: $$var not set"; \
				WARNINGS=1; \
			fi; \
		done; \
	fi; \
	if [ $$WARNINGS -eq 0 ]; then \
		echo "Environment check passed!"; \
	else \
		echo ""; \
		echo "Environment check completed with warnings."; \
		exit 1; \
	fi

check-env-docked:
	@echo "Checking docked mode environment..."
	@ERRORS=0; \
	if [ ! -f ".env" ]; then \
		echo "ERROR: No .env file found. Required for docked mode."; \
		exit 1; \
	fi; \
	for var in SUPABASE_URL SUPABASE_ANON_KEY DB_BACKEND; do \
		if ! grep -q "^$$var=" .env 2>/dev/null; then \
			echo "ERROR: Required variable $$var not set for docked mode"; \
			ERRORS=1; \
		fi; \
	done; \
	if [ $$ERRORS -ne 0 ]; then \
		echo ""; \
		echo "Docked mode requires additional environment variables."; \
		echo "See docs/DEPLOYMENT.md for configuration details."; \
		exit 1; \
	fi; \
	echo "Docked mode environment check passed!"

# Cleanup
clean:
	@echo "Cleaning up..."
	docker compose down -v --remove-orphans 2>/dev/null || true
	docker compose -f docker-compose.cpu.yml down -v --remove-orphans 2>/dev/null || true
	docker compose -f docker-compose.gpu.yml down -v --remove-orphans 2>/dev/null || true
	docker compose -f docker-compose.docked.yml down -v --remove-orphans 2>/dev/null || true
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".next" -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleanup complete"

# Database operations
migrate:
	@echo "Running database migrations..."
	docker compose exec backend python -c "from app.database import init_db; init_db()"

rebuild-index:
	@echo "Rebuilding search index..."
	curl -X POST http://localhost:8000/search/rebuild

# Health checks
health:
	@echo "Checking service health..."
	@curl -sf http://localhost:8000/health && echo "Backend: OK" || echo "Backend: DOWN"
	@curl -sf http://localhost:3000 && echo "Frontend: OK" || echo "Frontend: DOWN"
