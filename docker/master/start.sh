#!/bin/bash
set -e

# Function to check if postgres is ready
wait_for_postgres() {
    echo "Waiting for database to be ready..."
    for i in {1..30}; do
        if pg_isready -h db -p 5432 -U cahoots; then
            echo "Database is ready!"
            return 0
        fi
        echo "Waiting for database... $i/30"
        sleep 1
    done
    echo "Database connection timeout"
    return 1
}

# Function to run migrations with retries
run_migrations() {
    local max_attempts=3
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        echo "Running database migrations (attempt $attempt/$max_attempts)..."
        if python -m cahoots_service.cli.migrate verify && \
           python -m cahoots_service.cli.migrate upgrade; then
            echo "Migrations completed successfully!"
            return 0
        else
            echo "Migration attempt $attempt failed"
            if [ $attempt -eq $max_attempts ]; then
                echo "All migration attempts failed"
                return 1
            fi
            echo "Retrying in 5 seconds..."
            sleep 5
        fi
        attempt=$((attempt + 1))
    done
}

# Main execution
echo "Starting service initialization..."

# Wait for database
if ! wait_for_postgres; then
    echo "Failed to connect to database"
    exit 1
fi

# Change to the working directory
cd /app

# Run migrations
if ! run_migrations; then
    echo "Migration failed after all attempts"
    exit 1
fi

# Print migration status
python -m cahoots_service.cli.migrate status

# Start the API server
echo "Starting API server..."
exec python -m uvicorn cahoots_service.api.main:app --host 0.0.0.0 --port 8000 --reload 
