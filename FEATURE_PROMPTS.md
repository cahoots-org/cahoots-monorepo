# Feature Prompts for Testing (Existing Codebase)

These prompts are designed to test the "add feature to existing codebase" flow when a GitHub repo is connected. Each should generate a **minimal, focused** breakdown that follows existing patterns.

---

## Integration Features

### 1. Linear Integration
```
Add an integration for Linear.app for exporting tasks (similar to our Jira and Trello integrations)
```

### 2. Asana Integration
```
Add an Asana integration for exporting tasks, following the same patterns as our existing Jira and Trello integrations
```

### 3. GitHub Issues Export
```
Add the ability to export tasks directly to GitHub Issues in a connected repository
```

### 4. Notion Integration
```
Add a Notion integration that exports the task breakdown as a Notion database
```

### 5. Slack Notifications
```
Add Slack notifications when a task analysis completes (similar to how we handle WebSocket events)
```

---

## UI/UX Features

### 6. Dark Mode
```
Add a dark mode toggle to the application settings
```

### 7. Task Search
```
Add a search bar to filter tasks by title or description on the project view page
```

### 8. Keyboard Shortcuts
```
Add keyboard shortcuts for common actions (e.g., 'n' for new task, '/' for search, 'esc' to close modals)
```

### 9. Task Drag & Drop
```
Add drag and drop reordering of tasks within the task list
```

### 10. Collapsible Chapters
```
Add the ability to collapse/expand chapters in the Event Model view
```

---

## Export & Reporting Features

### 11. PDF Export
```
Add a PDF export option for the complete task breakdown and event model
```

### 12. CSV Export
```
Add CSV export for the task list with all metadata (story, epic, status, priority)
```

### 13. Markdown Export
```
Add a "Copy as Markdown" button that copies the task breakdown in a format suitable for pasting into GitHub issues or documentation
```

### 14. Shareable Links
```
Add the ability to generate a shareable public link for a project's task breakdown (read-only)
```

---

## Task Management Features

### 15. Task Status Updates
```
Add the ability to mark tasks as "In Progress", "Done", or "Blocked" directly from the UI
```

### 16. Task Estimates
```
Add story point estimation to tasks with a simple dropdown (1, 2, 3, 5, 8, 13)
```

### 17. Task Dependencies
```
Add the ability to mark task dependencies (this task blocks/is blocked by another task)
```

### 18. Task Comments
```
Add a simple commenting system on individual tasks for collaboration notes
```

### 19. Task Assignees
```
Add the ability to assign tasks to team members (using email or name)
```

---

## Analysis Enhancement Features

### 20. Tech Stack Detection
```
Add automatic tech stack detection from the connected GitHub repository (detect languages, frameworks, and suggest appropriate implementation patterns)
```

### 21. Complexity Scoring
```
Add a complexity score to each task based on the implementation details (Simple, Medium, Complex)
```

### 22. Risk Flags
```
Add automatic flagging of high-risk tasks (security-related, payment-related, data migration)
```

### 23. Similar Task Detection
```
Add detection for potentially duplicate or overlapping tasks within a project breakdown
```

---

## API & Automation Features

### 24. Webhook Support
```
Add webhook support to notify external services when a project analysis completes
```

### 25. API Key Management
```
Add API key management so users can programmatically create and retrieve task breakdowns
```

### 26. Bulk Task Creation
```
Add a bulk task creation endpoint that accepts a list of descriptions and returns breakdowns for all
```

---

## User Experience Features

### 27. Onboarding Tour
```
Add a guided onboarding tour for new users that highlights key features
```

### 28. Recent Projects
```
Add a "Recent Projects" section to the dashboard showing the last 5 viewed projects
```

### 29. Project Templates
```
Add project templates for common scenarios (SaaS app, mobile app, API service, CLI tool)
```

### 30. Favorites
```
Add the ability to favorite/star projects for quick access
```

---

## Performance & Quality Features

### 31. Caching Layer
```
Add Redis caching for completed task analyses to speed up repeat views
```

### 32. Rate Limiting
```
Add rate limiting to the task creation endpoint (5 requests per minute per user)
```

### 33. Request Logging
```
Add structured logging for all API requests with duration, status, and user info
```

---

## Expected Results

When testing with a connected GitHub repo, each prompt should generate:

| Feature Type | Expected Epics | Expected Stories | Expected Tasks |
|--------------|----------------|------------------|----------------|
| Integration (like Jira/Trello) | 1 | 2-4 | 8-15 |
| UI Feature (dark mode, search) | 1 | 1-3 | 5-12 |
| Export Feature | 1 | 1-2 | 4-10 |
| API Feature | 1 | 2-3 | 6-12 |

**Key indicators of success:**
- No subscription/payment handling unless requested
- No admin dashboards unless requested
- No scheduling systems unless requested
- Commands match the feature scope exactly
- References to existing patterns in the codebase

---

## Testing Commands

```bash
# Test with Linear integration
curl -X POST 'http://localhost:8000/api/tasks' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer dev-bypass-token' \
  -d '{"description": "Add an integration for Linear.app for exporting tasks (similar to our Jira and Trello integrations)", "github_repo_url": "https://github.com/cahoots-org/cahoots-monorepo"}'

# Test with dark mode
curl -X POST 'http://localhost:8000/api/tasks' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer dev-bypass-token' \
  -d '{"description": "Add a dark mode toggle to the application settings", "github_repo_url": "https://github.com/cahoots-org/cahoots-monorepo"}'

# Test with PDF export
curl -X POST 'http://localhost:8000/api/tasks' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer dev-bypass-token' \
  -d '{"description": "Add a PDF export option for the complete task breakdown and event model", "github_repo_url": "https://github.com/cahoots-org/cahoots-monorepo"}'
```
