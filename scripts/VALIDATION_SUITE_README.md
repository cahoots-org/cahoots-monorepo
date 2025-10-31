# Validation Suite v2 - Usage Guide

Comprehensive testing suite for Cahoots full project generation capabilities.

## Quick Start

```bash
# Run all tests
./scripts/validation_suite.sh all

# Run specific category
./scripts/validation_suite.sh atomic
./scripts/validation_suite.sh medium
./scripts/validation_suite.sh complex
./scripts/validation_suite.sh epic

# Run individual test
./scripts/validation_suite.sh test blog-platform

# List all available tests
./scripts/validation_suite.sh list

# Show help
./scripts/validation_suite.sh help
```

## Test Categories

### 🟢 Atomic (1-10 tasks expected)
Simple, well-defined features with minimal decomposition:
- `simple-crud` - Basic CRUD task manager
- `todo-app` - TODO list with filters
- `contact-form` - Contact form with validation
- `url-shortener` - URL shortening service
- `weather-widget` - Weather display widget

**Run all atomic tests:**
```bash
./scripts/validation_suite.sh atomic
```

### 🟡 Medium (10-30 tasks expected)
Features requiring moderate decomposition with multiple components:
- `blog-platform` - Blog with auth and content management
- `recipe-app` - Recipe sharing with ratings
- `expense-tracker` - Expense tracking with budgets
- `event-booking` - Event booking with payments
- `fitness-logger` - Workout tracking app

**Run all medium tests:**
```bash
./scripts/validation_suite.sh medium
```

### 🟠 Complex (30-70 tasks expected)
Projects with multiple integrated systems and advanced features:
- `learning-platform` - Online learning platform with courses
- `project-management` - Project management tool (Asana/Trello alternative)

**Run all complex tests:**
```bash
./scripts/validation_suite.sh complex
```

### 🔴 Epic (60-150 tasks expected)
Large-scale full applications with extensive feature sets:
- `healthcare-portal` - HIPAA-compliant patient portal
- `real-estate-platform` - Real estate listing platform

**Run all epic tests:**
```bash
./scripts/validation_suite.sh epic
```

## Individual Test Examples

```bash
# Test a simple atomic feature
./scripts/validation_suite.sh test simple-crud

# Test a medium complexity feature
./scripts/validation_suite.sh test blog-platform

# Test a complex feature
./scripts/validation_suite.sh test learning-platform

# Test an epic feature
./scripts/validation_suite.sh test healthcare-portal
```

## Environment Variables

Customize behavior with environment variables:

```bash
# Custom API endpoint
API_URL=http://prod.example.com/api/tasks ./scripts/validation_suite.sh atomic

# Custom authentication token
TOKEN=my-auth-token ./scripts/validation_suite.sh test blog-platform

# Custom report output location
REPORT_FILE=/home/user/my-report.json ./scripts/validation_suite.sh all

# Increase timeout for epic tasks (10 minutes)
MAX_WAIT_SECONDS=600 ./scripts/validation_suite.sh epic

# Combine multiple variables
API_URL=http://localhost:8000/api/tasks \
TOKEN=dev-bypass-token \
REPORT_FILE=/tmp/my-report.json \
MAX_WAIT_SECONDS=300 \
./scripts/validation_suite.sh all
```

## Default Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `API_URL` | `http://localhost:8000/api/tasks` | Cahoots API endpoint |
| `TOKEN` | `dev-bypass-token` | Authentication token |
| `REPORT_FILE` | `/tmp/validation_report_v2.json` | JSON report output path |
| `MAX_WAIT_SECONDS` | `300` (5 minutes) | Max wait time per task |

## Output

### Console Output
- **Color-coded progress** (🟢 🟡 🟠 🔴)
- **Real-time status updates** during processing
- **Summary statistics** by category
- **Task count analysis** (average, min, max)

### JSON Report
Saved to `$REPORT_FILE` (default: `/tmp/validation_report_v2.json`)

**Structure:**
```json
[
  {
    "category": "atomic",
    "name": "simple-crud",
    "description": "Build a task management app...",
    "expected_complexity": "atomic",
    "expected_min_tasks": 1,
    "expected_max_tasks": 10,
    "task_id": "abc-123",
    "status": "completed",
    "duration_seconds": 45,
    "epics": 1,
    "stories": 5,
    "tasks": 8,
    "success": true,
    "error": null
  }
]
```

