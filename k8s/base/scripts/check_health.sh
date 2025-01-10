#!/bin/sh
redis-cli -h $REDIS_HOST -p $REDIS_PORT get "health:$AGENT_TYPE" | grep -q "healthy" 