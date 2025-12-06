#!/bin/bash
#
# GrowPi Refactoring - Smoke Test Script
# Testet alle API Endpoints mit curl
#
# Usage: ./smoke_test.sh [base_url]
# Default: http://localhost:5000
#

set -e

BASE_URL="${1:-http://localhost:5000}"
PASS=0
FAIL=0

echo "=========================================="
echo "GrowPi API Smoke Tests"
echo "=========================================="
echo "Base URL: $BASE_URL"
echo ""

# Farben für Output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

test_endpoint() {
    local method=$1
    local endpoint=$2
    local description=$3
    local data=$4

    echo -n "Testing $method $endpoint ... "

    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" "$BASE_URL$endpoint")
    elif [ "$method" = "POST" ]; then
        response=$(curl -s -w "\n%{http_code}" -X POST -H "Content-Type: application/json" -d "$data" "$BASE_URL$endpoint")
    elif [ "$method" = "PUT" ]; then
        response=$(curl -s -w "\n%{http_code}" -X PUT -H "Content-Type: application/json" -d "$data" "$BASE_URL$endpoint")
    fi

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" -eq 200 ] || [ "$http_code" -eq 201 ]; then
        echo -e "${GREEN}✓ PASS${NC} (HTTP $http_code)"
        PASS=$((PASS + 1))
    else
        echo -e "${RED}✗ FAIL${NC} (HTTP $http_code)"
        echo "   Response: $body"
        FAIL=$((FAIL + 1))
    fi
}

echo "=== Health & Status Endpoints ==="
test_endpoint "GET" "/api/health" "Health check"
test_endpoint "GET" "/api/status" "System status"
test_endpoint "GET" "/api/temperature" "Temperature sensor"
echo ""

echo "=== Mode Management ==="
test_endpoint "GET" "/api/mode" "Get current mode"
# Nicht testen: POST /api/mode (würde Produktionssystem ändern)
echo ""

echo "=== Lamp Control ==="
# Nicht testen: POST /api/lamp/<ch> (würde Produktionssystem ändern)
echo "  (Skipped POST /api/lamp/* - würde Live-System ändern)"
echo ""

echo "=== Curves Management ==="
test_endpoint "GET" "/api/curves" "Get all curves"
test_endpoint "GET" "/api/curves/1" "Get curve channel 1"
test_endpoint "GET" "/api/curves/preview" "Get curve preview"
test_endpoint "GET" "/api/curves/intensities" "Get current intensities"
# Nicht testen: PUT /api/curves/<ch> (würde Produktionssystem ändern)
echo ""

echo "=== Logging Endpoints ==="
test_endpoint "GET" "/api/logs/sensors?hours=1&limit=10" "Get sensor logs"
test_endpoint "GET" "/api/logs/lamps?hours=1&limit=10" "Get lamp logs"
test_endpoint "GET" "/api/logs/events?hours=1&limit=10" "Get event logs"
test_endpoint "GET" "/api/logs/plugs?hours=1&limit=10" "Get plug logs"
test_endpoint "GET" "/api/logs/stats" "Get log statistics"
echo ""

echo "=========================================="
echo "Test Results:"
echo "=========================================="
echo -e "${GREEN}Passed: $PASS${NC}"
echo -e "${RED}Failed: $FAIL${NC}"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}✓ All smoke tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed!${NC}"
    exit 1
fi
