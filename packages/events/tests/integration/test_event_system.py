"""Integration tests for event system."""
import pytest
from unittest.mock import AsyncMock
import json
from datetime import datetime

from ...src.cahoots_events.bus.system import EventSystem
from ...src.cahoots_events.config import EventConfig
from cahoots_core.utils.redis import get_redis_client

pytestmark = pytest.mark.asyncio

async def test_event_publish_subscribe(event_system: EventSystem):
    """Test event publishing and subscribing behavior.
    
    Given: An event system connected to Redis
    When: A message is published to a channel
    Then: Subscribers should receive the message
    """
    channel = "test_channel"
    message = {"type": "test", "data": "hello"}
    received_messages = []
    
    # Subscribe to channel
    async def message_handler(msg):
        received_messages.append(msg)
    
    await event_system.subscribe(channel, message_handler)
    
    # Publish message
    await event_system.publish(channel, message)
    
    # Allow time for message processing
    await event_system.process_messages(timeout=1.0)
    
    # Verify behavior
    assert len(received_messages) == 1
    assert received_messages[0] == message

async def test_redis_failure_recovery(event_system: EventSystem, redis_client):
    """Test event system recovery after Redis failure.
    
    Given: An event system with active subscriptions
    When: Redis connection fails and recovers
    Then: Event system should reconnect and resume processing
    """
    channel = "test_failure_recovery"
    messages = []
    
    async def message_handler(msg):
        messages.append(msg)
    
    # Setup subscription
    await event_system.subscribe(channel, message_handler)
    
    # Simulate Redis failure
    await redis_client.aclose()
    
    # Verify connection lost
    assert not await event_system.verify_connection()
    
    # Reconnect Redis
    await redis_client.ping()
    
    # System should auto-reconnect on next operation
    message = {"type": "recovery_test", "data": "test"}
    await event_system.publish(channel, message)
    
    # Allow time for recovery and processing
    await event_system.process_messages(timeout=1.0)
    
    # Verify message received after recovery
    assert len(messages) == 1
    assert messages[0] == message

async def test_message_ordering(event_system: EventSystem):
    """Test message ordering guarantees.
    
    Given: Multiple messages published rapidly
    When: Messages are processed
    Then: Messages should be received in order of publishing
    """
    channel = "test_ordering"
    received_messages = []
    
    async def message_handler(msg):
        received_messages.append(msg)
    
    await event_system.subscribe(channel, message_handler)
    
    # Publish messages rapidly
    messages = [
        {"sequence": i, "timestamp": datetime.utcnow().isoformat()}
        for i in range(10)
    ]
    
    for msg in messages:
        await event_system.publish(channel, msg)
    
    # Allow time for processing
    await event_system.process_messages(timeout=1.0)
    
    # Verify order preserved
    assert len(received_messages) == len(messages)
    for i, msg in enumerate(received_messages):
        assert msg["sequence"] == i

async def test_dead_letter_queue(event_system: EventSystem):
    """Test dead letter queue functionality.
    
    Given: A failing message handler
    When: Messages are processed
    Then: Failed messages should be moved to DLQ
    """
    channel = "test_dlq"
    error_message = "Handler failure"
    
    async def failing_handler(msg):
        raise ValueError(error_message)
    
    # Subscribe failing handler
    await event_system.subscribe(channel, failing_handler)
    
    # Publish message
    message = {"type": "test", "data": "will_fail"}
    await event_system.publish(channel, message)
    
    # Allow time for processing and DLQ
    await event_system.process_messages(timeout=1.0)
    
    # Verify message in DLQ
    dlq_messages = await event_system.get_dlq_messages(channel)
    assert len(dlq_messages) == 1
    dlq_msg = dlq_messages[0]
    assert dlq_msg["original_message"] == message
    assert error_message in dlq_msg["error"]
    assert dlq_msg["retry_count"] == 0

async def test_concurrent_message_processing(event_system: EventSystem):
    """Test concurrent message processing behavior.
    
    Given: Multiple subscribers processing messages concurrently
    When: Messages are published rapidly
    Then: All messages should be processed correctly without race conditions
    """
    channel = "test_concurrent"
    processed_messages = set()
    processing_lock = asyncio.Lock()
    
    async def slow_handler(msg):
        async with processing_lock:
            await asyncio.sleep(0.1)  # Simulate processing time
            processed_messages.add(msg["id"])
    
    # Subscribe multiple handlers
    for _ in range(3):
        await event_system.subscribe(channel, slow_handler)
    
    # Publish messages concurrently
    messages = [
        {"id": f"msg_{i}", "data": f"test_{i}"}
        for i in range(10)
    ]
    
    await asyncio.gather(
        *(event_system.publish(channel, msg) for msg in messages)
    )
    
    # Allow time for processing
    await event_system.process_messages(timeout=2.0)
    
    # Verify all messages processed exactly once
    assert len(processed_messages) == len(messages)
    assert all(f"msg_{i}" in processed_messages for i in range(10)) 