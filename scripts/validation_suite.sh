#!/bin/bash

# Validation Suite v2 for Cahoots - Full Project Generation Testing
# Tests prompts from EXAMPLE_PROMPTS.md

API_URL="${API_URL:-http://localhost:8000/api/tasks}"
TOKEN="${TOKEN:-dev-bypass-token}"
REPORT_FILE="${REPORT_FILE:-/tmp/validation_report_v2.json}"
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

        ELAPSED=$((i * POLL_INTERVAL))
        echo "  Status: $STATUS (${ELAPSED}s elapsed)"
    done

    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))

    # Get final results
    FINAL=$(curl -s -H "Authorization: Bearer $TOKEN" "$API_URL/$TASK_ID")

    # Extract metrics
    CHILDREN=$(echo "$FINAL" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('data', {}).get('children_count', 0))" 2>/dev/null)
    FINAL_STATUS=$(echo "$FINAL" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('data', {}).get('status', ''))" 2>/dev/null)

    # Count epics and stories
    EPICS=$(echo "$FINAL" | python3 -c "import sys, json; d=json.load(sys.stdin); ctx=d.get('data', {}).get('context', {}); print(len(ctx.get('epics', [])))" 2>/dev/null)
    STORIES=$(echo "$FINAL" | python3 -c "import sys, json; d=json.load(sys.stdin); ctx=d.get('data', {}).get('context', {}); print(len(ctx.get('user_stories', [])))" 2>/dev/null)

    echo ""
    echo "RESULTS:"
    echo "  Status: $FINAL_STATUS"
    echo "  Duration: ${DURATION}s"
    echo "  Epics: $EPICS"
    echo "  User Stories: $STORIES"
    echo "  Implementation Tasks: $CHILDREN"
    echo "  Expected Complexity: $expected_complexity"
    echo "  Expected Tasks: $expected_min_tasks-$expected_max_tasks"

    # Determine success
    SUCCESS="false"
    ERROR_MSG=""

    if [ "$FINAL_STATUS" = "completed" ]; then
        if [ "$CHILDREN" -ge "$expected_min_tasks" ] && [ "$CHILDREN" -le "$expected_max_tasks" ]; then
            SUCCESS="true"
            print_status "$GREEN" "  ✓ Task count within expected range"
        else
            ERROR_MSG="Task count $CHILDREN outside expected range $expected_min_tasks-$expected_max_tasks"
            print_status "$YELLOW" "  ⚠ $ERROR_MSG"
        fi
    else
        ERROR_MSG="Task status: $FINAL_STATUS (not completed)"
        print_status "$RED" "  ✗ $ERROR_MSG"
    fi

    # Add to report
    # Convert bash boolean to Python boolean
    if [ "$SUCCESS" = "true" ]; then
        PY_SUCCESS="True"
    else
        PY_SUCCESS="False"
    fi

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
    "epics": $EPICS,
    "stories": $STORIES,
    "tasks": $CHILDREN,
    "success": $PY_SUCCESS,
    "error": "$ERROR_MSG" if "$ERROR_MSG" else None
})

with open('$REPORT_FILE', 'w') as f:
    json.dump(report, f, indent=2)
EOF

    echo ""
}

# Test definitions
run_atomic_tests() {
    print_status "$GREEN" "\n🟢 RUNNING ATOMIC TASKS\n"

    run_test "atomic" "simple-crud" \
        "Build a task management app where users can create, view, update, and delete tasks" \
        '{"tech_stack": "React, Node.js, PostgreSQL"}' \
        "atomic" 1 10

    run_test "atomic" "todo-app" \
        "Create a simple TODO list application with: Add new tasks with title and description, Mark tasks as complete/incomplete, Delete tasks, Filter by status (all, active, completed)" \
        '{"tech_stack": "React, Node.js"}' \
        "atomic" 1 10

    run_test "atomic" "contact-form" \
        "Build a contact form with name, email, and message fields. Validate email format. Send submissions to an API endpoint. Store submissions in a database. Display success/error messages. Tech stack: React frontend, Node.js/Express backend, PostgreSQL database." \
        '{"tech_stack": {"frontend": "React", "backend": "Node.js/Express", "database": "PostgreSQL"}}' \
        "atomic" 1 10

    run_test "atomic" "url-shortener" \
        "URL shortener service: user enters long URL, system generates short code, redirects short URL to original. Track click counts." \
        '{"tech_stack": "Node.js, Redis"}' \
        "atomic" 1 10

    run_test "atomic" "weather-widget" \
        "Display current weather for user's location. Show temperature, conditions, humidity. Use OpenWeatherMap API. Auto-refresh every 15 minutes. Mobile responsive design." \
        '{"tech_stack": "React", "integrations": ["OpenWeatherMap API"]}' \
        "atomic" 1 10
}

