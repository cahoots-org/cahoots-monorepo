"""Common utilities shared across the codebase."""

import asyncio
import json
import logging
import re
import time
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

from cahoots_core.exceptions.api import ValidationError

T = TypeVar("T")


def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> None:
    """Validate that required fields are present in data.

    Args:
        data: Data to validate
        required_fields: List of required field names

    Raises:
        ValidationError: If any required fields are missing
    """
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")


def sanitize_string(value: str) -> str:
    """Sanitize a string by removing special characters.

    Args:
        value: String to sanitize

    Returns:
        str: Sanitized string
    """
    return re.sub(r"[^\w\s-]", "", value).strip()


def to_snake_case(value: str) -> str:
    """Convert string to snake_case.

    Args:
        value: String to convert

    Returns:
        str: Snake case string
    """
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", value)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def to_camel_case(value: str) -> str:
    """Convert string to camelCase.

    Args:
        value: String to convert

    Returns:
        str: Camel case string
    """
    components = value.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def utc_now() -> datetime:
    """Get current UTC datetime.

    Returns:
        datetime: Current UTC datetime
    """
    return datetime.now(timezone.utc)


class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that handles datetime objects."""

    def default(self, obj: Any) -> Any:
        """Convert datetime objects to ISO format strings."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def json_dumps(obj: Any) -> str:
    """Dump object to JSON string, handling datetime objects.

    Args:
        obj: Object to serialize

    Returns:
        str: JSON string
    """
    return json.dumps(obj, cls=DateTimeEncoder)


def retry_async(
    max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0, exceptions: tuple = (Exception,)
) -> Callable:
    """Decorator for retrying async functions.

    Args:
        max_retries: Maximum number of retries
        delay: Initial delay between retries in seconds
        backoff: Backoff multiplier
        exceptions: Tuple of exceptions to catch

    Returns:
        Callable: Decorated function
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            current_delay = delay

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_retries:
                        break
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff

            raise last_exception

        return wrapper

    return decorator


def rate_limit(calls: int, period: float, raise_on_limit: bool = True) -> Callable:
    """Decorator for rate limiting function calls.

    Args:
        calls: Number of calls allowed per period
        period: Time period in seconds
        raise_on_limit: Whether to raise exception when limit is reached

    Returns:
        Callable: Decorated function
    """

    def decorator(func: Callable) -> Callable:
        timestamps: List[float] = []

        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            now = time.time()
            timestamps[:] = [ts for ts in timestamps if now - ts <= period]

            if len(timestamps) >= calls:
                if raise_on_limit:
                    raise ValidationError(
                        f"Rate limit exceeded: {calls} calls per {period} seconds"
                    )
                return None

            timestamps.append(now)
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def memoize(ttl: Optional[float] = None) -> Callable:
    """Decorator for memoizing function results.

    Args:
        ttl: Time to live in seconds, None for no expiration

    Returns:
        Callable: Decorated function
    """
    cache: Dict[str, Dict[str, Any]] = {}

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            now = time.time()

            if key in cache:
                result = cache[key]
                if ttl is None or now - result["timestamp"] < ttl:
                    return result["value"]
                del cache[key]

            value = await func(*args, **kwargs)
            cache[key] = {"value": value, "timestamp": now}
            return value

        return wrapper

    return decorator


def chunk_list(lst: List[T], size: int) -> List[List[T]]:
    """Split list into chunks of specified size.

    Args:
        lst: List to split
        size: Chunk size

    Returns:
        List[List[T]]: List of chunks
    """
    return [lst[i : i + size] for i in range(0, len(lst), size)]


def deep_get(obj: Dict[str, Any], path: str, default: Any = None) -> Any:
    """Get value from nested dictionary using dot notation.

    Args:
        obj: Dictionary to search
        path: Path to value using dot notation
        default: Default value if path not found

    Returns:
        Any: Value at path or default
    """
    try:
        parts = path.split(".")
        current = obj
        for part in parts:
            current = current[part]
        return current
    except (KeyError, TypeError):
        return default


def deep_update(target: Dict[str, Any], source: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively update target dictionary with source.

    Args:
        target: Dictionary to update
        source: Dictionary with updates

    Returns:
        Dict[str, Any]: Updated dictionary
    """
    for key, value in source.items():
        if isinstance(value, dict) and key in target and isinstance(target[key], dict):
            target[key] = deep_update(target[key], value)
        else:
            target[key] = value
    return target


logger = logging.getLogger(__name__)
