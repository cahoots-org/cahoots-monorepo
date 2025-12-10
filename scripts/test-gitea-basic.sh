#!/bin/bash
# Basic Gitea API test to debug merge issues
# Tests the fundamental operations: create repo, create branch, commit, create PR, merge

set -e

GITEA_URL="http://localhost:3001"
TOKEN="f10f946e4af76ad8ece8f80f507ddb9183dbad05"
OWNER="cahoots-bot"
REPO="test-merge-$(date +%s)"

echo "=== Basic Gitea Merge Test ==="
echo "Testing with repo: $REPO"
echo ""

# Helper function
api() {
    local method=$1
    local path=$2
    local data=$3
    
    if [ -n "$data" ]; then
        curl -s -X "$method" "$GITEA_URL/api/v1$path" \
            -H "Authorization: token $TOKEN" \
            -H "Content-Type: application/json" \
            -d "$data"
    else
        curl -s -X "$method" "$GITEA_URL/api/v1$path" \
            -H "Authorization: token $TOKEN"
    fi
}

# Step 1: Create a new repository
echo "Step 1: Creating repository..."
RESULT=$(api POST "/user/repos" "{\"name\":\"$REPO\",\"auto_init\":true,\"private\":true,\"default_branch\":\"main\"}")
if echo "$RESULT" | grep -q '"id"'; then
    echo "  ✓ Repository created"
else
    echo "  ✗ Failed to create repository: $RESULT"
    exit 1
fi

# Give Gitea a moment to initialize the repo
sleep 2

# Step 2: Create a feature branch
echo "Step 2: Creating feature branch..."
RESULT=$(api POST "/repos/$OWNER/$REPO/branches" '{"new_branch_name":"feature-test","old_branch_name":"main"}')
if echo "$RESULT" | grep -q '"name"'; then
    echo "  ✓ Branch created"
else
    echo "  ✗ Failed to create branch: $RESULT"
    # Clean up
    api DELETE "/repos/$OWNER/$REPO" > /dev/null
    exit 1
fi

# Step 3: Add a file to the feature branch
echo "Step 3: Adding file to feature branch..."
CONTENT=$(echo "Hello from feature branch" | base64)
RESULT=$(api POST "/repos/$OWNER/$REPO/contents/test.txt" "{
    \"content\":\"$CONTENT\",
    \"message\":\"Add test file\",
    \"branch\":\"feature-test\"
}")
if echo "$RESULT" | grep -q '"commit"'; then
    echo "  ✓ File added"
else
    echo "  ✗ Failed to add file: $RESULT"
    api DELETE "/repos/$OWNER/$REPO" > /dev/null
    exit 1
fi

# Step 4: Create a pull request
echo "Step 4: Creating pull request..."
RESULT=$(api POST "/repos/$OWNER/$REPO/pulls" '{
    "title":"Test PR",
    "head":"feature-test",
    "base":"main",
    "body":"Testing merge functionality"
}')
PR_NUMBER=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('number',''))" 2>/dev/null || echo "")
if [ -n "$PR_NUMBER" ]; then
    echo "  ✓ PR #$PR_NUMBER created"
else
    echo "  ✗ Failed to create PR: $RESULT"
    api DELETE "/repos/$OWNER/$REPO" > /dev/null
    exit 1
fi

# Step 5: Check PR status
echo "Step 5: Checking PR status..."
sleep 1
RESULT=$(api GET "/repos/$OWNER/$REPO/pulls/$PR_NUMBER")
MERGEABLE=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('mergeable','unknown'))" 2>/dev/null || echo "unknown")
STATE=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('state','unknown'))" 2>/dev/null || echo "unknown")
echo "  PR state: $STATE, mergeable: $MERGEABLE"

if [ "$MERGEABLE" = "False" ] || [ "$MERGEABLE" = "false" ]; then
    echo "  ⚠ PR is not mergeable! Let's investigate..."
    echo "  Full PR data:"
    echo "$RESULT" | python3 -m json.tool 2>/dev/null || echo "$RESULT"
fi

# Step 6: Attempt to merge
echo "Step 6: Merging PR..."
RESULT=$(api POST "/repos/$OWNER/$REPO/pulls/$PR_NUMBER/merge" '{"Do":"merge","MergeMessageField":"Merge test PR"}')
if echo "$RESULT" | grep -q '"sha"'; then
    echo "  ✓ PR merged successfully!"
    MERGE_SHA=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('sha',''))" 2>/dev/null)
    echo "  Merge commit: $MERGE_SHA"
elif echo "$RESULT" | grep -q "405"; then
    echo "  ✗ Got 405 error: $RESULT"
else
    echo "  ✗ Merge failed: $RESULT"
fi

# Step 7: Clean up
echo ""
echo "Step 7: Cleaning up..."
api DELETE "/repos/$OWNER/$REPO" > /dev/null
echo "  ✓ Repository deleted"

echo ""
echo "=== Test Complete ==="