run_medium_tests() {
    print_status "$YELLOW" "\n🟡 RUNNING MEDIUM COMPLEXITY TASKS\n"

    run_test "medium" "blog-platform" \
        "Build a blog platform with the following features: Authentication (User registration and login with email/password, JWT token-based authentication, Password reset via email), Content Management (Create, edit, delete blog posts, Rich text editor with markdown support, Draft and publish workflow, Featured images for posts, Categories and tags), Reader Features (Browse posts by category/tag, Search functionality, Commenting system for logged-in users only, Like/bookmark posts, RSS feed generation). Tech Stack: React, Node.js/Express, MongoDB" \
        '{"tech_stack": {"frontend": "React", "backend": "Node.js/Express", "database": "MongoDB"}}' \
        "medium" 10 30

    run_test "medium" "recipe-app" \
        "Build a recipe sharing app with: Recipe CRUD operations (title, ingredients, steps, prep time, servings), Image upload for recipe photos (AWS S3 or similar), User profiles with favorite recipes, Rating and review system (1-5 stars + text review), Search and filter (by cuisine, dietary restrictions, cook time), Ingredient-based search. Tech: React with TypeScript, Python/FastAPI, PostgreSQL, AWS S3" \
        '{"tech_stack": {"frontend": "React", "backend": "Python/FastAPI", "database": "PostgreSQL", "storage": "AWS S3"}}' \
        "medium" 10 30

    run_test "medium" "expense-tracker" \
        "Create an expense tracking application: User authentication with email/password, Add expenses (amount, category, date, description, receipt photo), Categories (Food, Transport, Entertainment, Bills, Shopping, Other), Monthly budget setting per category, Dashboard with charts (spending by category, trends over time), Export data as CSV or PDF, Recurring expense support (monthly bills), Multi-currency support, Mobile-friendly responsive design" \
        '{"tech_stack": {"frontend": "React", "backend": "Node.js", "database": "PostgreSQL"}}' \
        "medium" 10 30

    run_test "medium" "event-booking" \
        "Build an event booking platform where organizers can create events with details like name, description, date, time, location, capacity, and ticket price. Users should be able to browse upcoming events, filter by category and date, and purchase tickets. Include a payment integration with Stripe. Send confirmation emails after booking. Organizers get a dashboard to view bookings, check-in attendees, and export attendee lists. Include calendar integration (Google Calendar, iCal). Support for free and paid events. Tech stack: React, Node.js, PostgreSQL, Stripe API, SendGrid for emails." \
        '{"tech_stack": {"frontend": "React", "backend": "Node.js", "database": "PostgreSQL"}, "integrations": ["Stripe", "SendGrid", "Google Calendar"]}' \
        "medium" 10 30

    run_test "medium" "fitness-logger" \
        "Workout tracking app for gym enthusiasts. Core Functionality: Exercise library with instructions and videos (pre-populated database), Create custom workout routines (select exercises, sets, reps, rest time), Log completed workouts with weights and notes, Track progress over time with charts, Body measurement tracking (weight, body fat percentage, muscle mass), Personal records (PRs) for each exercise, Rest timer between sets, Workout history calendar view. Tech Stack: React Native, Node.js/Express, PostgreSQL, AWS S3 for videos" \
        '{"tech_stack": {"frontend": "React Native", "backend": "Node.js/Express", "database": "PostgreSQL", "storage": "AWS S3"}}' \
        "medium" 10 30
}

run_complex_tests() {
    print_status "$RED" "\n🟠 RUNNING COMPLEX TASKS\n"

    run_test "complex" "learning-platform" \
        "Build a comprehensive online learning platform with social features: USER MANAGEMENT (Multi-role authentication for students/instructors/admins, User profiles with bio/avatar/skills/achievements, OAuth integration with Google/GitHub, Email verification and password reset), COURSE CREATION (Instructors create courses with modules and lessons, Support video/text/quizzes/assignments, Video upload and streaming via AWS S3 + CloudFront, Rich text editor with code syntax highlighting, Course categories and difficulty levels, Draft/published workflow, Course pricing options), LEARNING EXPERIENCE (Video player with playback speed control and subtitles, Progress tracking, Note-taking during lessons, Downloadable resources, Interactive quizzes with instant feedback, Assignments with file submission, Discussion forums per course, Live Q&A sessions via WebRTC), SOCIAL FEATURES (Follow instructors and students, Activity feed, Direct messaging, Study groups/communities, Certificate generation upon completion), DISCOVERY (Course catalog with filters, Full-text search across courses, Personalized recommendations, Trending courses, Instructor profiles with ratings), PAYMENTS (Stripe integration for payments, Support one-time purchases and subscriptions, Revenue sharing for instructors, Coupon/discount codes, Invoicing and receipt generation), ANALYTICS (Student dashboard with progress/completed courses/certificates, Instructor dashboard with earnings/student enrollments/engagement metrics, Admin dashboard with platform metrics/user growth/revenue). Tech: React with TypeScript, Redux, Node.js/Express or Python/FastAPI, PostgreSQL with Redis for caching, AWS S3, CloudFront, Socket.io for real-time, SendGrid or AWS SES for email, Elasticsearch optional" \
        '{"tech_stack": {"frontend": "React", "backend": "Python/FastAPI", "database": "PostgreSQL", "cache": "Redis", "storage": "AWS S3", "cdn": "CloudFront", "realtime": "Socket.io", "email": "SendGrid"}}' \
        "complex" 30 70

    run_test "complex" "project-management" \
        "Build an Asana/Trello alternative with advanced features. WORKSPACE MANAGEMENT (Multi-tenant architecture with separate workspaces per organization, Workspace branding with logo and colors, Invite team members by email, Role-based permissions for admin/member/guest), PROJECT ORGANIZATION (Create unlimited projects per workspace, Multiple views including Board/Kanban/List/Calendar/Gantt chart/Timeline, Custom fields per project with text/number/dropdown/date/checkbox, Project templates for common workflows, Project archiving and restoration), TASK MANAGEMENT (Create tasks with title/description/assignee/due date/priority/labels, Subtasks and checklists, Task dependencies with blocks and blocked-by relationships, Recurring tasks daily/weekly/monthly, Time estimates and time tracking, Custom statuses per project, Bulk operations to move/update/delete multiple tasks), COLLABORATION (Comments on tasks with @mentions, File attachments for images/documents/PDFs, Activity log per task, Real-time updates via WebSockets, Notifications via in-app/email and optional Slack/Discord integration), AUTOMATION (Workflow automation rules with triggers and actions, Custom automations, Integration webhooks), REPORTING (Project progress dashboards, Burndown charts for sprint planning, Team workload view showing tasks per person, Time reports showing logged time per project/person, Custom report builder, Export reports as CSV/PDF), SEARCH (Full-text search across tasks/comments/attachments, Advanced filtering by assignee/due date/priority/labels/custom fields, Saved filters, Search across all projects or specific workspace), MOBILE APP (React Native mobile app for iOS/Android, Offline support with sync, Push notifications, Camera integration for attachments). Tech: React with TypeScript and Zustand or Redux, Python/FastAPI or Node.js with TypeScript, PostgreSQL, WebSockets via Socket.io or native WS, AWS S3 for file storage, PostgreSQL full-text search or Elasticsearch, Redis for caching, Celery or Bull for background jobs, SendGrid for email, React Native for mobile" \
        '{"tech_stack": {"frontend": "React", "backend": "Python/FastAPI", "database": "PostgreSQL", "cache": "Redis", "storage": "AWS S3", "realtime": "WebSockets", "queue": "Celery", "email": "SendGrid", "mobile": "React Native"}}' \
        "complex" 30 70
}

