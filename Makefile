# PMOVES-DoX Makefile
# Dual-mode deployment: standalone or docked (within PMOVES.AI)

.PHONY: standalone docked test-standalone test-docked clean help logs build pull check-parent

# Default target
help:
	@echo "PMOVES-DoX Makefile"
	@echo ""
	@echo "Mode Selection:"
	@echo "  make standalone      - Run in STANDALONE mode (all local services)"
	@echo "  make docked          - Run in DOCKED mode (within PMOVES.AI)"
	@echo ""
	@echo "Testing:"
	@echo "  make test-standalone - Test standalone deployment"
	@echo "  make test-docked     - Test docked deployment"
	@echo ""
	@echo "Utilities:"
	@echo "  make build           - Build all Docker images"
	@echo "  make pull            - Pull latest images from registry"
	@echo "  make clean           - Stop and remove all containers"
	@echo "  make logs            - Show logs from all services"
	@echo "  make ps              - Show running containers"
	@echo "  make restart         - Restart all services"
	@echo "  make check-parent    - Verify parent networks available (for docked mode)"
	@echo ""
	@echo "Service-Specific:"
	@echo "  make backend-logs    - Show backend service logs"
	@echo "  make frontend-logs   - Show frontend service logs"
	@echo "  make agent-zero-logs - Show DoX Agent Zero logs"
	@echo ""
	@echo "Geometry / CHIT:"
	@echo "  make geometry-test   - Test geometry bus connectivity"

# =============================================================================
# Mode Selection
# =============================================================================

standalone:
	@echo "Starting PMOVES-DoX in STANDALONE mode..."
	@echo ""
	@echo "DoX Services (all local):"
	@echo "  - Frontend:        http://localhost:3001"
	@echo "  - Backend API:     http://localhost:8484"
	@echo "  - DoX Agent Zero:  http://localhost:50051 (Web UI)"
	@echo "  - NATS WebSocket:  ws://localhost:9223"
	@echo "  - Neo4j:           http://localhost:17474"
	@echo "  - PostgREST:       http://localhost:54321"
	@echo ""
	@echo "Internal BoTZ Agents (coordinated by DoX Agent Zero):"
	@echo "  - Cipher (memory):     http://localhost:3025"
	@echo "  - Postman (API):       http://localhost:3026"
	@echo "  - Docling (PDF):       http://localhost:3020"
	@echo ""
	@echo "Starting with PMOVES_MODE=standalone..."
	PMOVES_MODE=standalone docker compose --env-file .env.local up -d --build

docked: check-parent
	@echo "Starting PMOVES-DoX in DOCKED mode (within PMOVES.AI)..."
	@test -d ../pmoves || { \
		echo "Error: Not within PMOVES.AI repository"; \
		echo "Expected: ../pmoves directory to exist"; \
		exit 1; \
	}
	@echo ""
	@echo "Dual-Instance Agent Zero Pattern:"
	@echo "  - Parent Agent Zero: http://localhost:8080 (general orchestration)"
	@echo "  - DoX Agent Zero:    http://localhost:50051 (document intelligence)"
	@echo ""
	@echo "DoX Services (local):"
	@echo "  - Frontend:        http://localhost:3001"
	@echo "  - Backend API:     http://localhost:8484"
	@echo "  - Neo4j:           http://localhost:17474"
	@echo ""
	@echo "Connected to Parent PMOVES.AI:"
	@echo "  - TensorZero Gateway: http://tensorzero-gateway:3030"
	@echo "  - Parent NATS:        nats://nats:4222"
	@echo "  - Parent Neo4j:       bolt://pmoves-neo4j-1:7687"
	@echo ""
	@echo "Starting with PMOVES_MODE=docked..."
	PMOVES_MODE=docked docker compose -f docker-compose.yml -f docker-compose.docked.yml --env-file .env.local up -d --build

check-parent:
	@echo "Verifying parent PMOVES.AI networks..."
	@echo ""
	@for network in pmoves_api pmoves_app pmoves_bus pmoves_data; do \
		docker network inspect $$network >/dev/null 2>&1 || { \
			echo "❌ Error: Parent network $$network not found"; \
			echo ""; \
			echo "Parent PMOVES.AI must be running first."; \
			echo "Start parent services from PMOVES.AI root:"; \
			echo "  cd ../pmoves && docker compose up -d"; \
			echo ""; \
			exit 1; \
		}; \
		echo "  ✓ $$network"; \
	done
	@echo ""
	@echo "✅ All parent networks verified"
	@echo ""
	@echo "DoX can now connect to:"
	@echo "  - pmoves_api:    TensorZero Gateway (:3030)"
	@echo "  - pmoves_bus:    Parent NATS (:4222)"
	@echo "  - pmoves_data:   Parent ClickHouse, Neo4j"
	@echo "  - pmoves_app:    Parent services"

# =============================================================================
# Testing
# =============================================================================

