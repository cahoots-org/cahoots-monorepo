# Production Runbook

## System Overview
The AI Development Team system consists of several key components:
- FastAPI application servers
- Redis for message queuing and caching
- AI agent workers
- Prometheus for metrics
- External service integrations (GitHub, Trello)

## Common Operations

### Starting the System
1. Ensure configuration is correct:
   ```bash
   # Verify configuration files
   ls config/*.yaml
   # Verify environment variables
   source .env && env | grep 'AI_'
   ```

2. Start Redis:
   ```bash
   # Check Redis status
   redis-cli ping
   # Start if needed
   systemctl start redis
   ```

3. Start application servers:
   ```bash
   uvicorn src.api.main:app --workers 4 --host 0.0.0.0 --port 8000
   ```

### Stopping the System
1. Graceful shutdown of application servers:
   ```bash
   # Send SIGTERM to uvicorn workers
   pkill -TERM uvicorn
   ```

2. Wait for connections to drain (30s default)

3. Stop Redis:
   ```bash
   systemctl stop redis
   ```

## Health Checks

### System Health
```bash
# Check overall system health
curl http://localhost:8000/health

# Check Redis connection
redis-cli ping

# Check metrics endpoint
curl http://localhost:8000/metrics
```

### Log Monitoring
```bash
# Application logs
tail -f /var/log/ai_dev_team/app.log

# Redis logs
tail -f /var/log/redis/redis.log

# System metrics
htop
```

## Common Issues and Solutions

### High CPU Usage
1. Check which processes are consuming CPU:
   ```bash
   top -c
   ```

2. Check application metrics:
   ```bash
   curl http://localhost:8000/metrics | grep cpu
   ```

3. Solutions:
   - Scale horizontally by adding more workers
   - Check for long-running transactions
   - Review Redis connection pool settings

### Memory Issues
1. Check memory usage:
   ```bash
   free -m
   ps aux --sort=-%mem | head
   ```

2. Solutions:
   - Increase worker memory limits
   - Check for memory leaks
   - Adjust Redis maxmemory settings

### Redis Connection Issues
1. Check Redis status:
   ```bash
   redis-cli info | grep connected
   ```

2. Check connection pool metrics:
   ```bash
   curl http://localhost:8000/metrics | grep redis_pool
   ```

3. Solutions:
   - Verify Redis configuration
   - Check network connectivity
   - Adjust connection pool settings

### High Response Times
1. Check response time metrics:
   ```bash
   curl http://localhost:8000/metrics | grep http_request_duration
   ```

2. Solutions:
   - Scale horizontally
   - Check database queries
   - Review caching strategy

## Maintenance Tasks

### Backup Procedures
1. Redis backup:
   ```bash
   # Trigger RDB snapshot
   redis-cli BGSAVE
   
   # Copy snapshot file
   cp /var/lib/redis/dump.rdb /backup/redis/
   ```

2. Configuration backup:
   ```bash
   # Backup config files
   tar -czf /backup/config_$(date +%Y%m%d).tar.gz config/
   ```

### Updating the System
1. Pull latest changes:
   ```bash
   git pull origin main
   ```

2. Update dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run migrations if needed:
   ```bash
   alembic upgrade head
   ```

4. Restart services:
   ```bash
   systemctl restart ai_dev_team
   ```

## Monitoring and Alerts

### Key Metrics to Watch
- CPU usage > 80%
- Memory usage > 90%
- Response time p95 > 500ms
- Error rate > 1%
- Redis connection pool utilization > 80%

### Alert Response
1. Acknowledge alert in monitoring system
2. Check relevant metrics and logs
3. Apply solutions from troubleshooting guide
4. Document incident and resolution
5. Update runbook if needed

## Security Procedures

### Rotating Credentials
1. Generate new credentials
2. Update configuration
3. Deploy changes
4. Verify system functionality
5. Revoke old credentials

### Security Incidents
1. Isolate affected systems
2. Assess impact
3. Apply security patches
4. Update credentials
5. Document incident
6. Report to security team

## Contact Information

### On-Call Rotation
- Primary: [Contact Info]
- Secondary: [Contact Info]
- Manager: [Contact Info]

### External Services
- Redis Support: [Contact Info]
- Cloud Provider Support: [Contact Info]
- Security Team: [Contact Info] 