run_epic_tests() {
    print_status "$RED" "\n🔴 RUNNING EPIC TASKS\n"

    run_test "epic" "healthcare-portal" \
        "Build a comprehensive patient portal and practice management system for healthcare providers. PATIENT-FACING FEATURES (Patient registration with medical history intake forms, Appointment scheduling with calendar view filtering by provider/specialty/location, Video telemedicine consultations via WebRTC integration, Secure HIPAA-compliant messaging with healthcare providers, Medical records access including lab results/imaging/prescriptions/visit summaries, Prescription refill requests with pharmacy integration, Bill payment and insurance information management, Upload medical documents like insurance cards and referral letters, Family account linking for parents managing children's accounts, Appointment reminders via email and SMS through Twilio, Health tracking for symptoms/vitals/medications, Find a provider search with filters for specialty/location/insurance/availability), PROVIDER-FACING FEATURES (Provider dashboard with daily schedule, Patient charts with medical history/allergies/medications/visit notes, Clinical note templates like SOAP notes, E-prescribing with pharmacy database integration, Lab order entry and results review, Appointment management to schedule/reschedule/cancel/track no-shows, Billing and coding with ICD-10 and CPT codes, Patient messaging with priority flags, Telehealth video interface, Referral management, Document scanning and upload), ADMIN FEATURES (Practice management dashboard showing appointments/revenue/patient volume, User management for patients/providers/staff with role-based access, Appointment scheduling templates for provider availability and time slots, Insurance provider management, Billing reports and claim tracking, HIPAA audit logs, System settings and configuration, Analytics and reporting for patient demographics/appointment types/revenue), INTEGRATIONS (EHR/EMR integration using HL7 FHIR standard, Pharmacy databases for e-prescribing, Insurance eligibility verification APIs, Laboratory interfaces for ordering and results, Payment processing via Stripe or Square, SMS notifications via Twilio, Calendar sync with Google Calendar and Outlook), COMPLIANCE AND SECURITY (HIPAA compliance with encryption at rest and in transit, Two-factor authentication, Audit logging for all PHI access, Automatic session timeout, Consent forms and digital signatures, Data backup and disaster recovery, Business Associate Agreements tracking). Tech: React with TypeScript and HIPAA-compliant UI design, Python/Django or Node.js with strict security policies, PostgreSQL with encryption, AWS S3 with server-side encryption for file storage, Twilio Video or Agora.io for telemedicine, WebSockets for secure messaging, Celery or RabbitMQ for background processing, SendGrid plus Twilio for email/SMS, HIPAA-compliant hosting on AWS with BAA or Azure Health or GCP, HIPAA-compliant logging with no PHI in logs" \
        '{"tech_stack": {"frontend": "React", "backend": "Python/Django", "database": "PostgreSQL", "storage": "AWS S3", "video": "Twilio Video", "realtime": "WebSockets", "queue": "Celery", "email": "SendGrid", "sms": "Twilio", "hosting": "AWS"}, "compliance": ["HIPAA"]}' \
        "epic" 60 150

    run_test "epic" "real-estate-platform" \
        "Create a comprehensive real estate platform for buyers, sellers, and agents (Zillow/Realtor.com alternative). USER TYPES AND AUTHENTICATION (Multi-role system for Buyers/Sellers/Agents/Brokers/Admins, Email/password registration with email verification, OAuth with Google and Facebook, Agent/Broker verification system with license validation, Public profile pages for agents with bio/listings/reviews/contact info), PROPERTY LISTINGS (Create listing with address/price/beds/baths/sqft/lot size/year built/property type including house/condo/townhouse/land/commercial, Multiple high-quality photos up to 50 with drag-to-reorder, Virtual tour integration with 360-degree photos and Matterport embeds, Video tours via YouTube/Vimeo embeds or direct upload, Detailed property descriptions with rich text editor, Amenities checklist for pool/garage/fireplace/AC etc, HOA information and fees, Property history showing previous sales and price changes, Neighborhood info including schools/crime stats/walkability score via APIs, Map view with property pin, Status options for Active/Pending/Sold/Off Market, Featured/Premium listings with paid promotion), SEARCH AND DISCOVERY (Map-based search with drawing custom boundaries, Filter by price range/beds/baths/sqft/property type/lot size/year built/keywords, Save searches with email alerts for new matches, Sort by price/newest/price reduced/square footage, Nearby searches to find similar properties in area, School district search, Open house calendar view, Recently viewed properties), AGENT FEATURES (Agent dashboard with all their listings, Lead management for inquiries from buyers, CRM integration with HubSpot or Salesforce, Automated follow-up emails, MLS integration to import listings from Multiple Listing Service, Comparative Market Analysis CMA tool, Client portal to share properties with clients, Performance analytics showing views/leads/conversions, Team management for brokers managing multiple agents), BUYER TOOLS (Mortgage calculator with rates integrating live rate APIs, Affordability calculator, Saved properties and notes, Schedule showing requests with agents, Make offers via digital offer forms, Favorites/watchlist with price drop alerts, Neighborhood comparison tool, Commute time calculator via Google Maps API), COMMUNICATION (Secure messaging between buyers and agents, Showing request scheduling, Email notifications for new listings/price drops/messages, SMS alerts via Twilio integration, Video chat for virtual showings), MOBILE APP (Native iOS and Android apps via React Native, Push notifications, Location-based search for nearby properties, Camera integration for reverse image search, Offline saved searches), MONETIZATION (Premium listings for agents with featured placement, Lead generation subscriptions for agents, Advertising with banner ads and sponsored listings, Freemium model with basic free and advanced features paid), ADMIN FEATURES (Listing moderation to approve/reject new listings, User management to suspend spam accounts, Agent verification workflow, Platform analytics for listings/users/revenue/engagement, Payment management for subscriptions and refunds, Content management for blog posts and guides, Featured listings management), DATA INTEGRATIONS (MLS data feeds for listing imports, School ratings API like GreatSchools, Crime data API, Walk Score API, Google Maps API for geocoding/directions/Street View, Mortgage rate APIs, Property tax records, Census data for demographics), ADDITIONAL FEATURES (Blog section with SEO-optimized content, Real estate guides like first-time buyer tips, Agent reviews and ratings, Email marketing with newsletters featuring new listings, Social media sharing, Print-friendly listing PDFs, Referral program to refer agent and get reward). Tech: Next.js React with SSR for SEO plus TypeScript and TailwindCSS, Python/Django or Node.js/NestJS with TypeScript for backend, PostgreSQL with PostGIS for geospatial queries, Elasticsearch for fast property search, Redis for frequently accessed data caching, AWS S3 plus CloudFront CDN for storage, Google Maps JavaScript API, SendGrid for email, Twilio for SMS, Celery or Bull for background jobs, Google Analytics plus custom dashboard, React Native for mobile, AWS or GCP with auto-scaling for deployment" \
        '{"tech_stack": {"frontend": "Next.js", "backend": "Python/Django", "database": "PostgreSQL", "search": "Elasticsearch", "cache": "Redis", "storage": "AWS S3", "cdn": "CloudFront", "maps": "Google Maps", "email": "SendGrid", "sms": "Twilio", "queue": "Celery", "mobile": "React Native", "hosting": "AWS"}}' \
        "epic" 60 150
}

