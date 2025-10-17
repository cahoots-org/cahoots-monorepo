# Event Modeling Guide for Code Generation

## Overview

This document provides a comprehensive guide for generating accurate Event Models from task descriptions. Event Modeling is a visual approach to modeling information systems using four core patterns, combined with Given/When/Then scenarios to capture business rules.

## Core Concepts

### What is Event Modeling?

Event Modeling is a collaborative visual technique for planning information systems. It models the system as a timeline read from left to right, showing:
- **What data enters the system** (Commands, External Events)
- **What happens in the system** (Events)
- **What data can be queried** (Read Models)
- **What runs automatically** (Automations)

**Key Principle**: Event Modeling describes **behavior**, not implementation. It focuses on **what** the system does, not **how** it's implemented.

## The Four Patterns

Every system can be modeled using these four fundamental patterns:

### 1. State Change Pattern
**When to use**: User or automation triggers a change in the system

**Components**:
- **Screen/UI** (optional): Shows the user interaction point
- **Command** (blue): The instruction to perform an action (e.g., "Add Item")
- **Event** (orange): The fact that something happened (e.g., "Item Added")

**Flow**: `Screen → Command → Event(s)`

**Notes**:
- Commands describe what **should** happen (imperative)
- Events describe what **did** happen (past tense)
- A command can result in multiple events
- Commands are the **only way** to change system state

**Example**: User clicks "Add to Cart" → "Add Item" command → "Item Added" event

### 2. State View Pattern
**When to use**: Displaying or querying information from the system

**Components**:
- **Screen/UI** (optional): Shows what the user sees
- **Read Model** (green): The structured data to display
- **Event(s)** (orange): The source(s) of the data

**Flow**: `Event(s) → Read Model → Screen`

**Notes**:
- Read Models can **only** query data from previously stored events
- **Information Completeness Check**: Every attribute in a Read Model must have a corresponding source in events or commands
- Read Models can aggregate data from multiple events
- **Not every slice needs a Read Model** - only those that display or query data

**Example**: "Item Added" event → "Cart Items" Read Model → displays cart contents

### 3. Automation Pattern
**When to use**: Background processes that run automatically

**Components**:
- **Triggering Event(s)**: What triggers the automation
- **Read Model** (green): Data needed for the automation
- **Gear Symbol**: Represents the automated processor
- **Command** (blue): The action the automation performs
- **Resulting Event(s)** (orange): What gets recorded

**Flow**: `Event(s) → Read Model → ⚙️ Processor → Command → Event(s)`

**Notes**:
- Automations run in the background without user interaction
- Triggered by events, timers, or system conditions
- Examples: sending emails, updating inventories, processing orders
- Implementation details (polling vs. event subscription) are not modeled

**Example**: "User Registered" → Email processor → "Send Welcome Email" → "Email Sent"

### 4. Translation Pattern
**When to use**: Receiving data from external systems

**Components**:
- **External Event** (yellow/different color): Data from outside
- **Processor** (optional): Handles translation
- **Command** (blue): Internal command with translated data
- **Internal Event** (orange): Stored in our system

**Flow**: `External Event → [Read Model] → ⚙️ Processor → Command → Internal Event`

**Variations**:
1. **Explicit Translation**: External Event → Automation → Command → Internal Event
2. **Implicit Translation**: External Event → (treated as Read Model) → Screen

**Notes**:
- Protects internal system from external changes (Anti-Corruption Layer)
- External events can come from APIs, Kafka, files, manual entry
- Translation details (HTTP, Kafka, etc.) are **not** modeled - focus on data flow

## Given/When/Then Scenarios

Given/When/Then (GWT) scenarios are critical for capturing **business rules** and **complex logic**.

### Structure

**For State Changes**:
```
GIVEN: [prerequisite events/state]
WHEN: [command is executed]
THEN: [expected event(s) or error]
```

**For State Views** (Given/Then only):
```
GIVEN: [event(s) occurred]
THEN: [expected data in Read Model]
```

**For Automations** (Given/Then only):
```
GIVEN: [triggering event(s)]
THEN: [expected resulting event(s)]
```

### When to Use GWTs

1. **Business Rules**: Any constraint or validation (e.g., "max 3 items in cart")
2. **Complex Logic**: Multi-step processes or conditional flows
3. **Error Cases**: What happens when rules are violated
4. **Edge Cases**: Boundary conditions and special scenarios
5. **Example Data**: Concrete examples with actual values

### GWT Best Practices

- **Don't save on GWTs** - define as many as needed to fully describe behavior
- **Use concrete examples** with real data (prices, quantities, IDs)
- **Place vertically** below each slice for readability
- **Include error scenarios** (THEN: expect error)
- **Provide context** with white sticky notes when needed
- Define with **business stakeholders** to capture real rules
- **Multiple events in order**: List left-to-right in sequence

