# Usage Examples

This document provides examples of how to use the core components of the Cahoots project.

## Table of Contents
- [Event System](#event-system)
- [Message Dispatcher](#message-dispatcher)
- [Configuration](#configuration)
- [Error Handling](#error-handling)
- [Shared Utilities](#shared-utilities)

## Event System

The Event System provides a pub/sub mechanism for asynchronous communication between components.

### Basic Usage

```python
from packages.core.src.utils.event_system import EventSystem, Event, EventType, EventPriority

# Create and start the event system
event_system = EventSystem()
await event_system.start()

# Define an event handler
async def task_handler(event):
    print(f"Received task: {event.payload}")

# Subscribe to events
event_system.subscribe(EventType.TASK_CREATED, task_handler)

# Publish an event
event = Event(
    type=EventType.TASK_CREATED,
    payload={"task_id": "123", "name": "Example Task"},
    priority=EventPriority.NORMAL
)
await event_system.publish(event)

# Stop the event system when done
await event_system.stop()
```

### Error Handling

```python
async def error_handler(event):
    if event.error:
        print(f"Error processing event: {event.error}")
        print(f"Original error: {event.error.original_error}")

event_system.subscribe(EventType.SYSTEM_ERROR, error_handler)
```

## Message Dispatcher

The Message Dispatcher handles message routing between components with support for targeted delivery and broadcasting.

### Basic Usage

```python
from packages.core.src.messaging.dispatcher import MessageDispatcher, Message, MessageType

# Create and start the dispatcher
dispatcher = MessageDispatcher()
await dispatcher.start()

# Define message handlers
async def task_handler(message):
    print(f"Processing task: {message.payload}")

# Register handlers
dispatcher.register_handler(
    MessageType.TASK_ASSIGNMENT,
    task_handler,
    target="worker-1"
)

# Send a message
message = Message(
    type=MessageType.TASK_ASSIGNMENT,
    payload={"task_id": "123"},
    target="worker-1"
)
await dispatcher.send(message)

# Broadcast a message
await dispatcher.broadcast(message)

# Stop the dispatcher when done
await dispatcher.stop()
```

## Configuration

The configuration system supports environment variables, YAML files, and programmatic updates.

### Basic Usage

```python
from packages.core.src.utils.config import Config, load_config, configure_logging

# Load configuration
config = load_config("config.yaml")

# Access configuration values
db_url = config.database.url
redis_url = config.redis.url
api_port = config.api.port

# Update configuration
config.api.workers = 8
config.logging.level = "DEBUG"

# Configure logging
configure_logging()
```

### Environment Variables

```bash
# Set environment variables
export APP_ENV=production
export DB_HOST=db.example.com
export REDIS_PASSWORD=secret
export API_WORKERS=4
export LOG_LEVEL=INFO
```

### YAML Configuration

```yaml
# config.yaml
env: production
debug: false
database:
  host: db.example.com
  port: 5432
  name: app_db
redis:
  host: redis.example.com
  ssl: true
api:
  workers: 4
  rate_limit: 1000
```

## Error Handling

The error handling system provides consistent error management across the application.

### Basic Usage

```python
from packages.core.src.utils.exceptions import (
    BaseError,
    ValidationError,
    handle_error,
    create_error_response
)
import logging

logger = logging.getLogger(__name__)

try:
    # Some operation that might fail
    raise ValidationError("Invalid input data")
except Exception as e:
    # Handle the error
    error = handle_error(
        logger,
        e,
        context={"operation": "process_data"}
    )
    
    # Create error response
    response = create_error_response(error)
```

### Custom Error Types

```python
from packages.core.src.utils.exceptions import BaseError

class CustomError(BaseError):
    """Custom error type."""
    pass

try:
    raise CustomError(
        message="Custom error occurred",
        code="CUSTOM_ERROR",
        details={"key": "value"}
    )
except CustomError as e:
    error_dict = e.to_dict()
```

## Shared Utilities

The shared utilities module provides common functionality used across the application.

### String Manipulation

```python
from packages.core.src.utils.shared_utils import (
    sanitize_string,
    truncate_string,
    format_timestamp,
    safe_json_loads,
    safe_json_dumps,
    retry_async
)

# Sanitize strings
clean = sanitize_string("Hello, World!")  # "Hello World"

# Truncate long strings
short = truncate_string("Long text...", max_length=10)

# Format timestamps
timestamp = format_timestamp()  # Current time in ISO format
```

### JSON Handling

```python
from packages.core.src.utils.shared_utils import safe_json_loads, safe_json_dumps

# Safely parse JSON
data = safe_json_loads('{"key": "value"}')

# Safely convert to JSON
json_str = safe_json_dumps({"key": "value"})
```

### Retry Mechanism

```python
from packages.core.src.utils.shared_utils import retry_async

@retry_async(max_attempts=3, delay=1.0)
async def fetch_data():
    # Operation that might fail
    pass

try:
    result = await fetch_data()
except Exception as e:
    print(f"All retry attempts failed: {e}")
```

### Performance Measurement

```python
from packages.core.src.utils.shared_utils import measure_time, measure_time_async

@measure_time
def slow_operation():
    # Synchronous operation
    pass

@measure_time_async
async def slow_async_operation():
    # Asynchronous operation
    pass
```

### Data Processing

```python
from packages.core.src.utils.shared_utils import chunk_list, merge_dicts

# Split list into chunks
chunks = chunk_list([1, 2, 3, 4, 5], chunk_size=2)

# Merge dictionaries
dict1 = {"a": 1, "b": {"x": 10}}
dict2 = {"b": {"y": 20}, "c": 3}
merged = merge_dicts(dict1, dict2)
```

### Time and Duration

```python
from packages.core.src.utils.shared_utils import parse_duration, format_duration

# Parse duration strings
seconds = parse_duration("1h")  # 3600
seconds = parse_duration("30m")  # 1800

# Format durations
formatted = format_duration(3665)  # "1h 1m 5s"
``` 