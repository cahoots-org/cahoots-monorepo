#!/bin/bash

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies (excluding torch)
grep -v "torch==" requirements.txt > requirements_no_torch.txt
pip install -r requirements_no_torch.txt

# Install PyTorch based on platform
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS - use default PyTorch channel
    pip install torch==1.9.0 --extra-index-url https://download.pytorch.org/whl/cpu
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    pip install torch==1.9.0+cpu -f https://download.pytorch.org/whl/torch_stable.html
else
    # Windows or other
    pip install torch==1.9.0+cpu -f https://download.pytorch.org/whl/torch_stable.html
fi

# Clean up temporary requirements file
rm requirements_no_torch.txt

# Set environment variables
export ENV=local

# Run the application
uvicorn src.api.main:app --reload --port 8000 