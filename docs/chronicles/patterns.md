# 🔍 Pattern Recognition Lens Guide

## Core Pattern Categories

### Behavioral Patterns
1. **State Management**
   WATCH FOR:
   - State transitions without validation
   - Missing boundary checks
   - Incomplete error states
   - Undefined recovery paths
   
   REQUIRED ACTIONS:
   - Validate all state changes
   - Test boundary conditions
   - Handle error states
   - Verify recovery paths

2. **Integration Points**
   WATCH FOR:
   - Unclear service boundaries
   - Direct database access
   - Unhandled API failures
   - Lost messages
   
   REQUIRED ACTIONS:
   - Define clear interfaces
   - Use repository pattern
   - Implement retry logic
   - Ensure message delivery

3. **Concurrency Issues**
   WATCH FOR:
   - Shared state access
   - Resource competition
   - Circular dependencies
   - Blocking operations
   
   REQUIRED ACTIONS:
   - Use atomic operations
   - Implement proper locks
   - Break dependency cycles
   - Make operations async

### 🛡️ Security Patterns

1. **Authentication Checks**
   WATCH FOR:
   - Token validation gaps
   - Session timeouts
   - Credential exposure
   - Missing access checks
   
   REQUIRED ACTIONS:
   - Validate all tokens
   - Manage sessions properly
   - Secure credentials
   - Enforce access control

2. **Authorization Rules**
   WATCH FOR:
   - Missing role checks
   - Incomplete permissions
   - Bypassed policies
   - Invalid scopes
   
   REQUIRED ACTIONS:
   - Verify all roles
   - Check all permissions
   - Enforce policies
   - Validate scopes

3. **Rate Limiting**
   WATCH FOR:
   - Shared counters
   - Non-atomic operations
   - Missing error handling
   - Resource exhaustion
   
   REQUIRED ACTIONS:
   - Isolate counters
   - Use atomic operations
   - Handle all errors
   - Protect resources

### ⚠️ Error Patterns

1. **Data Validation**
   WATCH FOR:
   - Missing input checks
   - Type mismatches
   - Format violations
   - Constraint breaches
   
   REQUIRED ACTIONS:
   - Validate all inputs
   - Check types strictly
   - Verify formats
   - Enforce constraints

2. **Resource Management**
   WATCH FOR:
   - Connection leaks
   - Memory growth
   - Open handles
   - Network issues
   - Context boundaries
   - Async lock patterns
   
   REQUIRED ACTIONS:
   - Pool connections
   - Monitor memory
   - Close handles
   - Handle timeouts
   - Enforce memory limits
   - Use proper async locks
   - Initialize contexts safely
   - Clean caches proactively

3. **Recovery Handling**
   WATCH FOR:
   - Unhandled failures
   - Data inconsistency
   - Network issues
   - State corruption
   
   REQUIRED ACTIONS:
   - Handle all failures
   - Maintain consistency
   - Manage connectivity
   - Recover state

## 🏗️ Implementation Patterns

### Code Organization
1. **Dependencies**
   WATCH FOR:
   - Tight coupling
   - Version conflicts
   - Circular imports
   - Hidden dependencies
   
   REQUIRED ACTIONS:
   - Use dependency injection
   - Manage versions
   - Break cycles
   - Make dependencies explicit

2. **Error Management**
   WATCH FOR:
   - Swallowed exceptions
   - Missing logging
   - Unclear recovery
   - State inconsistency
   
   REQUIRED ACTIONS:
   - Handle all exceptions
   - Log appropriately
   - Define recovery paths
   - Maintain state

### Test Structure
1. **Test Organization**
   WATCH FOR:
   - Duplicated setup
   - Complex fixtures
   - Unclear mocks
   - Weak assertions
   
   REQUIRED ACTIONS:
   - Share setup code
   - Simplify fixtures
   - Clarify mocks
   - Strengthen assertions

2. **Coverage Analysis**
   WATCH FOR:
   - Missing edge cases
   - Untested boundaries
   - Ignored error paths
   - Incomplete flows
   
   REQUIRED ACTIONS:
   - Test edge cases
   - Verify boundaries
   - Cover error paths
   - Complete flows

## ❌ Anti-Patterns

### Implementation Coupling
WATCH FOR:
- Tests tied to implementation
- Hard-coded values
- Time dependencies
- Environment assumptions

REQUIRED ACTIONS:
- Test behavior only
- Use dynamic values
- Make time explicit
- Abstract environment

### Resource Leaks
WATCH FOR:
- Unclosed resources
- Memory leaks
- Handle leaks
- Thread leaks

REQUIRED ACTIONS:
- Close all resources
- Monitor memory
- Track handles
- Manage threads

## 🔍 Recognition Protocol

### Pattern Detection Process
1. ANALYZE:
   - Code structure
   - Common patterns
   - Repeated logic
   - Dependencies

2. EVALUATE:
   - Test coverage
   - Pattern matches
   - Assertion types
   - Setup patterns

3. VALIDATE:
   - Error handling
   - Recovery paths
   - Logging patterns
   - State management

## Security Patterns

### Policy Inheritance Chain Pattern
**WATCH FOR**:
- Policy inheritance relationships
- Scope requirements in extended policies
- Base policy applicability

