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

## Database Migrations

Cahoots uses a custom migration tool built on top of Alembic for managing database schema changes. The tool provides a CLI interface for common migration tasks.

### Basic Usage

1. **Create a new migration**:
```bash
# Auto-generate from models
python -m cahoots_service.cli.migrate create -m "add user table"

# Create empty migration
python -m cahoots_service.cli.migrate create -m "custom migration" --no-autogenerate
```

2. **Check migration status**:
```bash
python -m cahoots_service.cli.migrate status
```

This shows:
- Current revision
- Available migrations
- Pending migrations
- Whether the database needs upgrading

3. **Apply migrations**:
```bash
# Upgrade to latest
python -m cahoots_service.cli.migrate upgrade

# Upgrade to specific revision
python -m cahoots_service.cli.migrate upgrade -t abc123
```

4. **Rollback migrations**:
```bash
# Rollback one migration
python -m cahoots_service.cli.migrate downgrade -1

# Rollback to specific revision
python -m cahoots_service.cli.migrate downgrade abc123
```

5. **Verify database state**:
```bash
python -m cahoots_service.cli.migrate verify
```

### Development Workflow

1. Make changes to your SQLAlchemy models
2. Create a new migration to capture the changes
3. Test the migration locally
4. Commit both model changes and migration files
5. When deploying, migrations run automatically during service startup

### Best Practices

- Always create migrations in a clean working directory
- Test both upgrade and downgrade paths
- Include meaningful descriptions in migration messages
- Review auto-generated migrations for accuracy
- Run migrations on a staging environment before production
- Back up the database before applying migrations in production

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
