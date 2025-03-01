FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies using the mounted pip cache
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# The site-packages will be mounted at runtime

# No need to install packages here as we'll mount them 