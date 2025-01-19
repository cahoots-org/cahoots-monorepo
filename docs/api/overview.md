# API Overview

## Introduction
The Cahoots API provides a RESTful interface for managing AI-powered software development workflows. This document provides a comprehensive overview of the API's capabilities, authentication mechanisms, and best practices.

## Base URL
```
Production: https://api.aidevteam.com/v1
Staging: https://api-staging.aidevteam.com/v1
Development: http://localhost:8000/v1
```

## Authentication
All API requests require authentication using an API key. Include the key in the `X-API-Key` header:
```bash
curl -H "X-API-Key: your_api_key" https://api.aidevteam.com/v1/health
```

## Rate Limiting
- Default: 60 requests per minute
- Burst: 10 requests
- Headers:
  - `X-RateLimit-Limit`: Total requests allowed
  - `X-RateLimit-Remaining`: Requests remaining
  - `X-RateLimit-Reset`: Time until limit resets
  - `X-RateLimit-Window`: Rate limit window size

## Common Headers
```http
Content-Type: application/json
Accept: application/json
X-API-Key: your_api_key
X-Request-ID: unique_request_id
```

## Response Format
All responses are JSON formatted:
```json
{
    "status": "success",
    "data": {
        // Response data
    },
    "meta": {
        "timestamp": "2024-02-20T12:00:00Z",
        "request_id": "req_123abc"
    }
}
```

## Error Handling
Error responses follow RFC 7807 (Problem Details for HTTP APIs):
```json
{
    "type": "https://api.aidevteam.com/errors/rate_limit_exceeded",
    "title": "Rate Limit Exceeded",
    "status": 429,
    "detail": "Request quota exceeded. Please wait 60 seconds.",
    "instance": "/messages/system"
}
```

## Core Resources

### Health Check
```http
GET /health
```
Returns system health status and component states.

### Projects
```http
POST /projects
GET /projects
GET /projects/{id}
PUT /projects/{id}
DELETE /projects/{id}
```
Manage development projects and their configurations.

### Messages
```http
POST /messages/{channel}
GET /messages/{channel}
```
Publish and subscribe to system messages.

### Agents
```http
GET /agents
GET /agents/{id}/status
POST /agents/{id}/tasks
```
Interact with AI development agents.

## Versioning
- API version in URL path (/v1, /v2)
- Breaking changes trigger version increment
- Supported versions:
  - v1: Current
  - v0: Deprecated, sunset date 2024-12-31

## Best Practices

### Request IDs
Include a unique request ID in the `X-Request-ID` header for tracing:
```bash
curl -H "X-Request-ID: $(uuidgen)" https://api.aidevteam.com/v1/health
```

### Pagination
Use offset pagination for list endpoints:
```http
GET /projects?limit=10&offset=0
```

Response includes pagination metadata:
```json
{
    "data": [...],
    "meta": {
        "total": 100,
        "limit": 10,
        "offset": 0,
        "next": "/projects?limit=10&offset=10"
    }
}
```

### Filtering
Use query parameters for filtering:
```http
GET /projects?status=active&type=backend
```

### Sorting
Use `sort` parameter with field and direction:
```http
GET /projects?sort=created_at:desc
```

### Field Selection
Use `fields` parameter to select specific fields:
```http
GET /projects?fields=id,name,status
```

## WebSocket API
Available at `wss://api.aidevteam.com/v1/ws`:
```javascript
const ws = new WebSocket('wss://api.aidevteam.com/v1/ws');
ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    console.log('Received:', message);
};
```

## SDK Support
Official SDKs available for:
- Python: `pip install cahoots`
- JavaScript: `npm install cahoots`
- Go: `go get github.com/aidevteam/sdk-go`

## API Changelog
- 2024-02-20: Added WebSocket support
- 2024-01-15: Added field selection
- 2024-01-01: Initial v1 release

## Support
- Documentation: https://docs.aidevteam.com
- Issues: https://github.com/aidevteam/api/issues
- Email: api-support@aidevteam.com
- Status: https://status.aidevteam.com 