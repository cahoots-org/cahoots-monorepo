# Local LLM Inference with vLLM

This guide explains how to run Cahoots with local LLM inference using your GPU.

## Overview

Cahoots supports local inference using [vLLM](https://github.com/vllm-project/vllm), a high-performance inference engine. This is ideal for:
- Maximum privacy (no data leaves your machine)
- Lower latency (no network round-trips)
- Cost savings (no API usage fees)
- Full control over model selection

## Hardware Requirements

**Recommended Configuration:**
- NVIDIA GPU with 24GB+ VRAM (tested on RTX 5090 with 32GB)
- 32GB+ system RAM
- 100GB+ free disk space (for model weights)

**Supported Models:**
- Qwen3-32B-Instruct (default, ~24GB VRAM with AWQ quantization)
- Qwen2.5-Coder-32B-Instruct
- Other models supported by vLLM (adjust `--max-model-len` as needed)

## Why Run vLLM on Host (Not Docker)?

Docker Desktop on Linux has limited GPU support. Running vLLM directly on the host provides:
- Direct GPU access without Docker overhead
- Better performance
- Simpler setup (no nvidia-container-toolkit configuration needed)

## Installation

### 1. Install vLLM

```bash
pip install vllm
```

### 2. Set Up Environment

Ensure your `.env` file has:

```bash
LLM_PROVIDER=local
LOCAL_LLM_URL=http://localhost:8001/v1
LOCAL_LLM_MODEL=Qwen/Qwen3-32B-Instruct
HUGGINGFACE_API_KEY=your_hf_token_here
```

Get a HuggingFace token from: https://huggingface.co/settings/tokens

## Running Local Inference

### Quick Start

```bash
# In terminal 1: Start vLLM server
./scripts/start_vllm.sh

# In terminal 2: Start Cahoots services
docker compose up -d
```

The vLLM server will:
1. Download Qwen3-32B-Instruct (first run only, ~20GB download)
2. Load the model into GPU memory (~24GB VRAM)
3. Start serving on `http://localhost:8001`

### Manual vLLM Configuration

If you want to customize vLLM settings:

```bash
HF_TOKEN=$HUGGINGFACE_API_KEY vllm serve Qwen/Qwen3-32B-Instruct \
    --quantization awq \
    --dtype auto \
    --max-model-len 32768 \
    --gpu-memory-utilization 0.9 \
    --enable-prefix-caching \
    --port 8001
```

**Key Parameters:**
- `--quantization awq`: Use AWQ quantization (4-bit) to reduce VRAM usage
- `--max-model-len 32768`: Maximum context length
- `--gpu-memory-utilization 0.9`: Use 90% of GPU memory
- `--enable-prefix-caching`: Cache prompt prefixes for faster repeated queries

## Performance

**Expected Performance (RTX 5090):**
- First token: ~200-500ms
- Generation speed: ~100-150 tokens/second
- Context processing: ~1000 tokens/second

**Model Quality:**
- Qwen3-32B-Instruct HumanEval score: 91.5
- Comparable to GPT-4 for code generation tasks
- Superior to Lambda's 405B model (HumanEval ~89)

## Troubleshooting

### vLLM won't start

**Issue:** `CUDA_ERROR` or `Out of memory`

**Solution:** Reduce GPU memory utilization:
```bash
vllm serve ... --gpu-memory-utilization 0.7
```

### Model download fails

**Issue:** `HTTPError 401` or authentication error

**Solution:** Check your HuggingFace token:
```bash
echo $HUGGINGFACE_API_KEY  # Should print your token
```

### Slow inference

**Issue:** Generation is slower than expected

**Possible causes:**
1. CPU bottleneck: Ensure vLLM is using GPU (check with `nvidia-smi`)
2. Disk I/O: Model loading from slow storage (first load only)
3. Memory pressure: Reduce `--max-model-len` or `--gpu-memory-utilization`

## Switching Between Providers

To switch back to cloud providers, update `.env`:

```bash
# Use Cerebras (fast, cost-effective)
LLM_PROVIDER=cerebras
CEREBRAS_API_KEY=your_key_here

# Use OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=your_key_here
```

Then restart Cahoots:
```bash
docker compose up --build -d api
```

## Advanced: Using Different Models

To use a different model:

1. Update `.env`:
   ```bash
   LOCAL_LLM_MODEL=Qwen/Qwen2.5-Coder-32B-Instruct
   ```

2. Start vLLM with the new model:
   ```bash
   HF_TOKEN=$HUGGINGFACE_API_KEY vllm serve Qwen/Qwen2.5-Coder-32B-Instruct \
       --quantization awq \
       --dtype auto \
       --max-model-len 32768 \
       --gpu-memory-utilization 0.9 \
       --port 8001
   ```

3. Restart Cahoots API:
   ```bash
   docker compose up --build -d api
   ```

## Docker Desktop GPU Support (Alternative)

If you switch from Docker Desktop to native Docker, you can run vLLM in a container:

1. Install native Docker (not Docker Desktop)
2. Install NVIDIA Container Toolkit
3. Uncomment the vLLM service in `docker-compose.yml`
4. Run: `docker compose --profile local-inference up -d`

This approach is not recommended for Docker Desktop users due to GPU passthrough limitations.

## Resources

- [vLLM Documentation](https://docs.vllm.ai/)
- [Qwen3 Model Card](https://huggingface.co/Qwen/Qwen3-32B-Instruct)
- [NVIDIA GPU Support for Docker](https://docs.docker.com/config/containers/resource_constraints/#gpu)
