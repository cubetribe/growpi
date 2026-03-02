#!/bin/bash
# Test Script für Calendar API
# Usage: ./test_calendar_api.sh

BASE_URL="http://localhost:5000"
# Für Production: BASE_URL="http://your-growpi-host.example.com:5000"

echo "=========================================="
echo "Calendar API Test Script"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test 1: Get all grows
echo -e "${BLUE}Test 1: GET /api/calendar/grows${NC}"
curl -s "$BASE_URL/api/calendar/grows" | jq '.'
echo ""

# Test 2: Get active grows only
echo -e "${BLUE}Test 2: GET /api/calendar/grows?active_only=true${NC}"
curl -s "$BASE_URL/api/calendar/grows?active_only=true" | jq '.'
echo ""

# Test 3: Get demo grow details
echo -e "${BLUE}Test 3: GET /api/calendar/grows/demo-grow-001${NC}"
curl -s "$BASE_URL/api/calendar/grows/demo-grow-001" | jq '.'
echo ""

# Test 4: Get timeline for demo grow
echo -e "${BLUE}Test 4: GET /api/calendar/grows/demo-grow-001/timeline${NC}"
curl -s "$BASE_URL/api/calendar/grows/demo-grow-001/timeline" | jq '.'
echo ""

# Test 5: Get logs for demo grow
echo -e "${BLUE}Test 5: GET /api/calendar/grows/demo-grow-001/logs${NC}"
curl -s "$BASE_URL/api/calendar/grows/demo-grow-001/logs" | jq '.'
echo ""

# Test 6: Get specific log
echo -e "${BLUE}Test 6: GET /api/calendar/logs/demo-log-001${NC}"
curl -s "$BASE_URL/api/calendar/logs/demo-log-001" | jq '.'
echo ""

# Test 7: Get month view
CURRENT_MONTH=$(date +%Y-%m)
echo -e "${BLUE}Test 7: GET /api/calendar/month/$CURRENT_MONTH${NC}"
curl -s "$BASE_URL/api/calendar/month/$CURRENT_MONTH" | jq '.'
echo ""

# Test 8: Create new grow
echo -e "${BLUE}Test 8: POST /api/calendar/grows (Create new grow)${NC}"
NEW_GROW=$(curl -s -X POST "$BASE_URL/api/calendar/grows" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Grow API",
    "strain": "Test Strain",
    "start_date": "'$(date +%Y-%m-%d)'",
    "notes": "Created via API test"
  }')
echo "$NEW_GROW" | jq '.'
GROW_ID=$(echo "$NEW_GROW" | jq -r '.grow_id')
echo -e "${GREEN}Created grow ID: $GROW_ID${NC}"
echo ""

# Test 9: Create daily log for new grow
if [ "$GROW_ID" != "null" ] && [ -n "$GROW_ID" ]; then
  echo -e "${BLUE}Test 9: POST /api/calendar/logs (Create daily log)${NC}"
  NEW_LOG=$(curl -s -X POST "$BASE_URL/api/calendar/logs" \
    -H "Content-Type: application/json" \
    -d '{
      "grow_id": "'"$GROW_ID"'",
      "log_date": "'$(date +%Y-%m-%d)'",
      "watered": true,
      "water_amount_ml": 500,
      "notes": "First watering via API test"
    }')
  echo "$NEW_LOG" | jq '.'
  LOG_ID=$(echo "$NEW_LOG" | jq -r '.log_id')
  echo -e "${GREEN}Created log ID: $LOG_ID${NC}"
  echo ""

  # Test 10: Update daily log
  if [ "$LOG_ID" != "null" ] && [ -n "$LOG_ID" ]; then
    echo -e "${BLUE}Test 10: PUT /api/calendar/logs/$LOG_ID (Update log)${NC}"
    curl -s -X PUT "$BASE_URL/api/calendar/logs/$LOG_ID" \
      -H "Content-Type: application/json" \
      -d '{
        "notes": "Updated via API test",
        "water_amount_ml": 600,
        "fertilized": true,
        "fertilizer_type": "BioBizz Grow"
      }' | jq '.'
    echo ""

    # Test 11: Get updated log
    echo -e "${BLUE}Test 11: GET /api/calendar/logs/$LOG_ID (Verify update)${NC}"
    curl -s "$BASE_URL/api/calendar/logs/$LOG_ID" | jq '.'
    echo ""
  fi

  # Test 12: Change phase
  echo -e "${BLUE}Test 12: POST /api/calendar/grows/$GROW_ID/phase (Change phase)${NC}"
  curl -s -X POST "$BASE_URL/api/calendar/grows/$GROW_ID/phase" \
    -H "Content-Type: application/json" \
    -d '{
      "new_phase": "vegetative",
      "notes": "Phase change via API test"
    }' | jq '.'
  echo ""

  # Test 13: Get updated timeline
  echo -e "${BLUE}Test 13: GET /api/calendar/grows/$GROW_ID/timeline (Verify phase change)${NC}"
  curl -s "$BASE_URL/api/calendar/grows/$GROW_ID/timeline" | jq '.'
  echo ""

  # Cleanup: Delete test data
  echo -e "${BLUE}Cleanup: DELETE /api/calendar/grows/$GROW_ID${NC}"
  curl -s -X DELETE "$BASE_URL/api/calendar/grows/$GROW_ID" | jq '.'
  echo ""
fi

echo "=========================================="
echo -e "${GREEN}All tests completed!${NC}"
echo "=========================================="
