# Event System Flows

## Basic Event Publishing Flow
```mermaid
sequenceDiagram
    participant Publisher
    participant Redis Store
    participant Redis PubSub
    participant Subscriber
    participant Dead Letter Queue
    
    Publisher->>Publisher: Create Event Schema
    Publisher->>Redis Store: Store Event (24h TTL)
    Publisher->>Redis PubSub: Publish to Channel
    Note over Redis PubSub: Event Channel
    
    par Subscriber Processing
        Redis PubSub->>Subscriber: Event Notification
        activate Subscriber
        alt Success
            Subscriber->>Subscriber: Process Event
        else Error
            Subscriber-->>Dead Letter Queue: Store Failed Event
            Dead Letter Queue-->>Subscriber: Retry Logic
        end
        deactivate Subscriber
    end
```

## Request-Response Pattern
```mermaid
sequenceDiagram
    participant Client Service
    participant Redis
    participant Context Manager
    participant Target Service
    participant Context Cache

    Client Service->>Context Manager: Get Request Context
    Context Manager->>Client Service: Request Context with Version
    Client Service->>Redis: Publish Request Event (with Context Version)
    Note over Redis: Request Channel
    Redis->>Target Service: Request Event
    
    Target Service->>Context Cache: Check Local Context Version
    alt Cache Invalid
        Context Cache-->>Target Service: Version Mismatch
        Target Service->>Context Manager: Fetch Updated Context
        Context Manager->>Target Service: New Context
        Target Service->>Context Cache: Update Local Cache
    else Cache Valid
        Context Cache-->>Target Service: Use Cached Context
    end
    
    Target Service->>Target Service: Process Request
    Target Service->>Redis: Publish Response Event
    Note over Redis: Response Channel
    Redis->>Client Service: Response Event
    
    Note over Client Service,Target Service: Context Version Tracking
```

## Task Coordination Flow
```mermaid
sequenceDiagram
    participant External Client
    participant Master Service
    participant Context Manager
    participant Redis
    participant Project Manager
    participant Developer
    participant UX Designer
    participant Tester

    External Client->>Master Service: Submit Task Request
    Master Service->>Context Manager: Get Project Context
    Context Manager->>Master Service: Project Context
    
    Master Service->>Master Service: Break Down Task
    
    par Task Distribution
        Master Service->>Redis: Publish Planning Event
        Redis->>Project Manager: Planning Event
        Project Manager->>Redis: Publish Story Events
        
        Redis->>Developer: Story Assignment Event
        Developer->>Redis: Publish Implementation Events
        
        Redis->>UX Designer: Design Task Event
        UX Designer->>Redis: Publish Design Events
        
        Redis->>Tester: Test Task Event
        Tester->>Redis: Publish Test Result Events
    end
    
    Master Service->>Redis: Subscribe to Status Channel
    Redis->>Master Service: Agent Status Updates
    
    Master Service->>External Client: Task Progress Updates
```

## Error Handling Flow
```mermaid
sequenceDiagram
    participant Service
    participant Redis
    participant Context Manager
    participant Dead Letter Queue
    participant Error Handler

    Service->>Redis: Publish Event
    Redis->>Context Manager: Event Notification
    Context Manager->>Context Manager: Context Validation Failed
    Context Manager->>Dead Letter Queue: Store Failed Event
    Dead Letter Queue->>Error Handler: Notify Error
    Error Handler->>Service: Error Notification
    Error Handler->>Context Manager: Update Error Context
    Note over Error Handler: Retry Logic/Circuit Breaking
```

## Context Manager Interactions
```mermaid
sequenceDiagram
    participant Service
    participant Context Manager
    participant Redis
    participant Metrics Service

    Service->>Context Manager: Request Context
    Context Manager->>Context Manager: Generate Context ID
    Context Manager->>Context Manager: Add Metadata
    Context Manager->>Service: Return Context
    Service->>Redis: Publish Event with Context
    Redis->>Context Manager: Event Notification
    Context Manager->>Context Manager: Validate & Update Context
    Context Manager->>Metrics Service: Log Context Metrics
    Context Manager->>Service: Context Status Update
```

## Project-wide Context Flow
```mermaid
sequenceDiagram
    participant Master Service
    participant Context Manager
    participant Project Manager
    participant Developer
    participant UX Designer
    participant Tester

    Master Service->>Context Manager: Initialize Project Context
    Context Manager->>Project Manager: Share Project Context
    Project Manager->>Context Manager: Update Planning Context
    Context Manager->>Developer: Share Development Context
    Developer->>Context Manager: Update Implementation Context
    Context Manager->>UX Designer: Share Design Context
    UX Designer->>Context Manager: Update Design Context
    Context Manager->>Tester: Share Testing Context
    Tester->>Context Manager: Update Test Results Context
    Context Manager->>Context Manager: Analyze & Improve Prompts
    Context Manager->>Master Service: Updated Project Context
``` 