# AI Dev Team API

An AI-powered development team that automates software development tasks through a RESTful API.

## Features

- Project Management
- Task Automation
- Code Generation
- Code Review
- Testing
- Continuous Integration/Deployment

## Quick Start

### Prerequisites

- Python 3.10+
- Redis
- Docker (optional)
- Kubernetes (optional)

### Local Development

1. Clone the repository:
```bash
git clone https://github.com/yourusername/ai-dev-team.git
cd ai-dev-team
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
.\venv\Scripts\activate   # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Run the development server:
```bash
uvicorn src.api.main:app --reload
```

The API will be available at http://localhost:8000

### Docker Deployment

Build and run using Docker:

```bash
docker build -t ai-dev-team .
docker run -p 8000:8000 --env-file .env ai-dev-team
```

### Kubernetes Deployment

1. Create the necessary secrets:
```bash
kubectl create secret generic ai-dev-team-secrets \
  --from-file=.env
```

2. Deploy the application:
```bash
kubectl apply -f k8s/
```

## API Documentation

API documentation is available at:
- Swagger UI: `/docs`
- ReDoc: `/redoc`
- OpenAPI Spec: `/openapi.json`

### Authentication

All API endpoints require authentication using an API key header:

```http
X-API-Key: your-api-key
```

### Example Request

Create a new project:

```bash
curl -X POST http://localhost:8000/projects \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "project-123",
    "name": "My Project",
    "description": "A new project"
  }'
```

## Configuration

Configuration is managed through:
1. Environment variables
2. YAML configuration files in `config/`
3. Command-line arguments

See `.env.example` for available environment variables.

## Architecture

### Components

- FastAPI web server
- Redis message broker
- Prometheus metrics
- Kubernetes deployment
- GitHub integration
- Trello integration

### Directory Structure

```
.
├── config/             # Configuration files
├── k8s/               # Kubernetes manifests
├── scripts/           # Utility scripts
├── src/               # Source code
│   ├── api/          # API endpoints
│   ├── agents/       # AI agents
│   ├── models/       # Data models
│   ├── services/     # External services
│   └── utils/        # Utilities
└── tests/            # Test suite
```

## Development

### Testing

Run tests with pytest:

```bash
pytest
```

With coverage:

```bash
pytest --cov=src --cov-report=html
```

### Code Quality

Run linters and type checks:

```bash
ruff check .
mypy src tests
```

### CI/CD

The project uses GitHub Actions for:
1. Running tests
2. Code quality checks
3. Security scanning
4. Building Docker images
5. Deploying to staging/production

## Monitoring

### Metrics

Prometheus metrics are available at `/metrics`, including:
- Request counts
- Request latency
- Redis operations
- Custom business metrics

### Logging

Structured JSON logging is configured for production with:
- Request tracking
- Error tracking
- Performance monitoring

## Security

- API key authentication
- Rate limiting
- Input validation
- CORS protection
- Security headers
- Non-root containers

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.