# Print summary
print_summary() {
    print_status "$BLUE" "\n========================================"
    print_status "$BLUE" "VALIDATION SUITE COMPLETE"
    print_status "$BLUE" "========================================\n"

    echo "Report saved to: $REPORT_FILE"
    echo ""

    python3 << 'EOF'
import json
import sys

with open('/tmp/validation_report_v2.json') as f:
    report = json.load(f)

# Overall stats
total = len(report)
passed = sum(1 for r in report if r['success'])
failed = total - passed
success_rate = (passed/total*100) if total > 0 else 0

print(f"Overall Summary:")
print(f"  Total tests: {total}")
print(f"  Passed: {passed}")
print(f"  Failed: {failed}")
print(f"  Success rate: {success_rate:.1f}%")
print()

# By category
categories = {}
for r in report:
    cat = r['category']
    if cat not in categories:
        categories[cat] = {'total': 0, 'passed': 0, 'failed': 0, 'tests': []}
    categories[cat]['total'] += 1
    if r['success']:
        categories[cat]['passed'] += 1
    else:
        categories[cat]['failed'] += 1
    categories[cat]['tests'].append(r)

print("Results by Category:")
for cat in ['atomic', 'medium', 'complex', 'epic']:
    if cat in categories:
        stats = categories[cat]
        rate = (stats['passed']/stats['total']*100) if stats['total'] > 0 else 0
        icon = '🟢' if cat == 'atomic' else '🟡' if cat == 'medium' else '🟠' if cat == 'complex' else '🔴'
        print(f"\n{icon} {cat.upper()}: {stats['passed']}/{stats['total']} passed ({rate:.1f}%)")

        for test in stats['tests']:
            status_icon = '✅' if test['success'] else '❌'
            name = test['name']
            epics = test['epics']
            stories = test['stories']
            tasks = test['tasks']
            duration = test['duration_seconds']
            expected_range = f"{test['expected_min_tasks']}-{test['expected_max_tasks']}"

            print(f"  {status_icon} {name}: {epics} epics, {stories} stories, {tasks} tasks ({duration}s) [expected: {expected_range}]")

            if not test['success'] and test.get('error'):
                print(f"     Error: {test['error']}")

# Task count analysis
print("\n\nTask Count Analysis:")
for cat in ['atomic', 'medium', 'complex', 'epic']:
    if cat in categories:
        tests = categories[cat]['tests']
        if tests:
            task_counts = [t['tasks'] for t in tests]
            avg_tasks = sum(task_counts) / len(task_counts)
            min_tasks = min(task_counts)
            max_tasks = max(task_counts)
            print(f"  {cat}: avg={avg_tasks:.1f}, min={min_tasks}, max={max_tasks}")
EOF
}