### Summary Statistics
At the end of each run:
- **Overall summary** (total, passed, failed, success rate)
- **Results by category** (with emoji indicators)
- **Individual test results** (status, epics, stories, tasks, duration)
- **Task count analysis** (avg, min, max per category)

## Examples

### Run Quick Smoke Test
Test one feature from each category:
```bash
./scripts/validation_suite.sh test simple-crud
./scripts/validation_suite.sh test blog-platform
./scripts/validation_suite.sh test learning-platform
```

### Production Validation
Test against production environment with extended timeout:
```bash
API_URL=https://api.cahoots.com/api/tasks \
TOKEN=prod-token-here \
MAX_WAIT_SECONDS=600 \
REPORT_FILE=/var/log/cahoots/validation-$(date +%Y%m%d).json \
./scripts/validation_suite.sh all
```

### CI/CD Pipeline Integration
```bash
#!/bin/bash
# ci-validate.sh

set -e

# Run validation suite
./scripts/validation_suite.sh atomic

# Check results
REPORT=/tmp/validation_report_v2.json
SUCCESS_RATE=$(python3 -c "
import json
with open('$REPORT') as f:
    report = json.load(f)
total = len(report)
passed = sum(1 for r in report if r['success'])
print(passed/total*100 if total > 0 else 0)
")

# Fail CI if success rate < 80%
if (( $(echo "$SUCCESS_RATE < 80" | bc -l) )); then
    echo "Validation failed: $SUCCESS_RATE% success rate"
    exit 1
fi

echo "Validation passed: $SUCCESS_RATE% success rate"
```

## Interpreting Results

### Success Criteria
A test is marked as **successful** if:
1. Task status reaches `completed`
2. Generated task count falls within expected range

### Warnings (⚠️)
- Task completed but count outside expected range
- May indicate over/under-decomposition

### Failures (❌)
- Task creation failed
- Task status is not `completed` (timeout, error, etc.)

### Expected Task Ranges

| Complexity | Min | Max | Typical |
|------------|-----|-----|---------|
| Atomic | 1 | 10 | 3-7 |
| Medium | 10 | 30 | 15-25 |
| Complex | 30 | 70 | 40-60 |
| Epic | 60 | 150 | 80-120 |

## Troubleshooting

### Issue: "Could not create task"
**Solution:** Check API endpoint and authentication token
```bash
# Test API directly
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-bypass-token" \
  -d '{"description": "test", "context": {}}'
```

### Issue: Task times out (stays in "processing")
**Solutions:**
- Increase `MAX_WAIT_SECONDS`
- Check Cahoots API logs: `docker compose logs api --tail 100`
- Check Contex logs: `docker compose logs context-engine --tail 100`

### Issue: Task count outside expected range
**Analysis:**
- Review actual task descriptions in Redis
- Check if decomposition is appropriate for the prompt
- Consider if expected ranges need adjustment

### Issue: All tests failing
**Checklist:**
1. Is Cahoots API running? `docker compose ps`
2. Is Redis running? `docker compose exec redis redis-cli ping`
3. Is Contex running? `docker compose ps context-engine`
4. Check API health: `curl http://localhost:8000/health`

## Advanced Usage

### Custom Test Iteration
Run the same test multiple times:
```bash
for i in {1..5}; do
  echo "Run $i"
  ./scripts/validation_suite.sh test blog-platform
  mv /tmp/validation_report_v2.json /tmp/report-run-$i.json
done
```

### Parallel Execution
Run multiple categories in parallel:
```bash
./scripts/validation_suite.sh atomic &
PID1=$!

./scripts/validation_suite.sh medium &
PID2=$!

wait $PID1 $PID2
echo "All tests complete"
```

### Analysis Scripts
Aggregate multiple reports:
```python
import json
import glob

reports = []
for file in glob.glob('/tmp/report-*.json'):
    with open(file) as f:
        reports.extend(json.load(f))

# Calculate aggregate stats
total = len(reports)
passed = sum(1 for r in reports if r['success'])
avg_duration = sum(r['duration_seconds'] for r in reports) / total

print(f"Total tests: {total}")
print(f"Success rate: {passed/total*100:.1f}%")
print(f"Avg duration: {avg_duration:.1f}s")
```

## Next Steps

After running validation:
1. Review JSON report for detailed metrics
2. Investigate failed tests (check logs, task IDs)
3. Analyze task counts vs. expected ranges
4. Use individual test IDs to inspect actual decomposition quality
5. Iterate on prompts or decomposition logic based on findings
