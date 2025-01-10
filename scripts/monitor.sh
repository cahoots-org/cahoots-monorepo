#!/bin/bash

# Exit on error
set -e

# Function to check service health
check_service() {
    local service=$1
    local status=$(docker-compose ps -q $service)
    
    if [ -z "$status" ]; then
        echo "❌ $service is not running"
        return 1
    else
        echo "✅ $service is running"
        return 0
    fi
}

# Function to check PostgreSQL connection
check_postgres() {
    if docker-compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
        echo "✅ PostgreSQL is accepting connections"
        return 0
    else
        echo "❌ PostgreSQL is not accepting connections"
        return 1
    fi
}

# Function to check Redis connection
check_redis() {
    if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
        echo "✅ Redis is accepting connections"
        return 0
    else
        echo "❌ Redis is not accepting connections"
        return 1
    fi
}

# Function to check API health
check_api() {
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ API is healthy"
        return 0
    else
        echo "❌ API is not responding"
        return 1
    fi
}

# Main monitoring loop
while true; do
    clear
    echo "=== AI Dev Team Service Monitor ==="
    echo "Time: $(date)"
    echo "=================================="
    echo
    
    # Check services
    check_service postgres
    check_service redis
    
    # Check connections
    check_postgres
    check_redis
    check_api
    
    # Check disk space
    echo
    echo "=== Disk Space ==="
    df -h | grep -E '^Filesystem|/dev/'
    
    # Check container logs for errors
    echo
    echo "=== Recent Errors ==="
    docker-compose logs --tail=5 2>&1 | grep -i "error"
    
    # Wait before next check
    sleep 10
done 