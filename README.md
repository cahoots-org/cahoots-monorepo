# Cahoots

An AI-powered development team that collaborates to build software solutions through microservices.

## Services

- **Master**: Orchestrates and coordinates the Cahoots AI services
- **Project Manager**: Handles project planning and task management
- **Developer**: Implements code changes and reviews
- **UX Designer**: Handles UI/UX related tasks
- **Tester**: Manages testing and quality assurance
- **Context Manager**: Maintains project context and documentation

## Tech Stack

- Python 3.11+
- FastAPI
- PostgreSQL
- Redis
- AWS (ECS, ECR, RDS)
- Terraform
- GitHub Actions

## Development Setup

1. Install dependencies:
```bash
python -m pip install -r requirements.txt
```

2. Install development dependencies:
```bash
python -m pip install -e ".[test]"
```

3. Set up environment variables:
```bash
export ENV=development
export REDIS_HOST=localhost
export REDIS_PORT=6379
```

## Testing

Run the test suite:
```bash
pytest --cov=packages --cov-report=term-missing
```

## Infrastructure

Cahoots uses Terraform to manage infrastructure across three environments:
- Development
- Staging
- Production

### Environment Configuration

Each environment has its own configuration:
- `.tfvars` file for environment-specific variables
- `.tfbackend` file for state management
- Separate VPC and networking setup
- Scaled resources appropriate for each environment

## CI/CD Pipeline

Cahoots uses GitHub Actions for CI/CD with the following stages:

1. **Test**
   - Runs Python tests
   - Uploads coverage reports
   - Uses Redis service container

2. **Lint**
   - Ruff for linting
   - MyPy for type checking

3. **Security**
   - Bandit security scanner
   - Safety dependency checker

4. **Build**
   - Builds Docker images for all services
   - Pushes to Amazon ECR

5. **Deploy**
   - Staging deployment with Terraform
   - Production deployment after staging success
   - Updates ECS services

## Project Structure

```
.
├── packages/
│   ├── core/       # Core functionality
│   ├── events/     # Event handling
│   ├── context/    # Context management
│   ├── service/    # Service implementations
│   └── agents/     # AI agent implementations
├── tests/          # Test suites
├── terraform/      # Infrastructure as code
└── docker/         # Dockerfiles for services
```

## Contributing

1. Create a feature branch from `main`
2. Make your changes
3. Run tests and linting
4. Submit a pull request

## License

[Add your license here]
