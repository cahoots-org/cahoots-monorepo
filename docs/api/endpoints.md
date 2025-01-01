# API Endpoints Reference

## Health Check

### GET /health
Get system health status.

**Response 200**
```json
{
    "status": "healthy",
    "environment": "production",
    "version": "1.0.0",
    "uptime_seconds": 3600,
    "system_metrics": {
        "cpu_percent": 45.2,
        "memory_percent": 62.8,
        "disk_percent": 38.5,
        "open_file_descriptors": 256
    },
    "services": {
        "redis": {
            "status": "healthy",
            "latency_ms": 1.2,
            "last_check": "2024-02-20T12:00:00Z"
        }
    }
}
```

## Projects

### POST /projects
Create a new project.

**Request**
```json
{
    "name": "AI Chat Bot",
    "description": "An AI-powered chat bot for customer service",
    "type": "backend",
    "settings": {
        "language": "python",
        "framework": "fastapi"
    }
}
```

**Response 201**
```json
{
    "id": "proj_123abc",
    "name": "AI Chat Bot",
    "description": "An AI-powered chat bot for customer service",
    "type": "backend",
    "settings": {
        "language": "python",
        "framework": "fastapi"
    },
    "created_at": "2024-02-20T12:00:00Z",
    "status": "created"
}
```

### GET /projects
List all projects.

**Parameters**
- `limit` (int): Number of items per page (default: 10, max: 100)
- `offset` (int): Offset for pagination (default: 0)
- `status` (string): Filter by status (active, archived, deleted)
- `type` (string): Filter by project type
- `sort` (string): Sort field and direction (e.g., created_at:desc)
- `fields` (string): Comma-separated list of fields to return

**Response 200**
```json
{
    "data": [
        {
            "id": "proj_123abc",
            "name": "AI Chat Bot",
            "status": "active",
            "created_at": "2024-02-20T12:00:00Z"
        }
    ],
    "meta": {
        "total": 42,
        "limit": 10,
        "offset": 0,
        "next": "/projects?limit=10&offset=10"
    }
}
```

### GET /projects/{id}
Get project details.

**Parameters**
- `id` (string): Project ID
- `fields` (string): Comma-separated list of fields to return

**Response 200**
```json
{
    "id": "proj_123abc",
    "name": "AI Chat Bot",
    "description": "An AI-powered chat bot for customer service",
    "type": "backend",
    "settings": {
        "language": "python",
        "framework": "fastapi"
    },
    "created_at": "2024-02-20T12:00:00Z",
    "updated_at": "2024-02-20T12:30:00Z",
    "status": "active",
    "metrics": {
        "tasks_completed": 10,
        "tasks_pending": 5
    }
}
```

## Messages

### POST /messages/{channel}
Publish a message to a channel.

**Parameters**
- `channel` (string): Channel name (system, project_manager, developer, etc.)

**Request**
```json
{
    "type": "task_created",
    "payload": {
        "task_id": "task_123",
        "project_id": "proj_123abc",
        "description": "Implement login API",
        "priority": "high"
    }
}
```

**Response 202**
```json
{
    "id": "msg_456def",
    "channel": "system",
    "type": "task_created",
    "timestamp": "2024-02-20T12:00:00Z",
    "status": "published"
}
```

### GET /messages/{channel}
Subscribe to messages from a channel (WebSocket).

**Connection**
```javascript
const ws = new WebSocket('wss://api.aidevteam.com/v1/messages/system');
ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    console.log('Received:', message);
};
```

**Message Format**
```json
{
    "id": "msg_456def",
    "channel": "system",
    "type": "task_created",
    "timestamp": "2024-02-20T12:00:00Z",
    "payload": {
        "task_id": "task_123",
        "project_id": "proj_123abc",
        "description": "Implement login API",
        "priority": "high"
    }
}
```

## Agents

### GET /agents
List available agents.

**Response 200**
```json
{
    "data": [
        {
            "id": "agent_789ghi",
            "type": "developer",
            "status": "active",
            "capabilities": [
                "python",
                "fastapi",
                "testing"
            ],
            "current_task": "task_123"
        }
    ]
}
```

### GET /agents/{id}/status
Get agent status.

**Parameters**
- `id` (string): Agent ID

**Response 200**
```json
{
    "id": "agent_789ghi",
    "type": "developer",
    "status": "active",
    "current_task": "task_123",
    "metrics": {
        "tasks_completed": 42,
        "average_completion_time": 300,
        "success_rate": 0.95
    },
    "last_active": "2024-02-20T12:00:00Z"
}
```

### POST /agents/{id}/tasks
Assign a task to an agent.

**Parameters**
- `id` (string): Agent ID

**Request**
```json
{
    "task_id": "task_123",
    "type": "implementation",
    "description": "Implement login API",
    "requirements": [
        "Use JWT authentication",
        "Include rate limiting"
    ],
    "priority": "high"
}
```

**Response 202**
```json
{
    "task_id": "task_123",
    "agent_id": "agent_789ghi",
    "status": "assigned",
    "estimated_completion": "2024-02-20T13:00:00Z"
}
```

## Error Responses

### 400 Bad Request
```json
{
    "type": "https://api.aidevteam.com/errors/validation_error",
    "title": "Validation Error",
    "status": 400,
    "detail": "Invalid project name",
    "errors": [
        {
            "field": "name",
            "message": "Must be between 3 and 50 characters"
        }
    ]
}
```

### 401 Unauthorized
```json
{
    "type": "https://api.aidevteam.com/errors/unauthorized",
    "title": "Unauthorized",
    "status": 401,
    "detail": "Invalid API key"
}
```

### 429 Too Many Requests
```json
{
    "type": "https://api.aidevteam.com/errors/rate_limit_exceeded",
    "title": "Rate Limit Exceeded",
    "status": 429,
    "detail": "Request quota exceeded. Please wait 60 seconds.",
    "retry_after": 60
}
```

### 500 Internal Server Error
```json
{
    "type": "https://api.aidevteam.com/errors/internal_error",
    "title": "Internal Server Error",
    "status": 500,
    "detail": "An unexpected error occurred",
    "request_id": "req_123abc"
}
``` 