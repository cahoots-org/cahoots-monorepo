# Agent Context Management Event Flow

## Events
1. ConversationStarted
   - conversationId: UUID
   - userId: UUID
   - startedAt: DateTime
   - initialContext: Dict
   - agentType: String

2. ContextUpdated
   - conversationId: UUID
   - updatedAt: DateTime
   - contextDiff: Dict
   - reason: String
   - updatedBy: String (agent/user id)

3. AgentActionTaken
   - conversationId: UUID
   - actionId: UUID
   - actionType: String
   - parameters: Dict
   - timestamp: DateTime
   - agentId: String
   - result: Dict

4. AgentDecisionMade
   - conversationId: UUID
   - decisionId: UUID
   - decisionType: String
   - reasoning: String
   - timestamp: DateTime
   - agentId: String
   - context: Dict

5. FileStateChanged
   - conversationId: UUID
   - filePath: String
   - changeType: String (created/modified/deleted)
   - timestamp: DateTime
   - agentId: String
   - diff: String

## Commands
1. StartConversation
   - userId: UUID
   - initialContext: Dict
   - agentType: String

2. UpdateContext
   - conversationId: UUID
   - contextDiff: Dict
   - reason: String
   - updatedBy: String

3. TakeAction
   - conversationId: UUID
   - actionType: String
   - parameters: Dict
   - agentId: String

4. MakeDecision
   - conversationId: UUID
   - decisionType: String
   - context: Dict
   - agentId: String

5. ChangeFileState
   - conversationId: UUID
   - filePath: String
   - changeType: String
   - diff: String
   - agentId: String

## Views/Projections
1. ConversationStateView
   - conversationId: UUID
   - currentContext: Dict
   - lastUpdated: DateTime
   - activeAgents: List[String]
   - status: String

2. AgentDecisionHistoryView
   - conversationId: UUID
   - decisions: List[Decision]
     - decisionId: UUID
     - timestamp: DateTime
     - type: String
     - reasoning: String
     - context: Dict

3. FileSystemStateView
   - conversationId: UUID
   - files: Dict[String, FileState]
     - path: String
     - lastModified: DateTime
     - lastModifiedBy: String
     - currentState: String

4. AgentActivityView
   - agentId: String
   - activeConversations: List[UUID]
   - recentActions: List[Action]
   - recentDecisions: List[Decision]

## Workflows
1. Start New Agent Conversation
   ```
   Command: StartConversation
   Event: ConversationStarted
   Views: 
   - Create ConversationStateView
   - Update AgentActivityView
   ```

2. Agent Makes Decision
   ```
   Command: MakeDecision
   Events:
   - AgentDecisionMade
   - ContextUpdated (if decision affects context)
   Views:
   - Update ConversationStateView
   - Update AgentDecisionHistoryView
   - Update AgentActivityView
   ```

3. Agent Takes Action
   ```
   Command: TakeAction
   Events:
   - AgentActionTaken
   - FileStateChanged (if action affects files)
   - ContextUpdated (if action affects context)
   Views:
   - Update ConversationStateView
   - Update FileSystemStateView
   - Update AgentActivityView
   ```

## Business Rules
1. Each conversation must maintain a consistent context state
2. Agents can only access files within their permitted workspace
3. Context updates must be traceable to specific decisions or actions
4. File changes must be atomic and consistent
5. Agent decisions must include reasoning and relevant context
6. Concurrent agent actions must be properly sequenced

## Special Considerations for Agent Communication
1. Event Replay
   - Agents can rebuild their understanding by replaying conversation events
   - Context can be reconstructed at any point in time
   - Decision patterns can be analyzed for improvement

2. Consistency Guarantees
   - Each event represents an atomic fact about the system
   - Views provide consistent snapshots of system state
   - Event ordering preserves causality between agent actions

3. Scalability
   - Events can be partitioned by conversationId
   - Views can be cached and updated incrementally
   - Different projections can serve different agent needs 