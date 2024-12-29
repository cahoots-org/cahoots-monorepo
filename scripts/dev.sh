#!/bin/bash

# Exit on error
set -e

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
source venv/bin/activate || . venv/Scripts/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export ENV=local

# Check if .env.local exists, otherwise check environment variables
if [ ! -f ".env.$ENV" ]; then
    if [ -z "$GITHUB_API_KEY" ] || [ -z "$TRELLO_API_KEY" ] || [ -z "$TRELLO_API_SECRET" ] || [ -z "$HUGGINGFACE_API_KEY" ]; then
        echo "No .env.local file found and environment variables not set. You can either:"
        echo "1. Create a .env.local file with your API keys (recommended)"
        echo "2. Set the environment variables directly"
        echo ""
        echo "Required variables (see .env for template):"
        echo "GITHUB_API_KEY=your_github_token_here"
        echo "TRELLO_API_KEY=your_trello_api_key_here" 
        echo "TRELLO_API_SECRET=your_trello_secret_here"
        echo "HUGGINGFACE_API_KEY=your_huggingface_token_here"
        exit 1
    fi
fi

# Run the application
echo "Starting development server..."
uvicorn src.api.main:app --reload --port 8000 --host 0.0.0.0