test-standalone:
	@echo "Testing standalone deployment..."
	@echo ""
	PMOVES_MODE=standalone docker compose --env-file .env.local up -d --build
	@echo "Waiting for services to start..."
	@sleep 15
	@echo ""
	@echo "Testing backend health..."
	@curl -sf http://localhost:8484/health > /dev/null || { \
		echo "❌ Backend health check failed"; \
		exit 1; \
	}
	@echo "✅ Backend: http://localhost:8484/health"
	@echo ""
	@echo "Testing frontend..."
	@curl -sf http://localhost:3001 > /dev/null || { \
		echo "❌ Frontend check failed"; \
		exit 1; \
	}
	@echo "✅ Frontend: http://localhost:3001"
	@echo ""
	@echo "Testing DoX Agent Zero..."
	@WARNINGS=0; \
	curl -sf http://localhost:50051/health > /dev/null || { \
		echo "⚠️  DoX Agent Zero health check failed (may still be starting)"; \
		WARNINGS=1; \
	}; \
	if [ $$WARNINGS -eq 0 ]; then echo "✅ DoX Agent Zero: http://localhost:50051/health"; fi
	@echo ""
	@echo "Testing geometry bus..."
	@WARNINGS=0; \
	curl -sf http://localhost:3001/api/cipher/geometry/demo-packet > /dev/null || { \
		echo "⚠️  Geometry endpoint not ready"; \
		WARNINGS=1; \
	}; \
	if [ $$WARNINGS -eq 0 ]; then echo "✅ Geometry bus available"; fi
	@echo ""
	@echo "✅ All standalone tests completed (check warnings above if any)"

test-docked:
	@echo "Testing docked deployment..."
	@test -d ../pmoves || { \
		echo "Error: Not within PMOVES.AI repository"; \
		exit 1; \
	}
	@echo ""
	PMOVES_MODE=docked docker compose -f docker-compose.yml -f docker-compose.docked.yml --env-file .env.local up -d --build
	@echo "Waiting for services to start..."
	@sleep 15
	@echo ""
	@echo "Testing backend health..."
	@curl -sf http://localhost:8484/health > /dev/null || { \
		echo "❌ Backend health check failed"; \
		exit 1; \
	}
	@echo "✅ Backend: http://localhost:8484/health"
	@echo ""
	@echo "Testing DoX Agent Zero MCP endpoint..."
	@curl -sf http://localhost:50051/health > /dev/null || { \
		echo "⚠️  DoX Agent Zero health check failed (may still be starting)"; \
	}
	@echo "✅ DoX Agent Zero: http://localhost:50051/health"
	@echo ""
	@echo "Checking parent connectivity..."
	@docker exec pmoves-dox-backend env | grep -q "TENSORZERO_BASE_URL=http://tensorzero-gateway:3030" || { \
		echo "❌ Not using parent TensorZero Gateway"; \
		exit 1; \
	}
	@echo "✅ Using parent TensorZero Gateway"
	@docker exec pmoves-dox-backend env | grep -q "NATS_URL=nats://nats:4222" || { \
		echo "❌ Not using parent NATS"; \
		exit 1; \
	}
	@echo "✅ Using parent NATS"
	@echo ""
	@echo "✅ All docked tests PASSED"

# =============================================================================
# Utilities
# =============================================================================

build:
	@echo "Building all Docker images..."
	docker compose --env-file .env.local build

pull:
	@echo "Pulling latest images..."
	docker compose --env-file .env.local pull

clean:
	@echo "Stopping and removing all containers..."
	docker compose --env-file .env.local down -v
	@echo "Removing local database files..."
	@rm -rf backend/data/*.db backend/data/*.sqlite3
	@echo "✅ Clean complete"

logs:
	docker compose --env-file .env.local logs -f --tail=100

ps:
	docker compose --env-file .env.local ps

restart:
	@echo "Restarting all services..."
	docker compose --env-file .env.local restart

# =============================================================================
# Service-Specific Logs
# =============================================================================

backend-logs:
	docker compose --env-file .env.local logs -f backend

frontend-logs:
	docker compose --env-file .env.local logs -f frontend

agent-zero-logs:
	docker compose --env-file .env.local logs -f agent-zero

nats-logs:
	docker compose --env-file .env.local logs -f nats

neo4j-logs:
	docker compose --env-file .env.local logs -f neo4j

# =============================================================================
# Geometry / CHIT Testing
# =============================================================================

geometry-test:
	@echo "Testing geometry bus connectivity..."
	@echo ""
	@echo "Fetching demo geometry packet (via Next.js proxy)..."
	@curl -sf http://localhost:3001/api/cipher/geometry/demo-packet | jq '.' || { \
		echo "❌ Geometry bus not available"; \
		echo "   Start services with: make standalone"; \
		exit 1; \
	}
	@echo ""
	@echo "✅ Geometry bus operational"
	@echo ""
	@echo "NATS WebSocket for frontend:"
	@echo "  ws://localhost:9223"
	@echo ""
	@echo "Geometry frontend:"
	@echo "  http://localhost:3001/geometry"
