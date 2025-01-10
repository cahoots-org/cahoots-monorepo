#!/usr/bin/env python3
"""Script to manage Redis cache."""
import os
import sys
from typing import Dict, List, Optional
from redis import Redis

def get_redis_client() -> Redis:
    """Get Redis client instance.
    
    Returns:
        Redis: Redis client
    """
    return Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        db=int(os.getenv("REDIS_DB", "0")),
        decode_responses=True
    )

def list_rate_limits(redis: Redis) -> None:
    """List all rate limit keys and their values.
    
    Args:
        redis: Redis client
    """
    print("\nRate Limit Keys:")
    pattern = "rate_limit:*"
    
    for key in redis.scan_iter(pattern):
        value = redis.get(key)
        ttl = redis.ttl(key)
        print(f"Key: {key}")
        print(f"Value: {value}")
        print(f"TTL: {ttl} seconds")
        print()

def clear_rate_limits(redis: Redis) -> None:
    """Clear all rate limit keys.
    
    Args:
        redis: Redis client
    """
    pattern = "rate_limit:*"
    keys = list(redis.scan_iter(pattern))
    
    if keys:
        redis.delete(*keys)
        print(f"\nCleared {len(keys)} rate limit keys")
    else:
        print("\nNo rate limit keys to clear")

def get_organization_usage(redis: Redis, organization_id: str) -> None:
    """Get usage statistics for an organization.
    
    Args:
        redis: Redis client
        organization_id: Organization ID
    """
    pattern = f"rate_limit:{organization_id}:*"
    keys = list(redis.scan_iter(pattern))
    
    if not keys:
        print(f"\nNo usage data found for organization {organization_id}")
        return
    
    print(f"\nUsage for organization {organization_id}:")
    for key in keys:
        value = redis.get(key)
        ttl = redis.ttl(key)
        print(f"Window: {key}")
        print(f"Requests: {value}")
        print(f"TTL: {ttl} seconds")
        print()

def monitor_rate_limits(redis: Redis) -> None:
    """Monitor rate limit changes in real-time.
    
    Args:
        redis: Redis client
    """
    pubsub = redis.pubsub()
    pattern = "__keyspace@0__:rate_limit:*"
    
    print("\nMonitoring rate limit changes (Ctrl+C to stop)...")
    pubsub.psubscribe(pattern)
    
    try:
        for message in pubsub.listen():
            if message["type"] == "pmessage":
                key = message["channel"].decode().split(":", 1)[1]
                value = redis.get(key)
                print(f"Key: {key}")
                print(f"New value: {value}")
                print()
    except KeyboardInterrupt:
        pubsub.unsubscribe()
        print("\nStopped monitoring")

def main() -> None:
    """Main function."""
    redis = get_redis_client()
    
    while True:
        print("\n=== Redis Cache Manager ===")
        print("1. List rate limits")
        print("2. Clear rate limits")
        print("3. Get organization usage")
        print("4. Monitor rate limits")
        print("5. Exit")
        
        choice = input("\nEnter your choice (1-5): ")
        
        try:
            if choice == "1":
                list_rate_limits(redis)
            elif choice == "2":
                clear_rate_limits(redis)
            elif choice == "3":
                org_id = input("Enter organization ID: ")
                get_organization_usage(redis, org_id)
            elif choice == "4":
                monitor_rate_limits(redis)
            elif choice == "5":
                print("\nGoodbye!")
                break
            else:
                print("\nInvalid choice!")
        except Exception as e:
            print(f"\nError: {str(e)}")

if __name__ == "__main__":
    main() 