**REQUIRED ACTIONS**:
1. Always validate base policies first
2. Check scope requirements before applying extended policies
3. Build complete policy chain before validation
4. Handle circular inheritance gracefully

### Rule Validation Pattern
**WATCH FOR**:
- Different rule types (scopes, IP, time windows)
- Rule validation order
- Rule combination effects

**REQUIRED ACTIONS**:
1. Validate each rule type independently
2. Log validation failures for debugging
3. Handle unknown rule types safely
4. Ensure proper error handling

### Policy Applicability Pattern
**WATCH FOR**:
- Policy chain construction
- Scope inheritance requirements
- Base vs extended policy behavior

**REQUIRED ACTIONS**:
1. Build complete policy chain
2. Skip inapplicable policies
3. Validate against each applicable policy
4. Maintain proper security boundaries

### Redis Operation Patterns
**WATCH FOR**:
- Byte encoding mismatches
- Non-atomic operations
- Key pattern consistency
- Scan operation handling

**REQUIRED ACTIONS**:
1. Always encode keys and values properly
2. Use atomic operations for updates
3. Maintain consistent key patterns
4. Handle scan results as bytes

### Policy Validation Patterns
**WATCH FOR**:
- Scope hierarchy violations
- Rule type inconsistencies
- Policy chain breaks
- Validation order issues

**REQUIRED ACTIONS**:
1. Validate from most specific to least specific
2. Handle each rule type independently
3. Build complete policy chains
4. Log validation failures clearly

### Context Protection Patterns
1. **Memory Boundary Protection**
   WATCH FOR:
   - Unbounded collections
   - Large object accumulation
   - Missing size checks
   - Inefficient data structures
   
   REQUIRED ACTIONS:
   - Implement size limits
   - Check before additions
   - Prune old data
   - Use efficient structures

2. **Async Context Management**
   WATCH FOR:
   - Mixed sync/async patterns
   - Improper lock usage
   - Unsafe initialization
   - Cache inconsistencies
   
   REQUIRED ACTIONS:
   - Use asyncio primitives
   - Implement proper locks
   - Ensure safe setup
   - Manage cache lifecycle

3. **State Mutation Safety**
   WATCH FOR:
   - Unprotected updates
   - Missing validations
   - Inconsistent state
   - Race conditions
   
   REQUIRED ACTIONS:
   - Use atomic operations
   - Validate all changes
   - Maintain consistency
   - Prevent races 

# Event Retention Patterns

## Lock Consistency Pattern
- **Description**: Ensures atomic operations during cleanup by using distributed locks
- **Required Actions**:
  1. Acquire lock with timeout before cleanup
  2. Perform all operations within lock
  3. Single commit per cleanup operation
  4. Release lock in finally block
- **Success Metrics**:
  - Lock acquisition rate
  - Concurrent operation prevention
  - Transaction consistency

## Memory Protection Pattern
- **Description**: Prevents unbounded memory growth through size limits
- **Required Actions**:
  1. Check payload size before persistence
  2. Use efficient size calculation methods
  3. Implement clear size limits
  4. Raise specific exceptions for violations
- **Success Metrics**:
  - Memory usage stability
  - Large payload rejection rate
  - System performance

## Transaction Safety Pattern
- **Description**: Maintains database consistency during async operations
- **Required Actions**:
  1. Execute before commit
  2. Proper error handling and rollback
  3. Atomic operations within transactions
  4. Clear transaction boundaries
- **Success Metrics**:
  - Transaction success rate
  - Data consistency
  - Recovery effectiveness

# Anti-Patterns

## Concurrent Commit Anti-Pattern
- **Description**: Multiple commits during cleanup operations
- **Prevention**:
  1. Use distributed locks
  2. Single commit point
  3. Clear transaction boundaries
  4. Proper error handling

## Memory Leak Anti-Pattern
- **Description**: Unbounded event growth without limits
- **Prevention**:
  1. Size validation before save
  2. Regular cleanup operations
  3. Clear retention policies
  4. Memory monitoring 

# Redis Operation Patterns

## Cache Consistency Pattern
- **Description**: Maintains consistency between cache and database during cleanup operations
- **Required Actions**:
  1. Delete from database first
  2. Remove from cache after successful DB operation
  3. Use consistent key patterns
  4. Handle partial failures gracefully
- **Success Metrics**:
  - Cache hit rate
  - Inconsistency detection rate
  - Recovery success rate

## Distributed Lock Pattern
- **Description**: Ensures exclusive access during critical operations
- **Required Actions**:
  1. Use SET NX with expiration
  2. Implement lock timeout
  3. Release lock in finally block
  4. Handle lock acquisition failures
- **Success Metrics**:
  - Lock contention rate
  - Failed acquisition handling
  - Deadlock prevention

## Cache Lifecycle Pattern
- **Description**: Manages event caching with proper TTL and cleanup
- **Required Actions**:
  1. Set appropriate TTL based on retention policy
  2. Clear cache entries during cleanup
  3. Handle cache misses gracefully
  4. Implement scan-based cleanup
- **Success Metrics**:
  - Cache efficiency
  - Memory usage
  - Cleanup success rate 