"""Event system configuration."""
from typing import Optional
from pydantic import BaseModel, Field


class EventConfig(BaseModel):
    """Event system configuration."""
    
    max_event_size: int = Field(
        default=1024 * 1024,  # 1MB
        description="Maximum size of event payload in bytes"
    )
    
    max_retries: int = Field(
        default=3,
        description="Maximum number of retry attempts for failed operations"
    )
    
    retry_delay: float = Field(
        default=1.0,
        description="Delay between retries in seconds"
    )
    
    heartbeat_interval: float = Field(
        default=5.0,
        description="Interval for heartbeat checks in seconds"
    )
    
    dlq_prefix: str = Field(
        default="dlq:",
        description="Prefix for dead letter queue keys"
    )
    
    queue_timeout: float = Field(
        default=30.0,
        description="Timeout for queue operations in seconds"
    )
    
    batch_size: int = Field(
        default=100,
        description="Maximum number of events to process in a batch"
    )

    retention_hours: int = Field(
        default=24,
        description="Number of hours to retain events before cleanup"
    )

    cache_ttl_seconds: int = Field(
        default=300,  # 5 minutes
        description="Time to live for cached events in seconds"
    )

    max_retry_count: int = Field(
        default=3,
        description="Maximum number of retries for failed events"
    ) 