# Cahoots Monolith Setup Guide

This guide shows you how to run the complete Cahoots system (monolith API + frontend) for testing and development.

## Quick Start (Recommended)

### Option 1: Docker Compose (Full Stack)

**Prerequisites:**
- Docker & Docker Compose installed
- 8GB+ RAM recommended

```bash
# 1. Navigate to the refactor directory
cd /home/rmiller/cahoots-decomp/refactor

# 2. Create environment file
cp .env.example .env

# 3. Edit .env file with your settings (optional for testing)
nano .env

# 4. Start the full stack
docker-compose up -d

# 5. Wait for services to be healthy (2-3 minutes)
docker-compose ps

# 6. Open the application
# Frontend: http://localhost:3000
# API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

**Services Started:**
- **Redis**: localhost:6379 (data storage)
- **API**: localhost:8000 (monolith backend)
- **Frontend**: localhost:3000 (React UI)

### Option 2: Development Mode (Hot Reload)

For active development with hot reloading:

```bash
# 1. Start backend services
docker-compose up -d redis

# 2. Run API locally
cd /home/rmiller/cahoots-decomp/refactor
python -m uvicorn app.main:app --reload --port 8000

# 3. In a new terminal, run frontend
cd /home/rmiller/cahoots-decomp/frontend
npm install
npm start

# Frontend will be available at http://localhost:3000
# API will be available at http://localhost:8000
```

## Detailed Setup Instructions

### Prerequisites Check

```bash
# Check Docker
docker --version
docker-compose --version

# Check Python (if running locally)
python --version  # Should be 3.11+

# Check Node.js (for frontend)
node --version    # Should be 16+
npm --version
```

### Environment Configuration

Create `.env` file in `/home/rmiller/cahoots-decomp/refactor/`:

```bash
# LLM Provider (for testing, use mock)
LLM_PROVIDER=mock

# For real LLM testing, uncomment one:
# LLM_PROVIDER=openai
# OPENAI_API_KEY=your_openai_key_here

# LLM_PROVIDER=groq
# GROQ_API_KEY=your_groq_key_here

# LLM_PROVIDER=lambda
# LAMBDA_API_KEY=your_lambda_key_here

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# Cache Settings
USE_SEMANTIC_CACHE=true
CACHE_TTL=3600

# Processing Settings
MAX_DEPTH=5
COMPLEXITY_THRESHOLD=0.45
BATCH_SIZE=3

# Development
ENV=development
```

### Frontend Configuration

Update `/home/rmiller/cahoots-decomp/frontend/.env` (if it exists):

```bash
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000
```

## Testing the System

### 1. Health Checks

```bash
# Check API health
curl http://localhost:8000/health

# Check API endpoints
curl http://localhost:8000/api/tasks/stats

# Check WebSocket (requires frontend)
# Open browser developer tools -> Network -> WS tab
# Navigate to http://localhost:3000
```

### 2. Create Test Tasks

**Via API (curl):**
```bash
# Simple task
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Create a hello world function in Python",
    "user_id": "test-user",
    "max_depth": 3
  }'

# Complex task
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Build a complete e-commerce platform with user management and payment processing",
    "user_id": "test-user",
    "max_depth": 5,
    "tech_preferences": {
      "backend_language": "Python",
      "frontend_framework": "React",
      "database": "PostgreSQL"
    }
  }'
```

**Via Frontend:**
1. Open http://localhost:3000
2. Click "Create New Task"
3. Enter task description
4. Submit and watch real-time decomposition

### 3. Performance Testing

```bash
# Run quick benchmark
cd /home/rmiller/cahoots-decomp/refactor
python test_benchmark.py

# Run full benchmark suite
python -m benchmarks.run_benchmarks --mode full --compare

# View results
ls benchmarks/results/
cat PERFORMANCE_REPORT.md
```

## Troubleshooting

### Common Issues

**1. Port Conflicts**
```bash
# Check what's using ports
sudo netstat -tulpn | grep :8000
sudo netstat -tulpn | grep :3000
sudo netstat -tulpn | grep :6379

# Stop conflicting services
sudo systemctl stop redis-server  # If Redis running locally
```

**2. Docker Issues**
```bash
# Restart Docker
sudo systemctl restart docker

# Clean up containers
docker-compose down -v
docker system prune -f

# Rebuild containers
docker-compose up -d --build
```

**3. Redis Connection Issues**
```bash
# Check Redis status
docker-compose logs redis

# Test Redis connection
docker-compose exec redis redis-cli ping

# Clear Redis data
docker-compose exec redis redis-cli FLUSHALL
```

**4. API Not Starting**
```bash
# Check API logs
docker-compose logs api

# Check dependencies
cd /home/rmiller/cahoots-decomp/refactor
pip install -r requirements.txt

# Run locally for debugging
python -m uvicorn app.main:app --reload --port 8000
```

**5. Frontend Issues**
```bash
# Check frontend logs
docker-compose logs frontend

# Install dependencies
cd /home/rmiller/cahoots-decomp/frontend
npm install

# Check environment
cat .env
```

### Monitoring & Logs

**View all logs:**
```bash
docker-compose logs -f
```

**View specific service logs:**
```bash
docker-compose logs -f api
docker-compose logs -f frontend
docker-compose logs -f redis
```

**Monitor resource usage:**
```bash
docker stats
```

## Development Workflow

### Making Changes

**Backend changes:**
1. Edit files in `/home/rmiller/cahoots-decomp/refactor/app/`
2. If using Docker: `docker-compose restart api`
3. If running locally: Auto-reload with `--reload` flag

**Frontend changes:**
1. Edit files in `/home/rmiller/cahoots-decomp/frontend/src/`
2. Changes auto-reload in development mode

### Adding New Features

1. **API Endpoint**: Add to `/app/api/routes/`
2. **Models**: Add to `/app/models/`
3. **Business Logic**: Add to `/app/processor/` or `/app/analyzer/`
4. **Tests**: Add to `/tests/unit/` or `/tests/integration/`
5. **Frontend**: Update React components

### Running Tests

```bash
# Unit tests
cd /home/rmiller/cahoots-decomp/refactor
python -m pytest tests/unit/ -v

# Integration tests
python -m pytest tests/integration/ -v

# Frontend tests (if available)
cd /home/rmiller/cahoots-decomp/frontend
npm test
```

## Production Deployment

### Docker Compose Production

```bash
# Use production compose file
docker-compose -f docker-compose.prod.yml up -d

# Or set production environment
ENV=production docker-compose up -d
```

### Environment Variables for Production

```bash
# Use real LLM provider
LLM_PROVIDER=openai
OPENAI_API_KEY=your_production_key

# Secure Redis
REDIS_PASSWORD=your_secure_password

# Disable debug features
ENV=production
USE_SEMANTIC_CACHE=true
CACHE_TTL=86400
```

## URLs & Endpoints

Once running, access these URLs:

- **Frontend**: http://localhost:3000
- **API Root**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Task Stats**: http://localhost:8000/api/tasks/stats
- **WebSocket**: ws://localhost:8000/ws/global
- **Redis**: localhost:6379

## Support

If you encounter issues:

1. Check this guide first
2. Review logs: `docker-compose logs -f`
3. Test individual components
4. Check the troubleshooting section
5. Verify environment configuration

The system is designed to be robust and should work out-of-the-box with the provided configuration.

Happy testing! 🚀