#!/bin/bash
# Test script for code generation
# Usage: ./scripts/test-codegen.sh <project_id>

set -e

PROJECT_ID="${1:-54d0065e-9c23-403e-9a18-3470c5290e04}"
API_URL="http://localhost:8000"
AUTH="Authorization: Bearer dev-bypass-token"

echo "=== Code Generation Test Script ==="
echo "Project ID: $PROJECT_ID"
echo ""

# Step 1: Clear generation state for this project
echo "Step 1: Clearing generation state..."
docker compose exec -T redis redis-cli DEL "generation:$PROJECT_ID" > /dev/null 2>&1 || true
echo "Done"
echo ""

# Step 2: Verify task exists
echo "Step 2: Verifying task exists..."
TASK_CHECK=$(curl -s "$API_URL/api/tasks/$PROJECT_ID" -H "$AUTH")
if echo "$TASK_CHECK" | grep -q "not found"; then
    echo "ERROR: Task $PROJECT_ID not found"
    exit 1
fi
echo "Task exists"
echo ""

# Step 3: Start code generation
echo "Step 3: Starting code generation..."
RESULT=$(curl -s -X POST "$API_URL/api/codegen/projects/$PROJECT_ID/generate" \
    -H "Content-Type: application/json" \
    -H "$AUTH" \
    -d '{"tech_stack": "nodejs-api"}')

echo "$RESULT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f'Status: {d.get(\"status\", \"error\")}')
print(f'Total slices: {d.get(\"total_slices\", 0)}')
if 'detail' in d:
    print(f'Error: {d[\"detail\"]}')
"
echo ""

# Step 4: Monitor progress
echo "Step 4: Monitoring progress (Ctrl+C to stop)..."
echo ""

while true; do
    STATUS=$(curl -s "$API_URL/api/codegen/projects/$PROJECT_ID/generate/status" -H "$AUTH")

    python3 -c "
import sys, json
d = json.loads('''$STATUS''')
s = d.get('status', '?')
p = d.get('progress_percent', 0)
c = d.get('completed_slices', 0)
t = d.get('total_slices', 0)
f = d.get('failed_slices', 0)
curr = d.get('current_slices', [])
err = d.get('last_error', '')

print(f'Status: {s} | Progress: {p:.0f}% | Completed: {c}/{t} | Failed: {f}')
if curr:
    print(f'  Working on: {len(curr)} slice(s)')
if err:
    print(f'  Last error: {err[:100]}...')

# Exit if done
if s in ('complete', 'failed', 'cancelled'):
    print('')
    print('=== Generation finished ===' if s == 'complete' else f'=== Generation {s} ===')
    sys.exit(0 if s == 'complete' else 1)
"

    PYEXIT=$?
    if [ $PYEXIT -ne 0 ] && [ $PYEXIT -ne 1 ]; then
        # Python parsing error, show raw
        echo "Raw: $STATUS"
    fi

    # Check if we should exit
    if echo "$STATUS" | grep -qE '"status":\s*"(complete|failed|cancelled)"'; then
        break
    fi

    sleep 10
done
