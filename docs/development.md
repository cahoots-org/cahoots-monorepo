# Development Guide

This guide provides detailed information for developers working on the Cahoots API.

## Development Environment Setup

### Required Tools

- Python 3.11+
- Redis 7.2+
- Docker
- kubectl (for Kubernetes development)
- Git
- Visual Studio Code (recommended)

### VS Code Extensions

We recommend the following extensions:
- Python
- Pylance
- Docker
- YAML
- Kubernetes
- GitLens
- Python Test Explorer
- Python Debugger
- GitHub Copilot
- Better Comments
- Error Lens
- Remote Development

### Dependencies

Core system dependencies:
- Redis for event system and caching
- PostgreSQL 16+ for data storage
- Argon2 for secure password hashing

Python dependencies are managed through requirements.txt and include:
- FastAPI for API development
- SQLAlchemy for database operations
- Pydantic for data validation
- Argon2-cffi for password hashing
- Redis[hiredis] for caching and events

### Environment Setup

1. Install Python dependencies:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. Install pre-commit hooks:
```bash
pip install pre-commit
pre-commit install
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

## Code Organization

### Project Structure

```
src/
├── api/                 # API endpoints and OpenAPI specs
├── agents/             # AI agent implementations
├── models/             # Data models and schemas
├── services/           # External service integrations
└── utils/              # Shared utilities
```

### Module Responsibilities

- `api/`: HTTP endpoints, request/response models, middleware
- `agents/`: AI agent logic, task processing
- `models/`: Pydantic models, database schemas
- `services/`: External API clients (GitHub, Trello)
- `utils/`: Shared functionality (logging, config, events)

## Coding Standards

### Python Style Guide

- Follow PEP 8
- Use type hints
- Maximum line length: 100 characters
- Use docstrings for all public functions/classes

### Example Function

```python
from typing import Optional, Dict, Any

def process_data(
    input_data: Dict[str, Any],
    options: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Process input data with optional configuration.

    Args:
        input_data: Data to process
        options: Optional processing configuration

    Returns:
        Processed data dictionary

    Raises:
        ValueError: If input_data is invalid
    """
    if not input_data:
        raise ValueError("Input data cannot be empty")

    result = {
        "processed": True,
        "data": input_data
    }

    if options:
        result.update({"options": options})

    return result
```

### Code Organization

- One class per file (with exceptions for small related classes)
- Group related functionality in modules
- Use `__init__.py` for public interfaces

## Testing

### Test Organization

```
tests/
├── conftest.py         # Shared fixtures
├── api/               # API tests
├── agents/            # Agent tests
├── services/          # Service tests
└── utils/             # Utility tests
```

### Writing Tests

1. Use descriptive test names:
```python
async def test_create_project_with_valid_data_succeeds():
    ...

async def test_create_project_with_missing_fields_fails():
    ...
```

2. Use fixtures for common setup:
```python
@pytest.fixture
async def mock_github():
    with patch("src.services.github_service.GitHubClient") as mock:
        yield mock

async def test_create_pr(mock_github):
    ...
```

3. Test edge cases and error conditions:
```python
async def test_create_project_handles_redis_connection_error():
    ...
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/api/test_main.py

# Run with coverage
pytest --cov=src --cov-report=html

# Run only marked tests
pytest -m "not slow"
```

## API Development

### Adding New Endpoints

1. Define request/response models:
```python
class NewFeatureRequest(BaseModel):
    name: str
    config: Dict[str, Any]

class NewFeatureResponse(BaseModel):
    id: str
    status: str
```

2. Implement endpoint:
```python
@app.post(
    "/features",
    response_model=NewFeatureResponse,
    tags=["Features"]
)
async def create_feature(
    request: NewFeatureRequest,
    api_key: str = Depends(verify_api_key)
):
    ...
```

3. Add tests:
```python
async def test_create_feature_endpoint():
    ...
```

### Documentation

- Use detailed docstrings
- Include request/response examples
- Document error conditions
- Update OpenAPI schema

## Deployment

### Local Development

```bash
uvicorn src.api.main:app --reload
```

### Docker Development

```bash
docker build -t cahoots:dev .
docker run -p 8000:8000 --env-file .env cahoots:dev
```

### Kubernetes Development

1. Build and push image:
```bash
docker build -t ghcr.io/org/cahoots:dev .
docker push ghcr.io/org/cahoots:dev
```

2. Deploy to development cluster:
```bash
kubectl apply -f k8s/dev/
```

## Debugging

### Local Debugging

1. VS Code launch configuration:
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: FastAPI",
            "type": "python",
            "request": "launch",
            "module": "uvicorn",
            "args": [
                "src.api.main:app",
                "--reload"
            ],
            "jinja": true
        }
    ]
}
```

2. Debug logging:
```python
logger.debug(
    "Processing request",
    request_id=request_id,
    data=data
)
```

### Production Debugging

1. Access logs:
```bash
kubectl logs -f deployment/cahoots
```

2. Shell into container:
```bash
kubectl exec -it deployment/cahoots -- /bin/bash
```

## Performance Optimization

### Profiling

1. Install profiling tools:
```bash
pip install py-spy
```

2. Generate profile:
```bash
py-spy record -o profile.svg -- python -m uvicorn src.api.main:app
```

### Monitoring

1. Check metrics:
```bash
curl http://localhost:8000/metrics
```

2. Monitor Redis:
```bash
redis-cli monitor
```

## Troubleshooting

### Common Issues

1. Redis Connection:
```python
try:
    await redis.ping()
except ConnectionError:
    logger.error("Redis connection failed")
```

2. API Authentication:
```python
if "X-API-Key" not in request.headers:
    raise HTTPException(status_code=401)
```

### Getting Help

1. Check logs:
```bash
tail -f logs/app.log
```

2. Review metrics:
```bash
curl http://localhost:8000/metrics | grep error
``` 