### Example GWTs

**Simple validation**:
```
GIVEN: Three items are already in the cart
WHEN: User executes "Add Item" command
THEN: System raises error "Maximum 3 items allowed"
```

**With example data**:
```
GIVEN: Item priced at "5.00€" was added
WHEN: User views cart
THEN: Total price shows "5.00€"
```

**Multiple events**:
```
GIVEN: Nothing has happened
WHEN: "Add Item" command is issued for a new cart
THEN: "Cart Created" event, followed by "Item Added" event
```

## Information Completeness Check

The Information Completeness Check is a crucial validation tool that ensures **no assumptions** about data availability.

### Rules

1. **For Read Models**: Every attribute must have a source event
   - If a Read Model has "email", there must be an event or command with "email"
   - Trace backwards: Read Model ← Event ← Command ← UI/External Source

2. **For Events**: Every attribute must come from the command
   - If an event has "productId", the command must provide it
   - Or the event can derive it from other events (complex logic)

3. **For Commands**: Every attribute must come from the UI or upstream
   - If a command needs "itemId", the UI must provide it
   - Or it comes from a Read Model feeding the UI

### How to Apply

1. **Start with Read Model**: What data does it display?
2. **Trace backwards**: Which event provides this data?
3. **Check the command**: Does the command provide all event data?
4. **Check the source**: Where does the command get its data?
5. **Mark gaps**: Use red arrows to highlight missing data flows

**Visual Indicator**: Red arrows show incomplete data flows that need resolution

### Common Patterns

- **Derived data**: Total price can be calculated from item prices
- **System-generated**: IDs, timestamps often generated during processing
- **Required additions**: Often reveals missing events or attributes

## Vertical Slices

### What is a Slice?

A **slice** is a complete, isolated unit of functionality representing one feature or use case. Each slice is a vertical cut through all layers (UI, business logic, persistence).

### Slice Types

1. **State Change Slice**: Command → Event(s)
2. **State View Slice**: Event(s) → Read Model
3. **Automation Slice**: Event(s) → Read Model → Processor → Command → Event(s)
4. **Translation Slice**: External Event → Processor → Command → Event(s)

### Slice Independence

- Slices work **in isolation** with **no direct dependencies**
- Events define the API between slices
- Can be implemented **in any order**
- Can be developed by **different team members simultaneously**
- Changes to one slice rarely affect others

### Naming Slices

Use clear, descriptive names from the Event Model:
- "Add Item"
- "Remove Item"
- "Cart Items" (state view)
- "Submit Cart"
- "Clear Cart"

## Swimlanes and Context

### Swimlanes

Use **horizontal swimlanes** to group related events by domain concept:
- Shopping cart swimlane
- Inventory swimlane
- Orders swimlane
- User accounts swimlane

**Purpose**: Visual organization, shows bounded contexts

### Chapters and Sub-Chapters

Use **blue arrows** above the timeline to group slices logically:
- **Chapter**: High-level context (e.g., "Shopping")
- **Sub-Chapter**: Specific area (e.g., "Items", "Inventory", "Submission")

**Purpose**: Provides big-picture structure, like chapters in a book

## Common Modeling Scenarios

### Multiple Events from One Command

A command can produce multiple events:
```
"Add Item" command →
  - "Cart Created" event (if cart doesn't exist)
  - "Item Added" event
```

**GWT Example**:
```
GIVEN: Nothing has happened (no cart exists)
WHEN: "Add Item" command is issued
THEN: "Cart Created" event, followed by "Item Added" event
```

### Events Affecting Multiple Read Models

One event can update multiple Read Models:
```
"Item Added" event →
  - Updates "Cart Items" Read Model
  - Updates "Cart with Products" Read Model (for price changes)
```

**Visual**: Use arrows from event to all affected Read Models

### Backward Dependencies

Later events can affect earlier Read Models:
```
"Item Archived" event →
  - Affects "Cart Items" Read Model (defined earlier)
```

**Visual**: Use **dotted arrow** pointing backward to show data-only impact (not flow impact)

### Complex Business Logic

When business logic is complex, use **multiple GWTs** to capture all rules:
```
"Add Item" slice might have:
- GWT 1: Happy path (item added successfully)
- GWT 2: Max items rule (error when ≥3 items)
- GWT 3: Out of stock (error when inventory = 0)
- GWT 4: Price validation (error when price invalid)
```

### Conditional Flows and Errors

**Don't model conditions in the main flow** - use separate flows:
- Model the "good case" first
- Create separate models for error cases
- Use **alternative flow markers** (sticky note with link)
- Define error cases as GWTs

**Example**: Main flow shows successful cart submission, separate flow shows "Submit Cart Error" for validation failures

