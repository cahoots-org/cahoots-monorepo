#!/bin/bash

# Lightweight Validation Suite for Parameter Sweep
# Runs 1 representative test per complexity level (4 tests total)

API_URL="${API_URL:-http://localhost:8000/api/tasks}"
TOKEN="${TOKEN:-dev-bypass-token}"
REPORT_FILE="${REPORT_FILE:-/tmp/validation_report_light.json}"
MAX_WAIT_SECONDS="${MAX_WAIT_SECONDS:-300}"  # 5 minutes max per task

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Initialize report
echo "[]" > "$REPORT_FILE"

# Helper function to print colored messages
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Run a single test
run_test() {
    local category="$1"
    local name="$2"
    local description="$3"
    local context="$4"
    local expected_complexity="$5"
    local expected_min_tasks="$6"
    local expected_max_tasks="$7"

    print_status "$BLUE" "========================================"
    print_status "$BLUE" "TEST: $category/$name"
    print_status "$BLUE" "========================================"
    echo "Description: $description"
    echo "Expected complexity: $expected_complexity"
    echo "Expected tasks: $expected_min_tasks-$expected_max_tasks"
    echo ""

    # Create task
    START_TIME=$(date +%s)
    RESPONSE=$(curl -s -X POST "$API_URL" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $TOKEN" \
      -d "{\"description\": \"$description\", \"context\": $context}")

    TASK_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('data', {}).get('task_id', ''))" 2>/dev/null)

    if [ -z "$TASK_ID" ]; then
        print_status "$RED" "❌ FAILED: Could not create task"
        echo "$RESPONSE" | python3 -m json.tool 2>/dev/null

        # Add to report
        python3 << EOF
import json
with open('$REPORT_FILE', 'r') as f:
    report = json.load(f)
report.append({
    "category": "$category",
    "name": "$name",
    "description": "$description",
    "expected_complexity": "$expected_complexity",
    "expected_min_tasks": $expected_min_tasks,
    "expected_max_tasks": $expected_max_tasks,
    "task_id": None,
    "status": "failed_to_create",
    "duration_seconds": 0,
    "epics": 0,
    "stories": 0,
    "tasks": 0,
    "success": False,
    "error": "Could not create task"
})
with open('$REPORT_FILE', 'w') as f:
    json.dump(report, f, indent=2)
EOF
        return 1
    fi

    print_status "$GREEN" "✓ Task created: $TASK_ID"
    print_status "$YELLOW" "⏳ Waiting for processing (max ${MAX_WAIT_SECONDS}s)..."

    # Poll for completion
    POLL_INTERVAL=2
    MAX_ITERATIONS=$((MAX_WAIT_SECONDS / POLL_INTERVAL))

    for i in $(seq 1 $MAX_ITERATIONS); do
        sleep $POLL_INTERVAL
        STATUS_RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN" "$API_URL/$TASK_ID")
        STATUS=$(echo "$STATUS_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('data', {}).get('status', ''))" 2>/dev/null)

        if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
            break
        fi

        # Show progress every 10 iterations (20 seconds)
        if [ $((i % 10)) -eq 0 ]; then
            print_status "$YELLOW" "  Still waiting... (${i}s elapsed, status: $STATUS)"
        fi
    done

    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))

    # Get final task details
    FINAL_RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN" "$API_URL/$TASK_ID")

    # Parse response
    PARSED=$(python3 << EOF
import sys, json
try:
    data = json.loads('''$FINAL_RESPONSE''')
    task_data = data.get('data', {})
    print(json.dumps({
        'status': task_data.get('status', 'unknown'),
        'children_count': task_data.get('children_count', 0),
        'error_message': task_data.get('error_message', '')
    }))
except Exception as e:
    print(json.dumps({'status': 'parse_error', 'children_count': 0, 'error_message': str(e)}))
EOF
    )

    FINAL_STATUS=$(echo "$PARSED" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))")
    CHILDREN_COUNT=$(echo "$PARSED" | python3 -c "import sys, json; print(json.load(sys.stdin).get('children_count', 0))")
    ERROR_MSG=$(echo "$PARSED" | python3 -c "import sys, json; print(json.load(sys.stdin).get('error_message', ''))")

    # Determine success
    SUCCESS="false"
    if [ "$FINAL_STATUS" = "completed" ] && [ "$CHILDREN_COUNT" -ge "$expected_min_tasks" ] && [ "$CHILDREN_COUNT" -le "$expected_max_tasks" ]; then
        SUCCESS="true"
        print_status "$GREEN" "✅ PASSED: Task completed with $CHILDREN_COUNT children (expected $expected_min_tasks-$expected_max_tasks)"
    elif [ "$FINAL_STATUS" = "completed" ]; then
        print_status "$YELLOW" "⚠️  COMPLETED BUT OUT OF RANGE: Got $CHILDREN_COUNT tasks, expected $expected_min_tasks-$expected_max_tasks"
    else
        print_status "$RED" "❌ FAILED: Status=$FINAL_STATUS, Children=$CHILDREN_COUNT"
        if [ -n "$ERROR_MSG" ]; then
            echo "Error: $ERROR_MSG"
        fi
    fi

    echo "Duration: ${DURATION}s"
    echo ""

    # Add to report
    python3 << EOF
import json
with open('$REPORT_FILE', 'r') as f:
    report = json.load(f)
