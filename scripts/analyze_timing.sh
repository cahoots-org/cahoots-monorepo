#!/bin/bash

# Analyze timing from a single test run
# Usage: ./analyze_timing.sh <task_id>

TASK_ID=$1
API_URL="${API_URL:-http://localhost:8000/api/tasks}"
TOKEN="${TOKEN:-dev-bypass-token}"

if [ -z "$TASK_ID" ]; then
    echo "Usage: $0 <task_id>"
    exit 1
fi

echo "=== TIMING ANALYSIS FOR TASK: $TASK_ID ==="
echo ""

# Get task status
RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN" "$API_URL/$TASK_ID")

# Extract key metrics
echo "$RESPONSE" | python3 << 'EOF'
import sys
import json
from datetime import datetime

data = json.load(sys.stdin)
task_data = data.get('data', {})

created_at = task_data.get('created_at')
updated_at = task_data.get('updated_at')
status = task_data.get('status')

if created_at and updated_at:
    from dateutil import parser
    start = parser.parse(created_at)
    end = parser.parse(updated_at)
    duration = (end - start).total_seconds()
    print(f"Total Duration: {duration:.2f}s")
    print(f"Status: {status}")
    print(f"Created: {created_at}")
    print(f"Updated: {updated_at}")
else:
    print("Timing data not available")

# Count outputs
epics = task_data.get('epic_ids', [])
task_tree = task_data.get('task_tree', {})
impl_tasks = task_tree.get('implementation_tasks', [])

print(f"\nOutputs:")
print(f"  Epics: {len(epics)}")
print(f"  Implementation Tasks: {len(impl_tasks)}")

# Estimate LLM calls (rough)
print(f"\nEstimated LLM Calls:")
print(f"  Epic generation: 1")
print(f"  Story generation (per epic): {len(epics)}")
print(f"  Task decomposition (per story): ~{len(impl_tasks) // max(len(epics), 1)}")
print(f"  Event model validation: ~{len(impl_tasks)}")
total_llm_calls = 1 + len(epics) + len(impl_tasks) + len(impl_tasks)
print(f"  Total estimated: ~{total_llm_calls}")

if duration and total_llm_calls:
    avg_per_call = duration / total_llm_calls
    print(f"\nAvg time per LLM call: ~{avg_per_call:.2f}s")

EOF
