#!/bin/bash
# PMOVES-DoX Enterprise Smoke Tests
# Tests all major integrations after enterprise readiness setup

set -e

PASSED=0
FAILED=0

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

test_pass() {
    echo -e "${GREEN}✓ $1${NC}"
    ((PASSED++))
}

test_fail() {
    echo -e "${RED}✗ $1${NC}"
    ((FAILED++))
}

test_info() {
    echo -e "${YELLOW}→ $1${NC}"
}

echo "=========================================="
echo "  PMOVES-DoX Enterprise Smoke Tests"
echo "=========================================="
echo ""

# ============================================================================
# Test 1: Backend API Health
# ============================================================================
test_info "Test 1: Backend API Health"
BACKEND_STATUS=$(curl -s http://localhost:8484/health)
if echo "$BACKEND_STATUS" | grep -q '"status":"ok"'; then
    UPTIME=$(echo "$BACKEND_STATUS" | grep -o 'uptime":[0-9.]*' | cut -d: -f2)
    test_pass "Backend API is healthy (uptime: ${UPTIME}s)"
else
    test_fail "Backend API health check failed"
fi

# ============================================================================
# Test 2: Backend OpenAPI/docs
# ============================================================================
test_info "Test 2: Backend API Documentation"
if curl -sf http://localhost:8484/docs > /dev/null 2>&1; then
    test_pass "Backend API docs available at /docs"
else
    test_fail "Backend API docs not accessible"
fi

# ============================================================================
# Test 3: TensorZero Health & ClickHouse Connectivity
# ============================================================================
test_info "Test 3: TensorZero Health & ClickHouse"
TZ_HEALTH=$(curl -s http://localhost:3000/health)
if echo "$TZ_HEALTH" | grep -q '"clickhouse":"ok"'; then
    test_pass "TensorZero connected to parent ClickHouse"
else
    test_fail "TensorZero ClickHouse connection failed"
fi

if echo "$TZ_HEALTH" | grep -q '"gateway":"ok"'; then
    test_pass "TensorZero gateway is healthy"
else
    test_fail "TensorZero gateway unhealthy"
fi

# ============================================================================
# Test 4: Ollama qwen3-embedding:8b Model
# ============================================================================
test_info "Test 4: Ollama qwen3-embedding:8b Model"
if docker exec pmoves-dox-ollama-1 ollama list | grep -q "qwen3-embedding:8b"; then
    MODEL_SIZE=$(docker exec pmoves-dox-ollama-1 ollama list | grep "qwen3-embedding:8b" | awk '{print $3}')
    test_pass "qwen3-embedding:8b available (${MODEL_SIZE})"
else
    test_fail "qwen3-embedding:8b not found in Ollama"
fi

# ============================================================================
# Test 5: Ollama Direct Embedding Test
# ============================================================================
test_info "Test 5: Ollama Direct Embedding Generation"
EMBEDDING=$(docker exec pmoves-dox-ollama-1 ollama run qwen3-embedding:8b "test" 2>/dev/null || echo "")
if [ -n "$EMBEDDING" ] && echo "$EMBEDDING" | grep -q "^\["; then
    EMBED_DIM=$(echo "$EMBEDDING" | jq 'length' 2>/dev/null || echo "0")
    if [ "$EMBED_DIM" = "4096" ]; then
        test_pass "Embedding generated with 4096 dimensions"
    else
        test_fail "Embedding dimension mismatch (got ${EMBED_DIM}, expected 4096)"
    fi
else
    test_fail "Failed to generate embedding via Ollama"
fi

# ============================================================================
# Test 6: Local DoX Supabase (PostgreSQL)
# ============================================================================
test_info "Test 6: Local DoX Supabase Connectivity"
if docker exec pmoves-dox-backend nc -z supabase-db 5432 2>/dev/null; then
    test_pass "Local Supabase (PostgreSQL) reachable from backend"
else
    test_fail "Local Supabase not reachable"
fi

# ============================================================================
# Test 7: Cipher Service
# ============================================================================
test_info "Test 7: Cipher Service MCP"
CIPHER_LOGS=$(docker logs pmoves-dox-cipher 2>&1)
if echo "$CIPHER_LOGS" | grep -q "API server is running"; then
    test_pass "Cipher service is running (MCP mode)"
else
    test_fail "Cipher service not running properly"
fi

# ============================================================================
# Test 8: Docker Network Connectivity (pmoves_data)
# ============================================================================
test_info "Test 8: Parent PMOVES.AI Network Connectivity"
if docker inspect pmoves-botz-tensorzero --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}' | grep -q "pmoves_data"; then
    test_pass "TensorZero connected to parent pmoves_data network"
else
    test_fail "TensorZero not on parent pmoves_data network"
fi

# ============================================================================
# Test 9: Parent ClickHouse Container
# ============================================================================
test_info "Test 9: Parent ClickHouse Container"
if docker inspect pmoves-tensorzero-clickhouse-1 > /dev/null 2>&1; then
    CH_STATUS=$(docker inspect pmoves-tensorzero-clickhouse-1 --format '{{.State.Status}}')
    test_pass "Parent ClickHouse container is ${CH_STATUS}"
else
    test_fail "Parent ClickHouse container not found"
fi

# ============================================================================
# Test 10: NATS Message Bus
# ============================================================================
test_info "Test 10: NATS Message Bus"
if docker exec pmoves-dox-nats nc -z localhost 4222 2>/dev/null; then
    test_pass "NATS is listening on port 4222"
else
    test_fail "NATS not accessible"
fi

# ============================================================================
# Test 11: Frontend Build
# ============================================================================
test_info "Test 11: Frontend Service"
if curl -sf http://localhost:3001 > /dev/null 2>&1; then
    test_pass "Frontend is accessible at port 3001"
else
    test_fail "Frontend not accessible"
fi

# ============================================================================
# Test 12: Docling MCP Service
# ============================================================================
test_info "Test 12: Docling MCP Service"
if docker logs pmoves-botz-docling 2>&1 | grep -q "docling_mcp_server"; then
    test_pass "Docling MCP service is running"
else
    test_fail "Docling MCP service not running"
fi

# ============================================================================
# Summary
# ============================================================================
echo ""
echo "=========================================="
echo "  Test Summary"
echo "=========================================="
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed! ✅${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed! ❌${NC}"
    exit 1
fi
