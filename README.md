# Cahoots

AI-powered task decomposition using Event Modeling. Turn high-level project descriptions into actionable epics, user stories, and implementation tasks.

## Quick Start

```bash
# Start the stack
docker compose up -d

# Create a task
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-bypass-token" \
  -d '{"description": "Build a user authentication system"}'

# View the API docs
open http://localhost:8000/docs
```

## Features

- **Event Modeling** - Automatically generates commands, events, and read models
- **Story-driven decomposition** - Breaks projects into epics, user stories, and atomic tasks
- **Tech stack awareness** - Tailors implementation details to your chosen technologies
- **Real-time updates** - WebSocket support for live progress tracking
- **Semantic context routing** - Powered by [Contex](https://github.com/cahoots-org/contex)

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
# LLM Provider (required)
LLM_PROVIDER=cerebras
CEREBRAS_API_KEY=your_key_here

# Or use other providers
# LLM_PROVIDER=openai|groq|lambda|local|mock
```

## API

### Tasks
- `POST /api/tasks` - Create and process a new task
- `GET /api/tasks/{id}` - Get task details
- `GET /api/tasks/{id}/tree` - Get full task tree with subtasks
- `GET /api/tasks/stats` - Get task statistics

### WebSocket
- `WS /ws/global` - Real-time task processing updates

### Health
- `GET /health` - Service health check

## Architecture

```
app/
├── api/            # FastAPI routes and WebSocket handlers
├── analyzer/       # LLM-powered task analysis and decomposition
├── processor/      # Task processing pipeline
├── models/         # Pydantic data models
├── services/       # External service integrations
└── storage/        # Redis storage layer
```

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
uvicorn app.main:app --reload --port 8000

# Run tests
pytest tests/ -v
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| API | 8000 | Main application |
| Frontend | 3000 | React UI |
| Redis | 6380 | Data storage |
| Context Engine | 8003 | Semantic routing |
| OpenSearch | 9201 | Vector search |
| Gitea | 3001 | Git server for code generation |
| Workspace Service | 8010 | File operations for agents |
| Runner Service | 8011 | Test execution |
| Prometheus | 9090 | Metrics collection |
| Grafana | 3002 | Metrics dashboards |

## Monitoring

Prometheus and Grafana are included for monitoring code generation performance.

```bash
# Start monitoring stack
docker compose up -d prometheus grafana
```

**Grafana:** http://localhost:3002
- Username: `admin`
- Password: `cahoots`

A pre-built dashboard "Cahoots Code Generation" is automatically provisioned with:
- Idea-to-code duration (the headline metric)
- LLM call latency and token usage
- Task processing rates
- Merge operation stats

**Prometheus:** http://localhost:9090
- Scrapes metrics from the API at `/metrics`

## License

Proprietary - All rights reserved.
