from dataclasses import dataclass


@dataclass
class RetryPolicy:
    """Configuration for retry behavior."""

    max_retries: int = 3
    retry_delay: int = 60  # seconds
    exponential_backoff: bool = True