# Main execution
show_usage() {
    cat << 'USAGE'
Validation Suite v2 - Full Project Generation Testing

Usage:
  ./validation_suite_v2.sh [COMMAND] [OPTIONS]

Commands:
  all              Run all test categories (default)
  atomic           Run only atomic/simple tasks (🟢)
  medium           Run only medium complexity tasks (🟡)
  complex          Run only complex tasks (🟠)
  epic             Run only epic tasks (🔴)

  test NAME        Run a specific test by name
                   Examples: simple-crud, blog-platform, learning-platform

  list             List all available tests
  help             Show this help message

Environment Variables:
  API_URL          API endpoint (default: http://localhost:8000/api/tasks)
  TOKEN            Auth token (default: dev-bypass-token)
  REPORT_FILE      Output JSON file (default: /tmp/validation_report_v2.json)
  MAX_WAIT_SECONDS Max seconds to wait per task (default: 300)

Examples:
  # Run all tests
  ./validation_suite_v2.sh all

  # Run only atomic tests
  ./validation_suite_v2.sh atomic

  # Run a specific test
  ./validation_suite_v2.sh test blog-platform

  # List all available tests
  ./validation_suite_v2.sh list

  # Custom API URL and timeout
  API_URL=http://prod.example.com/api/tasks MAX_WAIT_SECONDS=600 ./validation_suite_v2.sh complex

USAGE
}

list_tests() {
    cat << 'LIST'
Available Tests:

🟢 ATOMIC (1-10 tasks expected):
  - simple-crud: Basic CRUD task manager
  - todo-app: TODO list with filters
  - contact-form: Contact form with validation
  - url-shortener: URL shortening service
  - weather-widget: Weather display widget

🟡 MEDIUM (10-30 tasks expected):
  - blog-platform: Blog with auth and content management
  - recipe-app: Recipe sharing with ratings
  - expense-tracker: Expense tracking with budgets
  - event-booking: Event booking with payments
  - fitness-logger: Workout tracking app

🟠 COMPLEX (30-70 tasks expected):
  - learning-platform: Online learning platform with courses
  - project-management: Project management tool (Asana/Trello alternative)

🔴 EPIC (60-150 tasks expected):
  - healthcare-portal: HIPAA-compliant patient portal
  - real-estate-platform: Real estate listing platform

LIST
}

# Parse command
COMMAND="${1:-all}"

case "$COMMAND" in
    all)
        run_atomic_tests
        run_medium_tests
        run_complex_tests
        run_epic_tests
        print_summary
        ;;
    atomic)
        run_atomic_tests
        print_summary
        ;;
    medium)
        run_medium_tests
        print_summary
        ;;
    complex)
        run_complex_tests
        print_summary
        ;;
    epic)
        run_epic_tests
        print_summary
        ;;
    test)
        TEST_NAME="$2"
        if [ -z "$TEST_NAME" ]; then
            print_status "$RED" "Error: Please specify a test name"
            echo "Run './validation_suite_v2.sh list' to see available tests"
            exit 1
        fi

        # Run specific test based on name
        case "$TEST_NAME" in
            simple-crud)
                run_test "atomic" "simple-crud" \
                    "Build a task management app where users can create, view, update, and delete tasks" \
                    '{"tech_stack": "React, Node.js, PostgreSQL"}' \
                    "atomic" 1 10
                ;;
            todo-app)
                run_test "atomic" "todo-app" \
                    "Create a simple TODO list application with: Add new tasks with title and description, Mark tasks as complete/incomplete, Delete tasks, Filter by status (all, active, completed)" \
                    '{"tech_stack": "React, Node.js"}' \
                    "atomic" 1 10
                ;;
            contact-form)
                run_test "atomic" "contact-form" \
                    "Build a contact form with name, email, and message fields. Validate email format. Send submissions to an API endpoint. Store submissions in a database. Display success/error messages. Tech stack: React frontend, Node.js/Express backend, PostgreSQL database." \
                    '{"tech_stack": {"frontend": "React", "backend": "Node.js/Express", "database": "PostgreSQL"}}' \
                    "atomic" 1 10
                ;;
            url-shortener)
                run_test "atomic" "url-shortener" \
                    "URL shortener service: user enters long URL, system generates short code, redirects short URL to original. Track click counts." \
                    '{"tech_stack": "Node.js, Redis"}' \
                    "atomic" 1 10
                ;;
            weather-widget)
                run_test "atomic" "weather-widget" \
                    "Display current weather for user's location. Show temperature, conditions, humidity. Use OpenWeatherMap API. Auto-refresh every 15 minutes. Mobile responsive design." \
                    '{"tech_stack": "React", "integrations": ["OpenWeatherMap API"]}' \
                    "atomic" 1 10
                ;;
            blog-platform)
                run_test "medium" "blog-platform" \
                    "Build a blog platform with the following features: Authentication (User registration and login with email/password, JWT token-based authentication, Password reset via email), Content Management (Create, edit, delete blog posts, Rich text editor with markdown support, Draft and publish workflow, Featured images for posts, Categories and tags), Reader Features (Browse posts by category/tag, Search functionality, Commenting system for logged-in users only, Like/bookmark posts, RSS feed generation). Tech Stack: React, Node.js/Express, MongoDB" \
                    '{"tech_stack": {"frontend": "React", "backend": "Node.js/Express", "database": "MongoDB"}}' \
                    "medium" 10 30
                ;;
            recipe-app)
                run_test "medium" "recipe-app" \
                    "Build a recipe sharing app with: Recipe CRUD operations (title, ingredients, steps, prep time, servings), Image upload for recipe photos (AWS S3 or similar), User profiles with favorite recipes, Rating and review system (1-5 stars + text review), Search and filter (by cuisine, dietary restrictions, cook time), Ingredient-based search. Tech: React with TypeScript, Python/FastAPI, PostgreSQL, AWS S3" \
                    '{"tech_stack": {"frontend": "React", "backend": "Python/FastAPI", "database": "PostgreSQL", "storage": "AWS S3"}}' \
                    "medium" 10 30
                ;;
            expense-tracker)
                run_test "medium" "expense-tracker" \
                    "Create an expense tracking application: User authentication with email/password, Add expenses (amount, category, date, description, receipt photo), Categories (Food, Transport, Entertainment, Bills, Shopping, Other), Monthly budget setting per category, Dashboard with charts (spending by category, trends over time), Export data as CSV or PDF, Recurring expense support (monthly bills), Multi-currency support, Mobile-friendly responsive design" \
                    '{"tech_stack": {"frontend": "React", "backend": "Node.js", "database": "PostgreSQL"}}' \
                    "medium" 10 30
                ;;
            event-booking)
                run_test "medium" "event-booking" \
                    "Build an event booking platform where organizers can create events with details like name, description, date, time, location, capacity, and ticket price. Users should be able to browse upcoming events, filter by category and date, and purchase tickets. Include a payment integration with Stripe. Send confirmation emails after booking. Organizers get a dashboard to view bookings, check-in attendees, and export attendee lists. Include calendar integration (Google Calendar, iCal). Support for free and paid events. Tech stack: React, Node.js, PostgreSQL, Stripe API, SendGrid for emails." \
                    '{"tech_stack": {"frontend": "React", "backend": "Node.js", "database": "PostgreSQL"}, "integrations": ["Stripe", "SendGrid", "Google Calendar"]}' \
                    "medium" 10 30
                ;;
            fitness-logger)
                run_test "medium" "fitness-logger" \
                    "Workout tracking app for gym enthusiasts. Core Functionality: Exercise library with instructions and videos (pre-populated database), Create custom workout routines (select exercises, sets, reps, rest time), Log completed workouts with weights and notes, Track progress over time with charts, Body measurement tracking (weight, body fat percentage, muscle mass), Personal records (PRs) for each exercise, Rest timer between sets, Workout history calendar view. Tech Stack: React Native, Node.js/Express, PostgreSQL, AWS S3 for videos" \
                    '{"tech_stack": {"frontend": "React Native", "backend": "Node.js/Express", "database": "PostgreSQL", "storage": "AWS S3"}}' \
                    "medium" 10 30
                ;;
            learning-platform)
                run_test "complex" "learning-platform" \
                    "Build a comprehensive online learning platform with social features: USER MANAGEMENT (Multi-role authentication for students/instructors/admins, User profiles with bio/avatar/skills/achievements, OAuth integration with Google/GitHub, Email verification and password reset), COURSE CREATION (Instructors create courses with modules and lessons, Support video/text/quizzes/assignments, Video upload and streaming via AWS S3 + CloudFront, Rich text editor with code syntax highlighting, Course categories and difficulty levels, Draft/published workflow, Course pricing options), LEARNING EXPERIENCE (Video player with playback speed control and subtitles, Progress tracking, Note-taking during lessons, Downloadable resources, Interactive quizzes with instant feedback, Assignments with file submission, Discussion forums per course, Live Q&A sessions via WebRTC), SOCIAL FEATURES (Follow instructors and students, Activity feed, Direct messaging, Study groups/communities, Certificate generation upon completion), DISCOVERY (Course catalog with filters, Full-text search across courses, Personalized recommendations, Trending courses, Instructor profiles with ratings), PAYMENTS (Stripe integration for payments, Support one-time purchases and subscriptions, Revenue sharing for instructors, Coupon/discount codes, Invoicing and receipt generation), ANALYTICS (Student dashboard with progress/completed courses/certificates, Instructor dashboard with earnings/student enrollments/engagement metrics, Admin dashboard with platform metrics/user growth/revenue). Tech: React with TypeScript, Redux, Node.js/Express or Python/FastAPI, PostgreSQL with Redis for caching, AWS S3, CloudFront, Socket.io for real-time, SendGrid or AWS SES for email, Elasticsearch optional" \
                    '{"tech_stack": {"frontend": "React", "backend": "Python/FastAPI", "database": "PostgreSQL", "cache": "Redis", "storage": "AWS S3", "cdn": "CloudFront", "realtime": "Socket.io", "email": "SendGrid"}}' \
                    "complex" 30 70
                ;;
            project-management)
                run_test "complex" "project-management" \
                    "Build an Asana/Trello alternative with advanced features. WORKSPACE MANAGEMENT (Multi-tenant architecture with separate workspaces per organization, Workspace branding with logo and colors, Invite team members by email, Role-based permissions for admin/member/guest), PROJECT ORGANIZATION (Create unlimited projects per workspace, Multiple views including Board/Kanban/List/Calendar/Gantt chart/Timeline, Custom fields per project with text/number/dropdown/date/checkbox, Project templates for common workflows, Project archiving and restoration), TASK MANAGEMENT (Create tasks with title/description/assignee/due date/priority/labels, Subtasks and checklists, Task dependencies with blocks and blocked-by relationships, Recurring tasks daily/weekly/monthly, Time estimates and time tracking, Custom statuses per project, Bulk operations to move/update/delete multiple tasks), COLLABORATION (Comments on tasks with @mentions, File attachments for images/documents/PDFs, Activity log per task, Real-time updates via WebSockets, Notifications via in-app/email and optional Slack/Discord integration), AUTOMATION (Workflow automation rules with triggers and actions, Custom automations, Integration webhooks), REPORTING (Project progress dashboards, Burndown charts for sprint planning, Team workload view showing tasks per person, Time reports showing logged time per project/person, Custom report builder, Export reports as CSV/PDF), SEARCH (Full-text search across tasks/comments/attachments, Advanced filtering by assignee/due date/priority/labels/custom fields, Saved filters, Search across all projects or specific workspace), MOBILE APP (React Native mobile app for iOS/Android, Offline support with sync, Push notifications, Camera integration for attachments). Tech: React with TypeScript and Zustand or Redux, Python/FastAPI or Node.js with TypeScript, PostgreSQL, WebSockets via Socket.io or native WS, AWS S3 for file storage, PostgreSQL full-text search or Elasticsearch, Redis for caching, Celery or Bull for background jobs, SendGrid for email, React Native for mobile" \
                    '{"tech_stack": {"frontend": "React", "backend": "Python/FastAPI", "database": "PostgreSQL", "cache": "Redis", "storage": "AWS S3", "realtime": "WebSockets", "queue": "Celery", "email": "SendGrid", "mobile": "React Native"}}' \
                    "complex" 30 70
                ;;
            healthcare-portal)
                run_test "epic" "healthcare-portal" \
                    "Build a comprehensive patient portal and practice management system for healthcare providers. PATIENT-FACING FEATURES (Patient registration with medical history intake forms, Appointment scheduling with calendar view filtering by provider/specialty/location, Video telemedicine consultations via WebRTC integration, Secure HIPAA-compliant messaging with healthcare providers, Medical records access including lab results/imaging/prescriptions/visit summaries, Prescription refill requests with pharmacy integration, Bill payment and insurance information management, Upload medical documents like insurance cards and referral letters, Family account linking for parents managing children's accounts, Appointment reminders via email and SMS through Twilio, Health tracking for symptoms/vitals/medications, Find a provider search with filters for specialty/location/insurance/availability), PROVIDER-FACING FEATURES (Provider dashboard with daily schedule, Patient charts with medical history/allergies/medications/visit notes, Clinical note templates like SOAP notes, E-prescribing with pharmacy database integration, Lab order entry and results review, Appointment management to schedule/reschedule/cancel/track no-shows, Billing and coding with ICD-10 and CPT codes, Patient messaging with priority flags, Telehealth video interface, Referral management, Document scanning and upload), ADMIN FEATURES (Practice management dashboard showing appointments/revenue/patient volume, User management for patients/providers/staff with role-based access, Appointment scheduling templates for provider availability and time slots, Insurance provider management, Billing reports and claim tracking, HIPAA audit logs, System settings and configuration, Analytics and reporting for patient demographics/appointment types/revenue), INTEGRATIONS (EHR/EMR integration using HL7 FHIR standard, Pharmacy databases for e-prescribing, Insurance eligibility verification APIs, Laboratory interfaces for ordering and results, Payment processing via Stripe or Square, SMS notifications via Twilio, Calendar sync with Google Calendar and Outlook), COMPLIANCE AND SECURITY (HIPAA compliance with encryption at rest and in transit, Two-factor authentication, Audit logging for all PHI access, Automatic session timeout, Consent forms and digital signatures, Data backup and disaster recovery, Business Associate Agreements tracking). Tech: React with TypeScript and HIPAA-compliant UI design, Python/Django or Node.js with strict security policies, PostgreSQL with encryption, AWS S3 with server-side encryption for file storage, Twilio Video or Agora.io for telemedicine, WebSockets for secure messaging, Celery or RabbitMQ for background processing, SendGrid plus Twilio for email/SMS, HIPAA-compliant hosting on AWS with BAA or Azure Health or GCP, HIPAA-compliant logging with no PHI in logs" \
                    '{"tech_stack": {"frontend": "React", "backend": "Python/Django", "database": "PostgreSQL", "storage": "AWS S3", "video": "Twilio Video", "realtime": "WebSockets", "queue": "Celery", "email": "SendGrid", "sms": "Twilio", "hosting": "AWS"}, "compliance": ["HIPAA"]}' \
                    "epic" 60 150
                ;;
            real-estate-platform)
                run_test "epic" "real-estate-platform" \
                    "Create a comprehensive real estate platform for buyers, sellers, and agents (Zillow/Realtor.com alternative). USER TYPES AND AUTHENTICATION (Multi-role system for Buyers/Sellers/Agents/Brokers/Admins, Email/password registration with email verification, OAuth with Google and Facebook, Agent/Broker verification system with license validation, Public profile pages for agents with bio/listings/reviews/contact info), PROPERTY LISTINGS (Create listing with address/price/beds/baths/sqft/lot size/year built/property type including house/condo/townhouse/land/commercial, Multiple high-quality photos up to 50 with drag-to-reorder, Virtual tour integration with 360-degree photos and Matterport embeds, Video tours via YouTube/Vimeo embeds or direct upload, Detailed property descriptions with rich text editor, Amenities checklist for pool/garage/fireplace/AC etc, HOA information and fees, Property history showing previous sales and price changes, Neighborhood info including schools/crime stats/walkability score via APIs, Map view with property pin, Status options for Active/Pending/Sold/Off Market, Featured/Premium listings with paid promotion), SEARCH AND DISCOVERY (Map-based search with drawing custom boundaries, Filter by price range/beds/baths/sqft/property type/lot size/year built/keywords, Save searches with email alerts for new matches, Sort by price/newest/price reduced/square footage, Nearby searches to find similar properties in area, School district search, Open house calendar view, Recently viewed properties), AGENT FEATURES (Agent dashboard with all their listings, Lead management for inquiries from buyers, CRM integration with HubSpot or Salesforce, Automated follow-up emails, MLS integration to import listings from Multiple Listing Service, Comparative Market Analysis CMA tool, Client portal to share properties with clients, Performance analytics showing views/leads/conversions, Team management for brokers managing multiple agents), BUYER TOOLS (Mortgage calculator with rates integrating live rate APIs, Affordability calculator, Saved properties and notes, Schedule showing requests with agents, Make offers via digital offer forms, Favorites/watchlist with price drop alerts, Neighborhood comparison tool, Commute time calculator via Google Maps API), COMMUNICATION (Secure messaging between buyers and agents, Showing request scheduling, Email notifications for new listings/price drops/messages, SMS alerts via Twilio integration, Video chat for virtual showings), MOBILE APP (Native iOS and Android apps via React Native, Push notifications, Location-based search for nearby properties, Camera integration for reverse image search, Offline saved searches), MONETIZATION (Premium listings for agents with featured placement, Lead generation subscriptions for agents, Advertising with banner ads and sponsored listings, Freemium model with basic free and advanced features paid), ADMIN FEATURES (Listing moderation to approve/reject new listings, User management to suspend spam accounts, Agent verification workflow, Platform analytics for listings/users/revenue/engagement, Payment management for subscriptions and refunds, Content management for blog posts and guides, Featured listings management), DATA INTEGRATIONS (MLS data feeds for listing imports, School ratings API like GreatSchools, Crime data API, Walk Score API, Google Maps API for geocoding/directions/Street View, Mortgage rate APIs, Property tax records, Census data for demographics), ADDITIONAL FEATURES (Blog section with SEO-optimized content, Real estate guides like first-time buyer tips, Agent reviews and ratings, Email marketing with newsletters featuring new listings, Social media sharing, Print-friendly listing PDFs, Referral program to refer agent and get reward). Tech: Next.js React with SSR for SEO plus TypeScript and TailwindCSS, Python/Django or Node.js/NestJS with TypeScript for backend, PostgreSQL with PostGIS for geospatial queries, Elasticsearch for fast property search, Redis for frequently accessed data caching, AWS S3 plus CloudFront CDN for storage, Google Maps JavaScript API, SendGrid for email, Twilio for SMS, Celery or Bull for background jobs, Google Analytics plus custom dashboard, React Native for mobile, AWS or GCP with auto-scaling for deployment" \
                    '{"tech_stack": {"frontend": "Next.js", "backend": "Python/Django", "database": "PostgreSQL", "search": "Elasticsearch", "cache": "Redis", "storage": "AWS S3", "cdn": "CloudFront", "maps": "Google Maps", "email": "SendGrid", "sms": "Twilio", "queue": "Celery", "mobile": "React Native", "hosting": "AWS"}}' \
                    "epic" 60 150
                ;;
            *)
                print_status "$RED" "Error: Unknown test '$TEST_NAME'"
                echo "Run './validation_suite_v2.sh list' to see available tests"
                exit 1
                ;;
        esac
        print_summary
        ;;
    list)
        list_tests
        ;;
    help|--help|-h)
        show_usage
        ;;
    *)
        print_status "$RED" "Error: Unknown command '$COMMAND'"
        echo ""
        show_usage
        exit 1
        ;;
esac
