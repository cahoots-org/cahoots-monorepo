"""Dependency health check implementations."""
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from redis.asyncio import Redis, from_url as redis_from_url
import boto3
import aio_pika
import httpx

from cahoots_service.schemas.health import HealthStatus
from cahoots_service.utils.config import get_settings

settings = get_settings()

async def check_database(db: AsyncSession) -> HealthStatus:
    """Check database connectivity and health."""
    try:
        # Execute simple query to verify database connection
        result = await db.execute(text("SELECT 1"))
        await result.fetchone()
        return HealthStatus.HEALTHY
    except Exception as e:
        return HealthStatus.UNHEALTHY

async def check_redis(db: AsyncSession) -> HealthStatus:
    """Check Redis connectivity and health."""
    try:
        redis = await redis_from_url(settings.redis_url)
        await redis.ping()
        await redis.close()
        return HealthStatus.HEALTHY
    except Exception as e:
        return HealthStatus.UNHEALTHY

async def check_message_queue(db: AsyncSession) -> HealthStatus:
    """Check message queue connectivity and health."""
    try:
        connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        await connection.close()
        return HealthStatus.HEALTHY
    except Exception as e:
        return HealthStatus.UNHEALTHY

async def check_storage(db: AsyncSession) -> HealthStatus:
    """Check storage service connectivity and health."""
    try:
        session = boto3.Session()
        async with session.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            endpoint_url=settings.S3_ENDPOINT_URL
        ) as s3:
            await s3.head_bucket(Bucket=settings.S3_BUCKET)
        return HealthStatus.HEALTHY
    except Exception as e:
        return HealthStatus.UNHEALTHY

async def check_external_apis(db: AsyncSession) -> HealthStatus:
    """Check external API dependencies health."""
    try:
        async with httpx.AsyncClient() as client:
            # Check each external API endpoint
            responses = await _check_external_endpoints(client)
            
            # If any critical API is down, return UNHEALTHY
            if any(not resp["healthy"] for resp in responses if resp["critical"]):
                return HealthStatus.UNHEALTHY
                
            # If any non-critical API is down, return DEGRADED
            if any(not resp["healthy"] for resp in responses):
                return HealthStatus.DEGRADED
                
            return HealthStatus.HEALTHY
    except Exception as e:
        return HealthStatus.UNHEALTHY

async def _check_external_endpoints(client: httpx.AsyncClient) -> list[Dict[str, Any]]:
    """Check health of external API endpoints."""
    endpoints = [
        {
            "url": settings.STRIPE_API_URL,
            "critical": True
        },
        {
            "url": settings.GITHUB_API_URL,
            "critical": False
        }
        # Add other external API endpoints as needed
    ]
    
    results = []
    for endpoint in endpoints:
        try:
            response = await client.get(endpoint["url"])
            results.append({
                "url": endpoint["url"],
                "healthy": response.status_code < 500,
                "critical": endpoint["critical"]
            })
        except Exception:
            results.append({
                "url": endpoint["url"],
                "healthy": False,
                "critical": endpoint["critical"]
            })
    
    return results 