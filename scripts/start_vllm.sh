#!/bin/bash
# Start vLLM inference server on host (outside Docker)
# This is necessary because Docker Desktop on Linux doesn't support GPU passthrough well

set -e

# Check if vllm is installed
if ! command -v vllm &> /dev/null; then
    echo "❌ vllm not found. Installing..."
    pip install vllm
fi

# Check if HF token is set
if [ -z "$HUGGINGFACE_API_KEY" ]; then
    echo "⚠️  Warning: HUGGINGFACE_API_KEY not set. Loading from .env if available..."
    if [ -f .env ]; then
        export $(cat .env | grep HUGGINGFACE_API_KEY | xargs)
    fi

    if [ -z "$HUGGINGFACE_API_KEY" ]; then
        echo "❌ HUGGINGFACE_API_KEY is required for downloading models"
        exit 1
    fi
fi

# Use LOCAL_LLM_MODEL from environment or default
MODEL=${LOCAL_LLM_MODEL:-Qwen/Qwen2.5-Coder-32B-Instruct}

echo "🚀 Starting vLLM server..."
echo "   Model: $MODEL"
echo "   Port: 8001"
echo "   Quantization: AWQ (reduces VRAM usage)"
echo ""
echo "📊 Server will be available at: http://localhost:8001/v1"
echo "🛑 Press Ctrl+C to stop the server"
echo ""

HF_TOKEN=$HUGGINGFACE_API_KEY vllm serve "$MODEL" \
    --dtype auto \
    --max-model-len 32768 \
    --gpu-memory-utilization 0.9 \
    --enable-prefix-caching \
    --port 8001
