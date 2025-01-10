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

## Stripe Integration

### Local Development Setup

1. Install required tools:
```bash
brew install stripe/stripe-cli/stripe
brew install ngrok
```

2. Configure environment variables in `.env`:
```
STRIPE_SECRET_KEY=sk_test_your_test_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
```

3. Start your local development server:
```bash
source venv/bin/activate
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

4. Create a tunnel to your local server:
```bash
ngrok http 8000
```

5. Configure webhook in Stripe Dashboard:
   - Go to Developers > Webhooks
   - Add endpoint: `https://your-ngrok-url/webhook/stripe`
   - Select events:
     - customer.subscription.created
     - customer.subscription.updated
     - customer.subscription.deleted
     - invoice.paid
     - invoice.payment_failed
     - payment_intent.succeeded
     - payment_intent.payment_failed

6. Test webhooks using Stripe CLI:
```bash
# Login to Stripe
stripe login

# Test specific events
stripe trigger customer.subscription.created
stripe trigger invoice.paid
stripe trigger invoice.payment_failed
```

### Production Deployment

1. Configure environment variables on your production server:
```
STRIPE_SECRET_KEY=sk_live_your_live_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
```

2. Configure webhook in Stripe Dashboard:
   - Go to Developers > Webhooks
   - Add endpoint: `https://your-production-domain/webhook/stripe`
   - Select the same events as in development
   - Store the webhook signing secret securely
   - Update your deployment configuration with the new secret

3. Security considerations:
   - Always use HTTPS for webhook endpoints
   - Keep webhook signing secrets secure
   - Rotate secrets periodically
   - Monitor webhook events in Stripe Dashboard
   - Set up retry rules for failed webhook deliveries

4. Monitoring and logging:
   - Monitor webhook delivery in Stripe Dashboard
   - Check application logs for webhook processing
   - Set up alerts for webhook failures
   - Monitor subscription and payment events

### Testing Webhook Integration

1. Local testing:
```bash
# Start local server
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# In another terminal, start ngrok
ngrok http 8000

# In another terminal, trigger test events
stripe trigger customer.subscription.created
```

2. Webhook event types for testing:
```bash
# Subscription events
stripe trigger customer.subscription.created
stripe trigger customer.subscription.updated
stripe trigger customer.subscription.deleted

# Payment events
stripe trigger invoice.paid
stripe trigger invoice.payment_failed
stripe trigger payment_intent.succeeded
stripe trigger payment_intent.payment_failed
```

3. Verify webhook processing:
   - Check application logs
   - Verify database updates
   - Check Stripe Dashboard events
   - Monitor event system messages

### Troubleshooting

1. Webhook failures:
   - Verify webhook signing secret
   - Check endpoint URL configuration
   - Ensure server is accessible
   - Check application logs
   - Verify event handling logic

2. Common issues:
   - Invalid webhook signatures
   - Server not accessible
   - Missing event handlers
   - Database connection issues
   - Redis connection issues

3. Debug tools:
   - Stripe CLI logs
   - Application logs
   - Stripe Dashboard webhook logs
   - Database transaction logs