report.append({
    "category": "$category",
    "name": "$name",
    "description": "$description",
    "expected_complexity": "$expected_complexity",
    "expected_min_tasks": $expected_min_tasks,
    "expected_max_tasks": $expected_max_tasks,
    "task_id": "$TASK_ID",
    "status": "$FINAL_STATUS",
    "duration_seconds": $DURATION,
    "tasks": $CHILDREN_COUNT,
    "success": $SUCCESS,
    "error": "$ERROR_MSG"
})
with open('$REPORT_FILE', 'w') as f:
    json.dump(report, f, indent=2)
EOF

    if [ "$SUCCESS" = "true" ]; then
        return 0
    else
        return 1
    fi
}

# Print summary
print_summary() {
    print_status "$BLUE" "\n========================================\n"
    print_status "$BLUE" "VALIDATION SUMMARY\n"
    print_status "$BLUE" "========================================\n"

    python3 << EOF
import json
with open('$REPORT_FILE', 'r') as f:
    report = json.load(f)

total = len(report)
passed = sum(1 for r in report if r.get('success', False))
failed = total - passed

print(f"Total tests: {total}")
print(f"Passed: {passed}")
print(f"Failed: {failed}")
print(f"Success rate: {passed/total*100:.1f}%")
print()

if failed > 0:
    print("Failed tests:")
    for r in report:
        if not r.get('success', False):
            print(f"  - {r['category']}/{r['name']}: {r['status']} ({r.get('tasks', 0)} tasks)")
EOF
}

# Lightweight test suite - 1 test per complexity level
run_all_tests() {
    print_status "$GREEN" "\n🟢 ATOMIC TEST\n"
    run_test "atomic" "todo-app" \
        "Create a simple TODO list application with: Add new tasks with title and description, Mark tasks as complete/incomplete, Delete tasks, Filter by status (all, active, completed)" \
        '{"tech_stack": "React, Node.js"}' \
        "atomic" 1 10

    print_status "$YELLOW" "\n🟡 MEDIUM COMPLEXITY TEST\n"
    run_test "medium" "blog-platform" \
        "Build a blog platform with the following features: Authentication (User registration and login with email/password, JWT token-based authentication, Password reset via email), Content Management (Create, edit, delete blog posts, Rich text editor with markdown support, Draft and publish workflow, Featured images for posts, Categories and tags), Reader Features (Browse posts by category/tag, Search functionality, Commenting system for logged-in users only, Like/bookmark posts, RSS feed generation). Tech Stack: React, Node.js/Express, MongoDB" \
        '{"tech_stack": {"frontend": "React", "backend": "Node.js/Express", "database": "MongoDB"}}' \
        "medium" 10 30

    print_status "$RED" "\n🔴 COMPLEX TEST\n"
    run_test "complex" "marketplace" \
        "Build a full marketplace platform with: Multi-vendor system (vendors can register, create storefronts, list products), Product management (CRUD for products with multiple images, pricing, inventory, variants like size/color), Shopping cart and checkout (add to cart, apply discount codes, checkout with Stripe, order tracking), User accounts (buyers and sellers with different dashboards), Search and filtering (by category, price range, rating, location), Review and rating system (verified purchase reviews, photo reviews), Admin panel (approve vendors, manage categories, view analytics, handle disputes), Real-time notifications (order updates, new messages), Messaging system (buyers can contact sellers), Payment splits (platform fee + vendor payout via Stripe Connect). Tech Stack: Next.js, Node.js/Express, PostgreSQL, Redis for caching, AWS S3 for images, Stripe Connect, SendGrid" \
        '{"tech_stack": {"frontend": "Next.js", "backend": "Node.js/Express", "database": "PostgreSQL", "cache": "Redis", "storage": "AWS S3"}, "integrations": ["Stripe Connect", "SendGrid"]}' \
        "complex" 30 80

    print_status "$BLUE" "\n🔵 EPIC TEST\n"
    run_test "epic" "healthcare-system" \
        "Build a comprehensive healthcare management system with: Patient Portal (registration with personal and medical history, appointment scheduling with doctors, view test results and prescriptions, telemedicine video consultations, prescription refill requests, health tracking dashboard), Doctor Portal (manage availability and appointments, access patient records and history, write prescriptions electronically, order lab tests, video consultation interface, generate medical certificates and reports), Admin Dashboard (manage users (patients, doctors, staff), hospital/clinic management, inventory management for medicines and equipment, billing and insurance claims, analytics and reporting, appointment analytics), Pharmacy Module (receive electronic prescriptions, manage inventory, process insurance claims, delivery tracking), Lab Module (receive test orders, upload results, integrate with lab equipment, quality control workflows), Billing (invoice generation, insurance integration, payment processing with Stripe, automated reminders for unpaid bills), Compliance (HIPAA compliance for data privacy, audit logs for all data access, role-based access control, encrypted data storage and transmission), Notifications (SMS and email notifications for appointments, test results, prescription updates). Tech Stack: Next.js frontend, Python/FastAPI backend, PostgreSQL for structured data, MongoDB for medical records, Redis for caching, WebRTC for video calls, AWS S3 for medical documents, Stripe for payments, Twilio for SMS, SendGrid for email" \
        '{"tech_stack": {"frontend": "Next.js", "backend": "Python/FastAPI", "databases": ["PostgreSQL", "MongoDB"], "cache": "Redis", "storage": "AWS S3"}, "integrations": ["Stripe", "Twilio", "SendGrid", "WebRTC"]}' \
        "epic" 80 200

    print_summary
}

# Run based on argument
case "${1:-all}" in
    all)
        run_all_tests
        ;;
    *)
        echo "Usage: $0 [all]"
        echo "  all: Run all 4 tests (1 per complexity level)"
        exit 1
        ;;
esac
