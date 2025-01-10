#!/bin/bash

# Exit on error
set -e

# Start Docker Compose services
echo "Starting PostgreSQL and Redis..."
docker-compose up -d postgres redis

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
until docker-compose exec -T postgres pg_isready -U postgres; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 1
done

# Create database if it doesn't exist
echo "Creating database if it doesn't exist..."
docker-compose exec -T postgres psql -U postgres -tc "SELECT 1 FROM pg_database WHERE datname = 'ai_dev_team'" | grep -q 1 || \
  docker-compose exec -T postgres psql -U postgres -c "CREATE DATABASE ai_dev_team"

# Run Alembic migrations
echo "Running database migrations..."
export PYTHONPATH=$PYTHONPATH:$(pwd)
alembic upgrade head

echo "Database initialization complete!" 