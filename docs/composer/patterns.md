## 🔍 Pattern Recognition Lens Guide

### Core Pattern Categories

#### Redis Patterns
##### Redis PubSub Synchronous Pattern
**WATCH FOR**:
- Redis pubsub methods (subscribe, unsubscribe, publish) are synchronous despite being used in async context
- Attempting to await these methods will cause errors
- Missing this pattern leads to message processing failures

**REQUIRED ACTIONS**:
- Call pubsub methods directly without await
- Document synchronous nature in code comments
- Test pubsub operations in both sync and async contexts
- Ensure proper error handling for pubsub operations

**VALIDATION**:
- Verify message ordering is preserved
- Check subscription state after operations
- Monitor message delivery reliability
- Test recovery from connection failures 