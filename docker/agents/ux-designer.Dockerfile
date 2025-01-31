# Generated from Dockerfile.template
# Do not edit directly

# syntax=docker/dockerfile:1.4

ARG BASE_IMAGE=ghcr.io/your-org/ai-dev-team-base:latest

# Use the production stage from base image
FROM ${BASE_IMAGE} AS base

# Build arguments for agent customization
ARG AGENT_NAME
ARG AGENT_DESCRIPTION
ARG AGENT_ROLE

# Labels for container metadata
LABEL org.opencontainers.image.title="AI Dev Team - ux-designer Agent" \
      org.opencontainers.image.description="UX designer agent for user interface and experience design" \
      org.opencontainers.image.source="https://github.com/your-org/ai-dev-team"

# Environment variables for agent configuration
ENV AGENT_NAME=ux-designer \
    AGENT_ROLE=ux-designer \
    AGENT_CONFIG_PATH=/app/config/agent.yaml

# Create config directory
USER root
RUN mkdir -p /app/config /app/services/agents
USER app

# Copy agent-specific configuration
COPY --chown=app:app config/agents/ux-designer.yaml /app/config/agent.yaml

# Copy agent package
COPY --chown=app:app services/agents/cahoots_agents /app/services/agents/cahoots_agents

# Validate agent configuration
RUN python -c "import yaml; yaml.safe_load(open('/app/config/agent.yaml'))"

# Health check specific to agents
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/agent/health || exit 1

# Default command to run the agent
CMD ["python", "-m", "cahoots.agents.runner"] 