## What NOT to Model

### Implementation Details

❌ **Don't model**:
- Database types (PostgreSQL, MongoDB)
- API protocols (REST, GraphQL, gRPC)
- Message queues (Kafka, RabbitMQ)
- Caching strategies
- Authentication mechanisms
- Specific algorithms or code logic

✅ **Do model**:
- Data flow (where data comes from and goes to)
- Business rules (what should/shouldn't happen)
- User interactions (what users can do)
- System behavior (what the system does)

### Technology Stack

Event Modeling is **technology agnostic**. The same model can be implemented with:
- Different languages (Python, Java, Go)
- Different databases (SQL, NoSQL, Event Store)
- Different architectures (monolith, microservices, serverless)

**Focus**: What the system does, not how it's built

### How Automations Work

Don't specify whether automations use:
- Polling vs. Event subscription
- Synchronous vs. Asynchronous processing
- Single-threaded vs. Multi-threaded

**Focus**: What triggers them and what they produce

### Screen Design Details

Use **low-fidelity wireframes**:
- Simple boxes and labels
- Basic layout (buttons, fields, lists)
- Focus on **data**, not aesthetics

❌ Don't worry about:
- Colors, fonts, spacing
- Exact UI/UX design
- Responsive design
- Accessibility details

## Generating Event Models from Tasks

### Step-by-Step Process

#### 1. Identify Use Cases
Break down the task into discrete user actions or system behaviors:
- What can users do?
- What happens automatically?
- What external systems interact?

#### 2. Start with State Changes
For each user action:
- Define the Command (what user wants)
- Define resulting Event(s) (what happened)
- Optional: Sketch simple UI

#### 3. Add State Views
For each screen or query:
- Define what data is displayed (Read Model)
- Identify source Events
- Apply Information Completeness Check

#### 4. Model Automations
For background processes:
- Identify triggering event(s)
- Define Read Model for needed data
- Define command the automation issues
- Define resulting event(s)

#### 5. Handle External Systems
For integrations:
- Define External Event (what comes in)
- Model Translation (convert to internal)
- Store as Internal Event

#### 6. Define Business Rules
For each slice:
- Add GWT for happy path
- Add GWT for each constraint/validation
- Add GWT for error cases
- Include concrete examples

#### 7. Apply Information Completeness
For each element:
- Trace data backward to source
- Add missing attributes
- Mark incomplete flows (red arrows)
- Resolve gaps

#### 8. Organize the Model
- Group events in swimlanes
- Add chapters/sub-chapters
- Link duplicate elements
- Create alternative flows as needed

### Example: E-Commerce Cart

**Task**: "Build a shopping cart where users can add items, view cart contents, and submit orders"

**Event Model**:

**Slice 1: Add Item (State Change)**
- Command: "Add Item" (productId, price, quantity)
- Events: "Cart Created" (if new), "Item Added"
- GWT 1: GIVEN empty cart, WHEN add item, THEN Cart Created + Item Added
- GWT 2: GIVEN 3 items in cart, WHEN add item, THEN error "max 3 items"

**Slice 2: Cart Items (State View)**
- Read Model: "Cart Items" (itemId, productId, price, quantity, totalPrice)
- Source Events: "Cart Created", "Item Added", "Item Removed", "Item Archived"
- GWT: GIVEN item added with price 5.00€, THEN Read Model shows totalPrice 5.00€

**Slice 3: Submit Cart (State Change)**
- Command: "Submit Cart" (cartId, orderedProducts[])
- Event: "Cart Submitted"
- GWT 1: GIVEN item in cart, WHEN submit, THEN Cart Submitted
- GWT 2: GIVEN empty cart, WHEN submit, THEN error "cannot submit empty cart"

**Slice 4: Publish to Order System (Automation)**
- Trigger: "Cart Submitted" event
- Read Model: "Submitted Cart Data"
- Processor: Cart Publisher
- Command: "Publish Cart"
- Event: "External Cart Published" (yellow)
- GWT: GIVEN cart submitted, THEN External Cart Published

**Slice 5: Inventory Update (Translation)**
- External Event: "Inventory Changed" (productId, quantity)
- Processor: Inventory Translator
- Command: "Change Inventory"
- Internal Event: "Inventory Changed"
- GWT: GIVEN external inventory change, THEN internal Inventory Changed event stored

## Common Pitfalls

### 1. Modeling Implementation
**Problem**: Including database schemas, API endpoints, code logic
**Solution**: Focus only on data flow and business behavior

### 2. Assuming Data Exists
**Problem**: Not verifying where data comes from
**Solution**: Apply Information Completeness Check rigorously

### 3. Skipping GWTs
**Problem**: Not defining business rules or edge cases
**Solution**: Define GWTs for every rule, constraint, and error case

### 4. Too Few Slices
**Problem**: Modeling large chunks instead of small, focused slices
**Solution**: Break down into atomic, independent slices

### 5. Modeling Conditions in Flow
**Problem**: Trying to show if/else logic in main timeline
**Solution**: Create separate flows for alternatives

### 6. Forgetting Errors
**Problem**: Only modeling happy paths
**Solution**: Create error case GWTs and alternative flows

### 7. Over-Designing Screens
**Problem**: Spending too much time on UI details
**Solution**: Use simple sketches focused on data

### 8. Not Using Event Sourcing Mindset
**Problem**: Thinking in terms of CRUD (Create, Read, Update, Delete)
**Solution**: Think in terms of events (facts that happened)

## Complex Business Logic Handling

When dealing with complex business logic:

### 1. Use Multiple GWTs per Slice
Don't try to capture all logic in one GWT. Create separate GWTs for:
- Happy path
- Each business rule
- Each constraint
- Each error condition
- Edge cases
- Example scenarios

### 2. Create Specialized Read Models
Don't force all data into generic Read Models. Create **use-case-specific** Read Models:
- "Carts with Products" (maps products to affected carts)
- "Active Cart Sessions" (tracks all active carts)
- "Submitted Cart Data" (prepared for export)

### 3. Model Derived Logic Separately
When logic involves calculations or transformations:
- Show the input data (from events)
- Show the output data (in Read Model or Event)
- Use GWT with example data to show the transformation
- **Don't** specify the algorithm

**Example**:
```
GIVEN: Item with price 5.00€ added
GIVEN: Item with price 3.00€ added
THEN: Total price shows 8.00€
```

### 4. Break Down Complex Automations
If an automation does multiple things:
- Split into multiple automation slices
- Each automation does one thing
- Chain them via events

### 5. Use Chapters for Context
Group related slices under chapters to show:
- Which slices work together
- Business context
- Domain boundaries

## Not Every Slice Has a Read Model

**Important**: Only create Read Models when you need to **query or display** data.

### Slices WITHOUT Read Models:

1. **Pure State Changes**
   - Example: "Clear Cart" command → "Cart Cleared" event
   - No query needed, just records the action

2. **Event-to-Event Automations**
   - Example: "Payment Received" → Auto-process → "Order Confirmed"
   - May not need to query any data

3. **Simple Translations**
   - Example: External event → Direct command → Internal event
   - Translation might be simple field mapping

### Slices WITH Read Models:

1. **State Views**
   - Displaying data to users
   - Showing lists, details, summaries

2. **Validation Logic**
   - Checking constraints (e.g., max items in cart)
   - Reading current state to validate commands

3. **Complex Automations**
   - Need to query current state
   - Aggregate data from multiple events

4. **Reporting and Analytics**
   - Generating reports
   - Calculating metrics

**Rule of Thumb**: If the slice doesn't need to know "what's the current state?" or "what data should I display?", it probably doesn't need a Read Model.

## Summary Checklist

When generating an Event Model:

- [ ] Identify all use cases and user actions
- [ ] Create State Change slices for each action
- [ ] Create State View slices for each query/display
- [ ] Model automations for background processes
- [ ] Model translations for external integrations
- [ ] Define GWTs for all business rules
- [ ] Define GWTs for error cases
- [ ] Apply Information Completeness Check to all elements
- [ ] Only create Read Models when querying/displaying data
- [ ] Organize with swimlanes and chapters
- [ ] Use concrete examples in GWTs
- [ ] Focus on behavior, not implementation
- [ ] Ensure slices are independent
- [ ] Mark alternative flows
- [ ] Verify all data has a source

## Key Principles

1. **Behavior over Implementation**: Model what the system does, not how
2. **Events are Facts**: Past tense, immutable, what actually happened
3. **Commands are Intentions**: Imperative, what we want to happen
4. **Information Completeness**: Every piece of data must have a verified source
5. **Slices are Independent**: No direct dependencies between slices
6. **GWTs Capture Rules**: Business logic lives in Given/When/Then scenarios
7. **Visual and Clear**: Anyone should understand it without explanation
8. **Examples over Abstractions**: Concrete data beats generic descriptions
9. **Read Models are Optional**: Only when you need to query or display
10. **Fail Fast on Complexity**: Break down complex scenarios into multiple GWTs

## References

- **Event Modeling Official**: https://eventmodeling.org
- **Behavior-Driven Development (BDD)**: https://en.wikipedia.org/wiki/Behavior-driven_development
- **Vertical Slice Architecture**: Focus on features, not layers
- **Information Completeness Check**: Validate data sources at every step

---

*This guide is based on "Understanding Event Sourcing" by Martin Dilger and the Event Modeling methodology by Adam Dymitruk.*
