#!/bin/bash
# Detailed Gitea merge debug test

set -e

TOKEN="f10f946e4af76ad8ece8f80f507ddb9183dbad05"
GITEA_URL="http://localhost:3001"
REPO="test-merge-debug-$(date +%s)"

echo "=== Creating test repo: $REPO ==="
REPO_RESULT=$(curl -s -X POST "$GITEA_URL/api/v1/user/repos" \
    -H "Authorization: token $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"$REPO\",\"auto_init\":true,\"private\":true}")
echo "Repo result: $REPO_RESULT"

sleep 2

echo ""
echo "=== Creating feature branch ==="
BRANCH_RESULT=$(curl -s -X POST "$GITEA_URL/api/v1/repos/cahoots-bot/$REPO/branches" \
    -H "Authorization: token $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"new_branch_name":"feature-test","old_branch_name":"main"}')
echo "Branch result: $BRANCH_RESULT"

echo ""
echo "=== Adding file to feature branch ==="
CONTENT=$(echo "Hello World" | base64)
FILE_RESULT=$(curl -s -X POST "$GITEA_URL/api/v1/repos/cahoots-bot/$REPO/contents/test.txt" \
    -H "Authorization: token $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"content\":\"$CONTENT\",\"message\":\"Add test file\",\"branch\":\"feature-test\"}")
echo "File result: $FILE_RESULT" | head -c 200
echo "..."

echo ""
echo "=== Creating PR ==="
PR_RESULT=$(curl -s -X POST "$GITEA_URL/api/v1/repos/cahoots-bot/$REPO/pulls" \
    -H "Authorization: token $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"title":"Test PR","head":"feature-test","base":"main","body":"Test"}')
echo "PR result: $PR_RESULT"

PR_NUMBER=$(echo "$PR_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('number',''))" 2>/dev/null || echo "")
if [ -z "$PR_NUMBER" ]; then
    echo "ERROR: Failed to get PR number"
    curl -s -X DELETE "$GITEA_URL/api/v1/repos/cahoots-bot/$REPO" -H "Authorization: token $TOKEN"
    exit 1
fi

echo ""
echo "=== Checking PR #$PR_NUMBER details ==="
sleep 1
PR_DETAILS=$(curl -s "$GITEA_URL/api/v1/repos/cahoots-bot/$REPO/pulls/$PR_NUMBER" \
    -H "Authorization: token $TOKEN")
echo "$PR_DETAILS" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f'State: {d.get(\"state\")}')
print(f'Mergeable: {d.get(\"mergeable\")}')
print(f'Head: {d.get(\"head\",{}).get(\"ref\")} -> Base: {d.get(\"base\",{}).get(\"ref\")}')
print(f'Has conflicts: {d.get(\"merge_base\", \"unknown\")}')
"

echo ""
echo "=== Attempting merge with verbose output ==="
echo "Request: POST /repos/cahoots-bot/$REPO/pulls/$PR_NUMBER/merge"
echo 'Body: {"Do":"merge","MergeMessageField":"Merge test PR"}'
echo ""
echo "Response:"

# Use -i to get headers, -w to get HTTP code
HTTP_CODE=$(curl -s -w "%{http_code}" -o /tmp/merge_response.txt -X POST \
    "$GITEA_URL/api/v1/repos/cahoots-bot/$REPO/pulls/$PR_NUMBER/merge" \
    -H "Authorization: token $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"Do":"merge","MergeMessageField":"Merge test PR"}')

echo "HTTP Status: $HTTP_CODE"
echo "Response body:"
cat /tmp/merge_response.txt
echo ""

# Check PR status after merge attempt
echo ""
echo "=== PR status after merge attempt ==="
PR_STATUS=$(curl -s "$GITEA_URL/api/v1/repos/cahoots-bot/$REPO/pulls/$PR_NUMBER" \
    -H "Authorization: token $TOKEN")
echo "$PR_STATUS" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f'State: {d.get(\"state\")}')
print(f'Merged: {d.get(\"merged\")}')
print(f'Merged by: {d.get(\"merged_by\",{}).get(\"login\",\"none\")}')
"

echo ""
echo "=== Cleanup ==="
curl -s -X DELETE "$GITEA_URL/api/v1/repos/cahoots-bot/$REPO" -H "Authorization: token $TOKEN"
echo "Done - deleted $REPO"
