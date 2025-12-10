"""Unified Domain Analyzer

Single LLM call that extracts ALL domain analysis:
- Events
- State Machines
- Commands/Queries (CQRS)
- Database Schema

This replaces 4 separate LLM calls with 1 comprehensive analysis.
"""

from typing import List, Dict, Any
import time
from app.models import Task
from app.analyzer.llm_client import LLMClient, LocalLLMClient
from app.analyzer.validation_tools import VALIDATION_TOOLS, execute_tool_call
from app.analyzer.event_extractor import DomainEvent, EventType, EVENT_TYPE_MAPPING
from app.analyzer.state_machine_detector import StateMachine, StateTransition, TransitionType
from app.analyzer.cqrs_detector import Command, Query, CQRSAnalysis
from app.analyzer.schema_generator import Entity, Field, SchemaAnalysis
from app.metrics import (
    event_modeling_subphase_duration,
    event_modeling_llm_calls_per_subphase,
    event_modeling_validation_retries
)


class UnifiedDomainAnalyzer:
    """Single-pass domain analysis that extracts everything at once"""

    def __init__(self, llm_client: LLMClient, task_event_emitter=None):
        self.llm = llm_client
        self.task_event_emitter = task_event_emitter

    async def analyze_domain_from_description(self, root_task: Task, user_id: str = None) -> Dict[str, Any]:
        """
        Perform event modeling analysis from just the root task description (before decomposition).

        This is used when Event Modeling runs BEFORE task decomposition to establish
        the domain model first.

        Args:
            root_task: Root task with description
            user_id: User ID for emitting progress events

        Returns:
            Dictionary with events, commands, read_models, user_interactions, and automations
        """
        print(f"[UnifiedDomainAnalyzer] Analyzing domain from description only (pre-decomposition)")

        # Sub-phase 1: Initial analysis from description
        start_time = time.time()
        analysis = await self._analyze_description_only(root_task)
        duration = time.time() - start_time
        event_modeling_subphase_duration.labels(subphase="analyze_description").observe(duration)
        event_modeling_llm_calls_per_subphase.labels(subphase="analyze_description").inc()
        print(f"[UnifiedDomainAnalyzer] Sub-phase analyze_description took {duration:.2f}s")

        # Sub-phase 2: Swimlanes and chapters
        start_time = time.time()
        print(f"[UnifiedDomainAnalyzer] Detecting swimlanes and chapters...")
        analysis = await self._detect_swimlanes_and_chapters(root_task, analysis)
        duration = time.time() - start_time
        event_modeling_subphase_duration.labels(subphase="swimlanes_chapters").observe(duration)
        event_modeling_llm_calls_per_subphase.labels(subphase="swimlanes_chapters").inc()
        print(f"[UnifiedDomainAnalyzer] Sub-phase swimlanes_chapters took {duration:.2f}s")

        # Sub-phase 3: Wireframes and data flow
        start_time = time.time()
        print(f"[UnifiedDomainAnalyzer] Generating wireframes and data flow...")
        analysis = await self._generate_wireframes_and_dataflow(root_task, analysis)
        duration = time.time() - start_time
        event_modeling_subphase_duration.labels(subphase="wireframes_dataflow").observe(duration)
        event_modeling_llm_calls_per_subphase.labels(subphase="wireframes_dataflow").inc()
        print(f"[UnifiedDomainAnalyzer] Sub-phase wireframes_dataflow took {duration:.2f}s")

        # Skip data flow validation - too slow with retry loops
        # Final validation will catch major issues

        # Sub-phase 4: Validation and fixing
        validation_start = time.time()
        print(f"[UnifiedDomainAnalyzer] Running final validation...")
        from app.analyzer.event_model_validator import EventModelValidator
        validator = EventModelValidator()

        max_retries = 3  # Reduced from 10 to 3
        actual_retries = 0
        for retry in range(max_retries):
            validation_iter_start = time.time()
            is_valid, validation_issues = validator.validate(analysis)
            validation_iter_duration = time.time() - validation_iter_start
            event_modeling_subphase_duration.labels(subphase="validation").observe(validation_iter_duration)

            if is_valid:
                print(f"[UnifiedDomainAnalyzer] Final validation passed")
                break

            errors = [issue for issue in validation_issues if issue.severity == 'error']

            if errors and retry < max_retries - 1:
                print(f"[UnifiedDomainAnalyzer] Final validation failed with {len(errors)} errors (attempt {retry + 1}/{max_retries})")
                fix_start = time.time()
                analysis = await self._fix_validation_errors(analysis, validation_issues)
                fix_duration = time.time() - fix_start
                event_modeling_subphase_duration.labels(subphase="fix_errors").observe(fix_duration)
                event_modeling_llm_calls_per_subphase.labels(subphase="fix_errors").inc()
                actual_retries += 1
                print(f"[UnifiedDomainAnalyzer] Sub-phase fix_errors took {fix_duration:.2f}s")
            else:
                print(f"[UnifiedDomainAnalyzer] Proceeding with {len(errors)} validation errors after {max_retries} attempts")
                break

        # Record the number of retries
        event_modeling_validation_retries.observe(actual_retries)
        total_validation_duration = time.time() - validation_start
        print(f"[UnifiedDomainAnalyzer] Total validation phase took {total_validation_duration:.2f}s with {actual_retries} fix retries")

        # Emit progress
        if self.task_event_emitter and user_id:
            await self.task_event_emitter.emit_event_modeling_progress(
                root_task,
                user_id,
                events_count=len(analysis.get("events", [])),
                commands_count=len(analysis.get("commands", [])),
                read_models_count=len(analysis.get("read_models", [])),
                interactions_count=len(analysis.get("user_interactions", [])),
                automations_count=len(analysis.get("automations", []))
            )

        return analysis

    async def analyze_domain(self, task_tree: List[Task], root_task: Task = None, user_id: str = None) -> Dict[str, Any]:
        """
        Perform complete domain analysis, batching if needed.

        Args:
            task_tree: Complete task tree (root + all descendants)

        Returns:
            Dictionary with events, state_machines, cqrs_analysis, and schema
        """
        # Collect all atomic tasks
        atomic_tasks = [t for t in task_tree if t.is_atomic and t.implementation_details]

        if not atomic_tasks:
            return {
                "events": [],
                "commands": [],
                "read_models": [],
                "user_interactions": [],
                "automations": []
            }

        # Build context
        if root_task is None:
            root_task = next((t for t in task_tree if t.parent_id is None), None)

        # Batch tasks if we have too many (to avoid token limits)
        batch_size = 20  # Process 20 tasks at a time
        batches = []
        for i in range(0, len(atomic_tasks), batch_size):
            batch = atomic_tasks[i:i + batch_size]
            task_descriptions = []
            for task in batch:
                task_descriptions.append({
                    "description": task.description,
                    "implementation": task.implementation_details[:500] if task.implementation_details else ""
                })
            batches.append(task_descriptions)

        # Process each batch and combine results
        all_events = []
        all_commands = []
        all_read_models = []
        all_user_interactions = []
        all_automations = []

        for batch_idx, task_descriptions in enumerate(batches):
            print(f"[UnifiedDomainAnalyzer] Processing batch {batch_idx + 1}/{len(batches)} ({len(task_descriptions)} tasks)")

            # Generate batch without validation (validation happens once at the end)
            batch_start = time.time()
            batch_result = await self._analyze_batch(root_task, task_descriptions, len(atomic_tasks), None)
            batch_duration = time.time() - batch_start
            event_modeling_subphase_duration.labels(subphase="analyze_description").observe(batch_duration)
            event_modeling_llm_calls_per_subphase.labels(subphase="analyze_description").inc()
            print(f"[UnifiedDomainAnalyzer] Sub-phase analyze_description (batch {batch_idx + 1}) took {batch_duration:.2f}s")

            all_events.extend(batch_result.get("events", []))
            all_commands.extend(batch_result.get("commands", []))
            all_read_models.extend(batch_result.get("read_models", []))
            all_user_interactions.extend(batch_result.get("user_interactions", []))
            all_automations.extend(batch_result.get("automations", []))

            # Emit progress after each batch
            if self.task_event_emitter and root_task and user_id:
                await self.task_event_emitter.emit_event_modeling_progress(
                    root_task,
                    user_id,
                    events_count=len(all_events),
                    commands_count=len(all_commands),
                    read_models_count=len(all_read_models),
                    interactions_count=len(all_user_interactions),
                    automations_count=len(all_automations)
                )
                print(f"[UnifiedDomainAnalyzer] Emitted progress: {len(all_events)} events, {len(all_commands)} commands, {len(all_read_models)} read models")

        # Deduplicate by name (events are DomainEvent objects, others are dicts)
        dedup_start = time.time()
        events = self._deduplicate_events(all_events)
        commands = self._deduplicate_by_name(all_commands)
        read_models = self._deduplicate_by_name(all_read_models)
        user_interactions = self._deduplicate_user_interactions(all_user_interactions)
        automations = self._deduplicate_by_name(all_automations)
        dedup_duration = time.time() - dedup_start
        event_modeling_subphase_duration.labels(subphase="deduplication").observe(dedup_duration)
        print(f"[UnifiedDomainAnalyzer] Sub-phase deduplication took {dedup_duration:.2f}s")

        combined_result = {
            "events": events,
            "commands": commands,
            "read_models": read_models,
            "user_interactions": user_interactions,
            "automations": automations
        }

        # If we had multiple batches, make a final consolidation pass to ensure completeness
        if len(batches) > 1:
            print(f"[UnifiedDomainAnalyzer] Making final consolidation pass to ensure completeness")
            consolidation_start = time.time()
            combined_result = await self._consolidate_event_model(root_task, combined_result, atomic_tasks)
            consolidation_duration = time.time() - consolidation_start
            event_modeling_subphase_duration.labels(subphase="consolidation").observe(consolidation_duration)
            event_modeling_llm_calls_per_subphase.labels(subphase="consolidation").inc()
            print(f"[UnifiedDomainAnalyzer] Sub-phase consolidation took {consolidation_duration:.2f}s")

        # Sub-phase: Swimlanes and chapters
        start_time = time.time()
        print(f"[UnifiedDomainAnalyzer] Detecting swimlanes and chapters...")
        combined_result = await self._detect_swimlanes_and_chapters(root_task, combined_result)
        duration = time.time() - start_time
        event_modeling_subphase_duration.labels(subphase="swimlanes_chapters").observe(duration)
        event_modeling_llm_calls_per_subphase.labels(subphase="swimlanes_chapters").inc()
        print(f"[UnifiedDomainAnalyzer] Sub-phase swimlanes_chapters took {duration:.2f}s")

        # Sub-phase: Wireframes and data flow
        start_time = time.time()
        print(f"[UnifiedDomainAnalyzer] Generating wireframes and data flow...")
        combined_result = await self._generate_wireframes_and_dataflow(root_task, combined_result)
        duration = time.time() - start_time
        event_modeling_subphase_duration.labels(subphase="wireframes_dataflow").observe(duration)
        event_modeling_llm_calls_per_subphase.labels(subphase="wireframes_dataflow").inc()
        print(f"[UnifiedDomainAnalyzer] Sub-phase wireframes_dataflow took {duration:.2f}s")

        # Skip data flow validation - too slow with retry loops
        # Final validation will catch major issues

        # Sub-phase: Validation and fixing
        validation_start = time.time()
        print(f"[UnifiedDomainAnalyzer] Running final validation...")
        from app.analyzer.event_model_validator import EventModelValidator
        validator = EventModelValidator()

        max_retries = 3  # Reduced from 10 to 3
        actual_retries = 0
        for retry in range(max_retries):
            validation_iter_start = time.time()
            is_valid, validation_issues = validator.validate(combined_result)
            validation_iter_duration = time.time() - validation_iter_start
            event_modeling_subphase_duration.labels(subphase="validation").observe(validation_iter_duration)

            if is_valid:
                print(f"[UnifiedDomainAnalyzer] Final validation passed")
                break

            errors = [issue for issue in validation_issues if issue.severity == 'error']

            if errors and retry < max_retries - 1:
                print(f"[UnifiedDomainAnalyzer] Final validation failed with {len(errors)} errors (attempt {retry + 1}/{max_retries})")
                fix_start = time.time()
                combined_result = await self._fix_validation_errors(combined_result, validation_issues)
                fix_duration = time.time() - fix_start
                event_modeling_subphase_duration.labels(subphase="fix_errors").observe(fix_duration)
                event_modeling_llm_calls_per_subphase.labels(subphase="fix_errors").inc()
                actual_retries += 1
                print(f"[UnifiedDomainAnalyzer] Sub-phase fix_errors took {fix_duration:.2f}s")
            else:
                print(f"[UnifiedDomainAnalyzer] Proceeding with {len(errors)} validation errors after {max_retries} attempts")
                break

        # Record validation metrics
        event_modeling_validation_retries.observe(actual_retries)
        total_validation_duration = time.time() - validation_start
        print(f"[UnifiedDomainAnalyzer] Total validation phase took {total_validation_duration:.2f}s with {actual_retries} fix retries")

        return combined_result

    async def _analyze_description_only(self, root_task: Task) -> Dict[str, Any]:
        """Analyze domain from just the root task description (no atomic tasks yet).

        This is used when running Event Modeling BEFORE task decomposition.

        Args:
            root_task: Root task with description and optional context

        Returns:
            Event model with commands, events, read models, user interactions, and automations
        """
        # Extract context if available
        context_info = ""
        if root_task.context:
            if root_task.context.get("tech_stack"):
                context_info += f"\nTech Stack: {root_task.context['tech_stack']}"
            if root_task.context.get("repository_context"):
                context_info += f"\nRepository Context:\n{root_task.context['repository_context'][:1000]}"

            # Add GitHub repository context if available
            if root_task.context.get("github"):
                github_ctx = root_task.context["github"]
                print(f"[UnifiedDomainAnalyzer] ✅ Injecting GitHub context from {github_ctx.get('repo_url', 'Unknown')}")
                context_info += f"\n\nGitHub Repository Context:"
                context_info += f"\nRepository: {github_ctx.get('repo_url', 'Unknown')}"

                # Add repository summary
                if github_ctx.get("repo_summary"):
                    print(f"[UnifiedDomainAnalyzer]   - Repository summary: {len(github_ctx['repo_summary'])} chars")
                    context_info += f"\n\nRepository Overview:\n{github_ctx['repo_summary'][:2000]}"

                # Add file summaries for implementation patterns
                if github_ctx.get("file_summaries"):
                    file_count = len(github_ctx["file_summaries"])
                    print(f"[UnifiedDomainAnalyzer]   - File summaries: {file_count} files")
                    context_info += f"\n\nKey Implementation Files:"
                    for file_path, summary in list(github_ctx["file_summaries"].items())[:5]:
                        context_info += f"\n\n{file_path}:\n{summary[:500]}"
            else:
                print(f"[UnifiedDomainAnalyzer] No GitHub context available for this task")

        prompt = f"""Analyze this software project using Event Modeling methodology.

Project Description:
{root_task.description}
{context_info}

IMPORTANT - Event Modeling Principles:
1. Events are FACTS (past tense) - what happened in the system
2. Commands are INTENTIONS (imperative) - what users/systems want to do
3. Read Models are QUERIES - data views (only create when displaying/querying data)
4. Automations are BACKGROUND PROCESSES - triggered automatically
5. Focus on BEHAVIOR not implementation

STEP 1: IDENTIFY THE APPLICATION TYPE AND APPLY DOMAIN-SPECIFIC PATTERNS

First, identify which application archetype(s) this project matches:

**TWO-SIDED MARKETPLACE** (Airbnb, Uber, Fiverr, etc.):
Required patterns to include:
- Escrow/Hold mechanics: CreditHeld, CreditReleased, HoldExpired, RefundIssued
- Booking lifecycle: RequestSubmitted, RequestAccepted, RequestDeclined, BookingConfirmed, BookingCancelled, BookingRescheduled
- Completion flow: ServiceStarted, ServiceCompleted, ServiceDisputed
- No-show handling: NoShowReported, NoShowConfirmed, PenaltyApplied
- Dispute resolution: DisputeOpened, EvidenceSubmitted, DisputeResolved, DisputeEscalated
- Ratings & reviews: RatingSubmitted, RatingDisputed, ReviewPublished, ReviewHidden
- Trust & safety: UserReported, UserWarned, UserSuspended, UserBanned, VerificationRequested, VerificationCompleted

**CREDIT/TOKEN ECONOMY**:
Required patterns to include:
- Balance management: CreditsAdded, CreditsDeducted, CreditHeld, CreditReleased
- Transactions: TransactionInitiated, TransactionCompleted, TransactionFailed, TransactionReversed
- Expiration: CreditsExpiring, CreditsExpired
- Promotions: BonusAwarded, PromotionApplied

**SCHEDULING SYSTEM** (calendars, appointments, sessions):
Required patterns to include:
- Availability: AvailabilitySet, AvailabilityUpdated, SlotBlocked, SlotReleased
- Timezone handling: TimezoneDetected, TimezoneConflictResolved
- Reminders: ReminderScheduled, ReminderSent, ReminderSnoozed
- Conflicts: ConflictDetected, ConflictResolved

**SUBSCRIPTION/SaaS**:
Required patterns to include:
- Lifecycle: TrialStarted, SubscriptionCreated, SubscriptionUpgraded, SubscriptionDowngraded, SubscriptionCancelled, SubscriptionExpired
- Billing: PaymentScheduled, PaymentProcessed, PaymentFailed, PaymentRetried
- Usage: UsageLimitReached, UsageLimitWarning, OverageCharged

**CONTENT PLATFORM** (social, publishing, media):
Required patterns to include:
- Content lifecycle: ContentCreated, ContentEdited, ContentPublished, ContentArchived, ContentDeleted
- Moderation: ContentFlagged, ContentReviewed, ContentApproved, ContentRejected
- Engagement: ContentViewed, ContentLiked, ContentShared, ContentCommented

**E-COMMERCE**:
Required patterns to include:
- Cart: CartCreated, ItemAdded, ItemRemoved, CartAbandoned
- Checkout: CheckoutStarted, CheckoutCompleted, CheckoutAbandoned
- Order: OrderPlaced, OrderConfirmed, OrderCancelled, OrderRefunded
- Fulfillment: OrderShipped, OrderDelivered, DeliveryFailed, ReturnRequested, ReturnReceived

STEP 2: IDENTIFY EDGE CASES AND FAILURE SCENARIOS

For EVERY happy path event, ask yourself: "What could go wrong?"

Common failure patterns to include:
- Validation failures: ValidationFailed, InvalidDataRejected
- Authorization failures: AccessDenied, PermissionInsufficient
- Resource conflicts: ConflictDetected, ResourceLocked, ResourceUnavailable
- Timeout/expiration: SessionExpired, RequestTimedOut, LinkExpired, HoldExpired
- External service failures: PaymentFailed, NotificationFailed, IntegrationError
- User-initiated cancellations: RequestCancelled, BookingCancelled, OrderCancelled
- Rollback scenarios: TransactionRolledBack, ChangeReverted
- Retry scenarios: RetryScheduled, RetryAttempted, RetryExhausted

STEP 3: ENSURE COMPLETE ENTITY LIFECYCLES

For each major entity, ensure you have events for:
1. Creation (e.g., UserRegistered, OrderCreated)
2. Updates/Changes (e.g., ProfileUpdated, OrderModified)
3. State transitions (e.g., OrderSubmitted → OrderConfirmed → OrderShipped)
4. Cancellation/Termination (e.g., OrderCancelled, AccountDeactivated)
5. Failure states (e.g., OrderFailed, DeliveryFailed)
6. Recovery/Retry (e.g., PaymentRetried, DeliveryRescheduled)

Extract the following components:

1. EVENTS - Facts that happened (past tense):
   - name: PastTense format ("UserRegistered", "ItemAdded", "OrderPlaced")
   - event_type: user_action, system_event, integration, or state_change
   - description: What happened
   - actor: Who/what triggered it (User, System, ExternalService, etc.)
   - affected_entity: What was affected (User, Order, Cart, etc.)
   - payload: Array of field objects with:
     * name: Field name
     * type: Data type (string, integer, decimal, boolean, datetime, array, object)
     * description: What this field represents
     * source: Object describing where this data comes from:
       - type: "command_parameter" | "derived" | "system" | "lookup"
       - from: Source reference (command.parameterName, calculation formula, system field, lookup source)
       - details: Additional context if needed

   Include lifecycle events:
   - Creation: "CartCreated", "SessionStarted", "UserRegistered"
   - Changes: "ItemAdded", "PriceChanged", "StatusUpdated"
   - Completion: "OrderSubmitted", "SessionEnded", "GameFinished"

2. COMMANDS - User/system intentions (imperative):
   - name: Imperative format ("AddItem", "RegisterUser", "SubmitOrder")
   - description: What the command does
   - parameters: Array of parameter objects with:
     * name: Parameter name
     * type: Data type (string, integer, decimal, boolean, datetime, array, object)
     * description: What this parameter represents
     * required: Boolean (true/false)
     * constraints: Optional object with min, max, pattern, enum
     * source: Object describing where this data comes from:
       - type: "ui_input" | "url_parameter" | "read_model" | "system" | "session"
       - details: Additional context (wireframe component, route, field name, etc.)
   - triggers_events: Events produced (list of event names)

   Each command represents a State Change slice (Command → Event(s))

3. READ MODELS - Data views (only when querying/displaying):
   - name: What data is shown ("CartItems", "UserProfile", "OrderHistory")
   - description: Purpose of this view
   - fields: Array of field objects with:
     * name: Field name
     * type: Data type (string, integer, decimal, boolean, datetime, array, object)
     * item_type: For arrays, the type of items
     * schema: For arrays of objects, the schema of each object
     * description: What this field represents
     * source: Object describing where this data comes from:
       - type: "event_field" | "aggregation" | "derived"
       - from: Source reference (EventName.fieldName, aggregation formula, calculation)
       - events: Array of event names that populate this field

   CRITICAL: Only create read models when:
   - Displaying data to users
   - Querying current state for validation
   - Feeding data to automations
   - NOT for every command/event

   Each read model represents a State View slice (Events → Read Model)

4. USER INTERACTIONS - How users trigger commands:
   - action: User action ("Click submit", "Enter email", "Select item")
   - triggers_command: Command name
   - viewed_read_model: Read model shown (if any)

5. AUTOMATIONS - Background processes (Event → Process → Event):
   - name: What the automation does
   - trigger_event: Event that triggers it
   - result_events: Events it produces

   Each automation represents an Automation slice (Event → Read Model → Processor → Command → Event)

REQUIRED OUTPUT FORMAT - You MUST include ALL 5 sections:

Return JSON with exactly these keys (all are required, use empty arrays if none found):
{{
  "events": [...],
  "commands": [...],
  "read_models": [...],
  "user_interactions": [...],
  "automations": [...]
}}

Example for a shopping cart WITH COMPLETE SCHEMAS (notice the 'payload', 'parameters', and 'fields' arrays with full type information and source tracking):
{{
  "events": [
    {{
      "name": "ItemAdded",
      "event_type": "user_action",
      "description": "Item added to cart",
      "actor": "User",
      "affected_entity": "Cart",
      "payload": [
        {{"name": "cartId", "type": "string", "description": "Cart identifier", "source": {{"type": "command_parameter", "from": "AddItem.cartId"}}}},
        {{"name": "productId", "type": "string", "description": "Product added", "source": {{"type": "command_parameter", "from": "AddItem.productId"}}}},
        {{"name": "quantity", "type": "integer", "description": "Quantity added", "source": {{"type": "command_parameter", "from": "AddItem.quantity"}}}},
        {{"name": "price", "type": "decimal", "description": "Product price at add time", "source": {{"type": "lookup", "from": "ProductCatalog.price", "details": "Retrieved by productId"}}}},
        {{"name": "timestamp", "type": "datetime", "description": "When item was added", "source": {{"type": "system", "from": "server_timestamp"}}}}
      ]
    }},
    {{
      "name": "CartCreated",
      "event_type": "system_event",
      "description": "Shopping cart created",
      "actor": "System",
      "affected_entity": "Cart",
      "payload": [
        {{"name": "cartId", "type": "string", "description": "New cart ID", "source": {{"type": "system", "from": "uuid_generator"}}}},
        {{"name": "userId", "type": "string", "description": "Cart owner", "source": {{"type": "command_parameter", "from": "AddItem.userId"}}}},
        {{"name": "timestamp", "type": "datetime", "description": "Creation time", "source": {{"type": "system", "from": "server_timestamp"}}}}
      ]
    }}
  ],
  "commands": [
    {{
      "name": "AddItem",
      "description": "Add item to shopping cart",
      "parameters": [
        {{"name": "cartId", "type": "string", "description": "Cart to add to", "required": false, "source": {{"type": "url_parameter", "details": "/cart/:cartId"}}}},
        {{"name": "productId", "type": "string", "description": "Product to add", "required": true, "source": {{"type": "ui_input", "details": "productSelector component"}}}},
        {{"name": "quantity", "type": "integer", "description": "Number to add", "required": true, "constraints": {{"min": 1, "max": 99}}, "source": {{"type": "ui_input", "details": "quantityInput"}}}},
        {{"name": "userId", "type": "string", "description": "Current user", "required": true, "source": {{"type": "session", "details": "authenticated user"}}}}
      ],
      "triggers_events": ["CartCreated", "ItemAdded"]
    }},
    {{
      "name": "RemoveItem",
      "description": "Remove item from cart",
      "parameters": [
        {{"name": "cartId", "type": "string", "description": "Cart to remove from", "required": true, "source": {{"type": "url_parameter", "details": "/cart/:cartId"}}}},
        {{"name": "itemId", "type": "string", "description": "Item to remove", "required": true, "source": {{"type": "ui_input", "details": "removeButton in item row"}}}}
      ],
      "triggers_events": ["ItemRemoved"]
    }}
  ],
  "read_models": [
    {{
      "name": "CartItems",
      "description": "Display items in cart",
      "fields": [
        {{
          "name": "items",
          "type": "array",
          "item_type": "object",
          "schema": [
            {{"name": "productId", "type": "string"}},
            {{"name": "quantity", "type": "integer"}},
            {{"name": "price", "type": "decimal"}}
          ],
          "description": "List of cart items",
          "source": {{"type": "event_field", "from": "ItemAdded", "events": ["ItemAdded", "ItemRemoved"]}}
        }},
        {{
          "name": "totalPrice",
          "type": "decimal",
          "description": "Sum of all items",
          "source": {{"type": "aggregation", "from": "SUM(items.price * items.quantity)", "events": ["ItemAdded", "ItemRemoved"]}}
        }},
        {{
          "name": "itemCount",
          "type": "integer",
          "description": "Total number of items",
          "source": {{"type": "aggregation", "from": "COUNT(items)", "events": ["ItemAdded", "ItemRemoved"]}}
        }}
      ]
    }}
  ],
  "user_interactions": [
    {{"action": "Click 'Add to Cart' button", "triggers_command": "AddItem", "viewed_read_model": "ProductDetails"}},
    {{"action": "Click 'Remove' button", "triggers_command": "RemoveItem", "viewed_read_model": "CartItems"}}
  ],
  "automations": [
    {{"name": "Publish cart to order system", "trigger_event": "CartSubmitted", "result_events": ["ExternalCartPublished"]}}
  ]
}}

6. AUTOMATIC BEHAVIORS - System behaviors that happen without user input:
   Think through the complete behavior lifecycle. What happens automatically?

   Examples of automatic behaviors to identify:
   - Timers and intervals (pieces falling every N seconds, session timeouts, countdowns)
   - State transitions (piece locks when can't fall, order expires after timeout)
   - Spawning and generation (new piece spawns after lock, new enemy appears after delay)
   - Background calculations (score updates, health regeneration, auto-save)
   - Periodic checks (inventory level alerts, deadline reminders)

   For each automatic behavior, you MUST create:
   a) The triggering event or timer (e.g., "GameTick", "TimerElapsed", "ThresholdReached")
   b) The automation that processes it
   c) The resulting events (e.g., "PieceMoved", "PieceLocked", "NewPieceSpawned")

CRITICAL - Think Through Complete Lifecycles and State Machines:

For each entity/concept in the system, ask yourself:
1. How is it created? → Creation event (e.g., "PieceSpawned", "SessionStarted")
2. What states can it be in? → State transition events (e.g., "PieceFalling", "PieceLocked")
3. What triggers state changes? → Commands, automations, or time-based events
4. What happens automatically over time? → Timer events and automations
5. What is the end state? → Termination event (e.g., "PieceRemoved", "SessionEnded")

Example: Tetris Piece Lifecycle
- Created: "PieceSpawned" (spawned by "SpawnNextPiece" automation)
- States: Falling (automatic via "GameTick"), Moving (user commands), Locked
- State Transitions:
  * Spawned → Falling (automatic via GameTick automation)
  * Falling → Locked (when can't fall further, triggers "PieceLocked" event)
  * Locked → Removed (when line clears, triggers "LineCleared" event)
- Automatic Behaviors:
  * GameTick automation: Every 500ms → Move piece down → "PieceMoved" or "PieceLocked"
  * SpawnNextPiece automation: "PieceLocked" → Spawn new piece → "PieceSpawned"

COMPLETE Tetris Example (showing what you MUST include):
{{
  "events": [
    {{"name": "GameStarted", "event_type": "user_action", "description": "Game started", "actor": "User", "affected_entity": "Game"}},
    {{"name": "GameTick", "event_type": "system_event", "description": "Game timer tick (occurs every 500ms)", "actor": "System", "affected_entity": "Game"}},
    {{"name": "PieceSpawned", "event_type": "system_event", "description": "New piece spawned", "actor": "System", "affected_entity": "Piece"}},
    {{"name": "PieceMoved", "event_type": "user_action", "description": "Piece moved by user or gravity", "actor": "User|System", "affected_entity": "Piece"}},
    {{"name": "PieceRotated", "event_type": "user_action", "description": "Piece rotated", "actor": "User", "affected_entity": "Piece"}},
    {{"name": "PieceLocked", "event_type": "system_event", "description": "Piece locked in place (can't fall further)", "actor": "System", "affected_entity": "Piece"}},
    {{"name": "LineCleared", "event_type": "system_event", "description": "Full line cleared", "actor": "System", "affected_entity": "Board"}},
    {{"name": "GameOver", "event_type": "system_event", "description": "Game ended", "actor": "System", "affected_entity": "Game"}}
  ],
  "commands": [
    {{"name": "StartGame", "description": "Start new game", "triggers_events": ["GameStarted", "GameTick", "PieceSpawned"]}},
    {{"name": "MoveLeft", "description": "Move piece left", "triggers_events": ["PieceMoved"]}},
    {{"name": "MoveRight", "description": "Move piece right", "triggers_events": ["PieceMoved"]}},
    {{"name": "MoveDown", "description": "Soft drop (move down faster)", "triggers_events": ["PieceMoved", "PieceLocked"]}},
    {{"name": "RotatePiece", "description": "Rotate piece", "triggers_events": ["PieceRotated"]}},
    {{"name": "HardDrop", "description": "Instant drop to bottom", "triggers_events": ["PieceMoved", "PieceLocked"]}}
  ],
  "read_models": [
    {{"name": "GameBoard", "description": "Current game board state"}},
    {{"name": "Score", "description": "Current score and level"}},
    {{"name": "NextPiece", "description": "Preview of next piece"}}
  ],
  "user_interactions": [
    {{"action": "Press arrow key left", "triggers_command": "MoveLeft", "viewed_read_model": "GameBoard"}},
    {{"action": "Press arrow key down", "triggers_command": "MoveDown", "viewed_read_model": "GameBoard"}},
    {{"action": "Press spacebar", "triggers_command": "HardDrop", "viewed_read_model": "GameBoard"}}
  ],
  "automations": [
    {{"name": "AutomaticGravity", "trigger_event": "GameTick", "result_events": ["PieceMoved", "PieceLocked"]}},
    {{"name": "SpawnNextPiece", "trigger_event": "PieceLocked", "result_events": ["PieceSpawned"]}},
    {{"name": "CheckLineComplete", "trigger_event": "PieceLocked", "result_events": ["LineCleared"]}},
    {{"name": "CheckGameOver", "trigger_event": "PieceLocked", "result_events": ["GameOver"]}},
    {{"name": "GameLoop", "trigger_event": "GameTick", "result_events": ["GameTick"]}}
  ]
}}

Notice in this example:
- GameTick is a recurring system event (timer-based)
- PieceLocked is a state transition event (system detects piece can't fall)
- Automations create complete behavior loops (gravity, spawning, line clearing)
- Distinction between MoveDown (soft drop) and HardDrop (instant drop)

Guidelines:
- Be comprehensive: include ALL commands for user actions AND system actions
- Past tense for events, imperative for commands
- Include timer/tick events for time-based behaviors
- Create automations for ALL automatic behaviors
- Think through complete state machines and lifecycles
- Every user action should have a corresponding command
- Every automatic behavior should have an automation

CRITICAL - COMPLETENESS CHECKLIST:
Before returning your response, verify you have included:

1. **Domain-Specific Patterns**: If this is a marketplace, did you include escrow, disputes, ratings?
   If booking/scheduling, did you include availability, cancellations, no-shows?

2. **Failure Events**: For every happy path event, did you add the corresponding failure event?
   (e.g., PaymentProcessed → PaymentFailed, BookingConfirmed → BookingFailed)

3. **Cancellation/Reversal Events**: Can users cancel or undo actions? Include:
   - Cancellation events (RequestCancelled, BookingCancelled)
   - Refund events (RefundRequested, RefundProcessed)
   - Reversal events (TransactionReversed, ChangeReverted)

4. **Trust & Safety** (for multi-user systems): Did you include:
   - Reporting (UserReported, ContentFlagged)
   - Moderation actions (ContentRemoved, UserWarned, UserSuspended)
   - Verification (VerificationRequested, VerificationCompleted)

5. **Expiration/Timeout Events**: What happens when things expire?
   - Session/token expiration (SessionExpired, TokenExpired)
   - Hold expiration (HoldExpired, ReservationExpired)
   - Deadline passed (DeadlineMissed, OfferExpired)

6. **Notification Events**: Include events for all notifications:
   - ReminderSent, NotificationSent, AlertTriggered
   - These are often forgotten but critical for user experience

CRITICAL COMMAND RULES - AVOID THESE COMMON MISTAKES:

1. ❌ NO UI-SPECIFIC COMMANDS - Commands should represent DOMAIN ACTIONS, not UI interactions
   - BAD: "ClickSubmitButton", "DisplayProductList", "ShowCheckout", "RenderCart"
   - GOOD: "SubmitOrder", "PlaceOrder", "InitiateCheckout", "AddItem"
   - Rule: If the command verb is Click, Display, Show, Render, View → it's a UI action, NOT a domain command

2. ❌ NO QUERY/RETRIEVAL COMMANDS - Queries are handled by READ MODELS, not commands
   - BAD: "RetrieveOrderHistory", "GetUserProfile", "FetchProductDetails"
   - GOOD: Use Read Models instead (e.g., "OrderHistory" read model, "UserProfile" read model)
   - Rule: If the command verb is Retrieve, Get, Fetch, Load, Query → it's a query, use a Read Model instead

3. ❌ AVOID DUPLICATE READ MODELS - Check for semantic duplicates
   - BAD: Having both "CartContents" and "CartItems" (same thing)
   - BAD: Having both "ProductList" and "ProductCatalog" (same thing)
   - GOOD: Choose ONE name per concept and stick with it
   - Rule: Before adding a read model, check if a similar one already exists

4. ✅ COMMANDS MUST CHANGE STATE - Every command should trigger at least one event
   - Commands represent user/system INTENTIONS that change the system state
   - Examples: CreateOrder, UpdateProfile, DeleteProduct, ProcessPayment

CRITICAL: Your response must be ONLY valid JSON. No explanations, no markdown, no code blocks, no extra text.
Just the raw JSON object starting with {{ and ending with }}.
"""

        try:
            response = await self.llm.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=32000
            )

            # Extract and parse response using same robust method as _analyze_batch
            import json
            import re

            if isinstance(response, dict) and "choices" in response:
                content = response["choices"][0]["message"]["content"]

                data = None

                # Strategy 1: Try direct JSON parse
                try:
                    data = json.loads(content.strip())
                    print(f"[UnifiedDomainAnalyzer] Successfully parsed JSON directly")
                except json.JSONDecodeError:
                    pass

                # Strategy 2: Look for JSON in code blocks
                if data is None:
                    code_block_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', content)
                    if code_block_match:
                        try:
                            data = json.loads(code_block_match.group(1))
                            print(f"[UnifiedDomainAnalyzer] Successfully extracted JSON from code block")
                        except json.JSONDecodeError:
                            pass

                # Strategy 3: Find the first complete JSON object
                if data is None:
                    start_idx = content.find('{')
                    if start_idx != -1:
                        brace_count = 0
                        in_string = False
                        escape = False

                        for i in range(start_idx, len(content)):
                            char = content[i]

                            if escape:
                                escape = False
                                continue

                            if char == '\\':
                                escape = True
                                continue

                            if char == '"' and not escape:
                                in_string = not in_string
                                continue

                            if not in_string:
                                if char == '{':
                                    brace_count += 1
                                elif char == '}':
                                    brace_count -= 1
                                    if brace_count == 0:
                                        json_str = content[start_idx:i+1]
                                        try:
                                            data = json.loads(json_str)
                                            print(f"[UnifiedDomainAnalyzer] Successfully extracted JSON using brace matching")
                                            break
                                        except json.JSONDecodeError:
                                            pass

                if data is None:
                    print(f"[UnifiedDomainAnalyzer] Failed to parse JSON, returning empty analysis")
                    print(f"[UnifiedDomainAnalyzer] Response preview: {content[:500]}")
                    data = {"events": [], "commands": [], "read_models": [], "user_interactions": [], "automations": []}
            else:
                data = response

            # Parse results
            events = self._parse_events(data.get("events", []))
            commands = data.get("commands", [])
            read_models = data.get("read_models", [])
            user_interactions = data.get("user_interactions", [])
            automations = data.get("automations", [])

            print(f"[UnifiedDomainAnalyzer] Description-based analysis returned: {len(events)} events, {len(commands)} commands, {len(read_models)} read models")

            return {
                "events": events,
                "commands": commands,
                "read_models": read_models,
                "user_interactions": user_interactions,
                "automations": automations
            }

        except Exception as e:
            import traceback
            print(f"Error in description-based domain analysis: {e}")
            traceback.print_exc()
            return {
                "events": [],
                "commands": [],
                "read_models": [],
                "user_interactions": [],
                "automations": []
            }

    async def _analyze_batch(self, root_task, task_descriptions: list, total_tasks: int, validation_feedback: str = None) -> Dict[str, Any]:
        """Analyze a single batch of tasks.

        Args:
            root_task: Root task for context
            task_descriptions: List of atomic tasks to analyze
            total_tasks: Total number of tasks
            validation_feedback: Optional feedback from previous validation attempt
        """

        prompt = f"""Analyze this software project using Event Modeling methodology.

Project: {root_task.description if root_task else ""}

Note: Analyzing {len(task_descriptions)} of {total_tasks} total tasks.

Atomic Tasks:
{task_descriptions}

IMPORTANT - Event Modeling Principles:
1. Events are FACTS (past tense) - what happened in the system
2. Commands are INTENTIONS (imperative) - what users/systems want to do
3. Read Models are QUERIES - data views (only create when displaying/querying data)
4. Automations are BACKGROUND PROCESSES - triggered automatically
5. Focus on BEHAVIOR not implementation

STEP 1: IDENTIFY THE APPLICATION TYPE AND APPLY DOMAIN-SPECIFIC PATTERNS

First, identify which application archetype(s) this project matches and include the required patterns:

**TWO-SIDED MARKETPLACE**: Include escrow (CreditHeld/Released), booking lifecycle (RequestSubmitted/Accepted/Declined),
  disputes (DisputeOpened/Resolved), ratings (RatingSubmitted), no-shows (NoShowReported/PenaltyApplied)

**CREDIT/TOKEN ECONOMY**: Include balance events (CreditsHeld/Released/Expired), transactions (TransactionCompleted/Failed/Reversed)

**SCHEDULING SYSTEM**: Include availability (AvailabilitySet/Updated), reminders (ReminderScheduled/Sent), conflicts (ConflictDetected)

**SUBSCRIPTION/SaaS**: Include lifecycle (TrialStarted, SubscriptionCreated/Cancelled), billing (PaymentProcessed/Failed)

STEP 2: ENSURE COMPLETE EVENT COVERAGE

For EVERY happy path, include the corresponding failure/cancellation events:
- BookingConfirmed → BookingCancelled, BookingFailed
- PaymentProcessed → PaymentFailed, RefundIssued
- ServiceCompleted → ServiceDisputed, NoShowReported

For multi-user systems, include Trust & Safety events:
- UserReported, UserWarned, UserSuspended, VerificationRequested/Completed

Extract the following components:

1. EVENTS - Facts that happened (past tense):
   - name: PastTense format ("UserRegistered", "ItemAdded", "OrderPlaced")
   - event_type: user_action, system_event, integration, or state_change
   - description: What happened
   - actor: Who/what triggered it (User, System, ExternalService, etc.)
   - affected_entity: What was affected (User, Order, Cart, etc.)
   - payload: Array of field objects with:
     * name: Field name
     * type: Data type (string, integer, decimal, boolean, datetime, array, object)
     * description: What this field represents
     * source: Object describing where this data comes from:
       - type: "command_parameter" | "derived" | "system" | "lookup"
       - from: Source reference (command.parameterName, calculation formula, system field, lookup source)
       - details: Additional context if needed

   Include lifecycle events:
   - Creation: "CartCreated", "SessionStarted", "UserRegistered"
   - Changes: "ItemAdded", "PriceChanged", "StatusUpdated"
   - Completion: "OrderSubmitted", "SessionEnded", "GameFinished"

2. COMMANDS - User/system intentions (imperative):
   - name: Imperative format ("AddItem", "RegisterUser", "SubmitOrder")
   - description: What the command does
   - parameters: Array of parameter objects with:
     * name: Parameter name
     * type: Data type (string, integer, decimal, boolean, datetime, array, object)
     * description: What this parameter represents
     * required: Boolean (true/false)
     * constraints: Optional object with min, max, pattern, enum
     * source: Object describing where this data comes from:
       - type: "ui_input" | "url_parameter" | "read_model" | "system" | "session"
       - details: Additional context (wireframe component, route, field name, etc.)
   - triggers_events: Events produced (list of event names)

   Each command represents a State Change slice (Command → Event(s))

3. READ MODELS - Data views (only when querying/displaying):
   - name: What data is shown ("CartItems", "UserProfile", "OrderHistory")
   - description: Purpose of this view
   - fields: Array of field objects with:
     * name: Field name
     * type: Data type (string, integer, decimal, boolean, datetime, array, object)
     * item_type: For arrays, the type of items
     * schema: For arrays of objects, the schema of each object
     * description: What this field represents
     * source: Object describing where this data comes from:
       - type: "event_field" | "aggregation" | "derived"
       - from: Source reference (EventName.fieldName, aggregation formula, calculation)
       - events: Array of event names that populate this field

   CRITICAL: Only create read models when:
   - Displaying data to users
   - Querying current state for validation
   - Feeding data to automations
   - NOT for every command/event

   Each read model represents a State View slice (Events → Read Model)

4. USER INTERACTIONS - How users trigger commands:
   - action: User action ("Click submit", "Enter email", "Select item")
   - triggers_command: Command name
   - viewed_read_model: Read model shown (if any)

5. AUTOMATIONS - Background processes (Event → Process → Event):
   - name: What the automation does
   - trigger_event: Event that triggers it
   - result_events: Events it produces

   Each automation represents an Automation slice (Event → Read Model → Processor → Command → Event)

REQUIRED OUTPUT FORMAT - You MUST include ALL 5 sections:

Return JSON with exactly these keys (all are required, use empty arrays if none found):
{{
  "events": [...],
  "commands": [...],
  "read_models": [...],
  "user_interactions": [...],
  "automations": [...]
}}

Example for a shopping cart WITH COMPLETE SCHEMAS (notice the 'payload', 'parameters', and 'fields' arrays with full type information and source tracking):
{{
  "events": [
    {{
      "name": "ItemAdded",
      "event_type": "user_action",
      "description": "Item added to cart",
      "actor": "User",
      "affected_entity": "Cart",
      "payload": [
        {{"name": "cartId", "type": "string", "description": "Cart identifier", "source": {{"type": "command_parameter", "from": "AddItem.cartId"}}}},
        {{"name": "productId", "type": "string", "description": "Product added", "source": {{"type": "command_parameter", "from": "AddItem.productId"}}}},
        {{"name": "quantity", "type": "integer", "description": "Quantity added", "source": {{"type": "command_parameter", "from": "AddItem.quantity"}}}},
        {{"name": "price", "type": "decimal", "description": "Product price at add time", "source": {{"type": "lookup", "from": "ProductCatalog.price", "details": "Retrieved by productId"}}}},
        {{"name": "timestamp", "type": "datetime", "description": "When item was added", "source": {{"type": "system", "from": "server_timestamp"}}}}
      ]
    }},
    {{
      "name": "CartCreated",
      "event_type": "system_event",
      "description": "Shopping cart created",
      "actor": "System",
      "affected_entity": "Cart",
      "payload": [
        {{"name": "cartId", "type": "string", "description": "New cart ID", "source": {{"type": "system", "from": "uuid_generator"}}}},
        {{"name": "userId", "type": "string", "description": "Cart owner", "source": {{"type": "command_parameter", "from": "AddItem.userId"}}}},
        {{"name": "timestamp", "type": "datetime", "description": "Creation time", "source": {{"type": "system", "from": "server_timestamp"}}}}
      ]
    }}
  ],
  "commands": [
    {{
      "name": "AddItem",
      "description": "Add item to shopping cart",
      "parameters": [
        {{"name": "cartId", "type": "string", "description": "Cart to add to", "required": false, "source": {{"type": "url_parameter", "details": "/cart/:cartId"}}}},
        {{"name": "productId", "type": "string", "description": "Product to add", "required": true, "source": {{"type": "ui_input", "details": "productSelector component"}}}},
        {{"name": "quantity", "type": "integer", "description": "Number to add", "required": true, "constraints": {{"min": 1, "max": 99}}, "source": {{"type": "ui_input", "details": "quantityInput"}}}},
        {{"name": "userId", "type": "string", "description": "Current user", "required": true, "source": {{"type": "session", "details": "authenticated user"}}}}
      ],
      "triggers_events": ["CartCreated", "ItemAdded"]
    }},
    {{
      "name": "RemoveItem",
      "description": "Remove item from cart",
      "parameters": [
        {{"name": "cartId", "type": "string", "description": "Cart to remove from", "required": true, "source": {{"type": "url_parameter", "details": "/cart/:cartId"}}}},
        {{"name": "itemId", "type": "string", "description": "Item to remove", "required": true, "source": {{"type": "ui_input", "details": "removeButton in item row"}}}}
      ],
      "triggers_events": ["ItemRemoved"]
    }}
  ],
  "read_models": [
    {{
      "name": "CartItems",
      "description": "Display items in cart",
      "fields": [
        {{
          "name": "items",
          "type": "array",
          "item_type": "object",
          "schema": [
            {{"name": "productId", "type": "string"}},
            {{"name": "quantity", "type": "integer"}},
            {{"name": "price", "type": "decimal"}}
          ],
          "description": "List of cart items",
          "source": {{"type": "event_field", "from": "ItemAdded", "events": ["ItemAdded", "ItemRemoved"]}}
        }},
        {{
          "name": "totalPrice",
          "type": "decimal",
          "description": "Sum of all items",
          "source": {{"type": "aggregation", "from": "SUM(items.price * items.quantity)", "events": ["ItemAdded", "ItemRemoved"]}}
        }},
        {{
          "name": "itemCount",
          "type": "integer",
          "description": "Total number of items",
          "source": {{"type": "aggregation", "from": "COUNT(items)", "events": ["ItemAdded", "ItemRemoved"]}}
        }}
      ]
    }}
  ],
  "user_interactions": [
    {{"action": "Click 'Add to Cart' button", "triggers_command": "AddItem", "viewed_read_model": "ProductDetails"}},
    {{"action": "Click 'Remove' button", "triggers_command": "RemoveItem", "viewed_read_model": "CartItems"}}
  ],
  "automations": [
    {{"name": "Publish cart to order system", "trigger_event": "CartSubmitted", "result_events": ["ExternalCartPublished"]}}
  ]
}}

CRITICAL: For the tasks provided, identify actual commands users/system execute. Every user action needs a command.
For Tetris example:
- Commands: StartGame, MoveLeft, MoveRight, RotatePiece, DropPiece, PauseGame
- Events: GameStarted, PieceMoved, PieceRotated, PieceDropped, LineCleared, GameOver
- Read Models: GameBoard, Score, NextPiece
- User Interactions: Press arrow key left → MoveLeft, Press space → DropPiece
- Automations: LineCleared → CheckGameOver → GameOver

Guidelines:
- Be comprehensive: include ALL commands for user actions
- Past tense for events, imperative for commands
- Only create read models when displaying/querying data
- Every user action should have a corresponding command

CRITICAL - COMPLETENESS CHECKLIST:
Before returning your response, verify you have included:

1. **Domain-Specific Patterns**: If this is a marketplace, did you include escrow, disputes, ratings?
   If booking/scheduling, did you include availability, cancellations, no-shows?

2. **Failure Events**: For every happy path event, did you add the corresponding failure event?
   (e.g., PaymentProcessed → PaymentFailed, BookingConfirmed → BookingFailed)

3. **Cancellation/Reversal Events**: Include RequestCancelled, BookingCancelled, RefundRequested, etc.

4. **Trust & Safety** (for multi-user systems): Include UserReported, UserWarned, UserSuspended, VerificationRequested

5. **Expiration Events**: Include HoldExpired, SessionExpired, ReservationExpired as needed

CRITICAL COMMAND RULES - AVOID THESE COMMON MISTAKES:

1. ❌ NO UI-SPECIFIC COMMANDS - Commands should represent DOMAIN ACTIONS, not UI interactions
   - BAD: "ClickSubmitButton", "DisplayProductList", "ShowCheckout", "RenderCart", "ClickOrderReturnInitiationButton"
   - GOOD: "SubmitOrder", "PlaceOrder", "InitiateCheckout", "AddItem", "InitiateOrderReturn"
   - Rule: If the command verb is Click, Display, Show, Render, View → it's a UI action, NOT a domain command

2. ❌ NO QUERY/RETRIEVAL COMMANDS - Queries are handled by READ MODELS, not commands
   - BAD: "RetrieveOrderHistory", "GetUserProfile", "FetchProductDetails", "RetrieveOrderStatusUpdateHistory"
   - GOOD: Use Read Models instead (e.g., "OrderHistory" read model, "UserProfile" read model)
   - Rule: If the command verb is Retrieve, Get, Fetch, Load, Query → it's a query, use a Read Model instead

3. ❌ AVOID DUPLICATE READ MODELS - Check for semantic duplicates
   - BAD: Having both "CartContents" and "CartItems" (same thing, keep the more descriptive one)
   - BAD: Having both "ProductList" and "ProductCatalog" (same thing)
   - GOOD: Choose ONE name per concept and stick with it (prefer "CartItems" over "CartContents")
   - Rule: Before adding a read model, check if a similar one already exists

4. ✅ COMMANDS MUST CHANGE STATE - Every command should trigger at least one event
   - Commands represent user/system INTENTIONS that change the system state
   - Examples: CreateOrder, UpdateProfile, DeleteProduct, ProcessPayment, InitiateReturn

5. ✅ READ MODELS MUST HAVE PROPER EVENT SOURCES - Every read model field must reference the events that populate it
   - BAD: Read model "OrderStatusUpdateHistory" sourcing from event "OrderStatusUpdateHistoryRetrieved" (that's a query, not an event!)
   - GOOD: Read model "OrderStatusUpdateHistory" sourcing from events "OrderStatusUpdated", "OrderShipped", "OrderDelivered"
   - Rule: Read model sources must be actual DOMAIN EVENTS (past tense facts), not query operations

CRITICAL: Your response must be ONLY valid JSON. No explanations, no markdown, no code blocks, no extra text.
Just the raw JSON object starting with {{ and ending with }}.
"""

        # Add validation feedback if provided
        if validation_feedback:
            prompt += f"""

⚠️ CRITICAL - YOUR PREVIOUS RESPONSE HAD VALIDATION ERRORS ⚠️

The following errors MUST be fixed in your next response:

{validation_feedback}

MANDATORY FIXES:
1. If a command references an event that doesn't exist, you MUST either:
   - Add that event to the events list, OR
   - Change the command to reference an existing event
2. Event names in "triggers_events" must EXACTLY match event names in the "events" list
3. All events must be past tense (e.g., "GamePaused", not "PauseGame")
4. All commands must be imperative (e.g., "PauseGame", not "GamePaused")

DO NOT submit a response that fails these validations. Fix the issues now.

IMPORTANT: If validation tools are available, use them to check your output BEFORE returning:
- validate_event_type: Check each event type is valid
- validate_command_event_pair: Check each command triggers events
- validate_event_name: Check event names are past tense
- validate_command_name: Check command names are imperative
"""

        try:
            # Use tool-based validation for local models that support it
            if isinstance(self.llm, LocalLLMClient):
                print(f"[UnifiedDomainAnalyzer] Using tool-based validation for event model generation")
                response = await self.llm.chat_completion_with_tools(
                    messages=[{"role": "user", "content": prompt}],
                    tools=VALIDATION_TOOLS,
                    tool_executor=execute_tool_call,
                    max_tokens=32000,
                    max_rounds=3  # Limit to 3 rounds to prevent infinite loops
                )
            else:
                # Cerebras or other LLMs without tool support
                response = await self.llm.chat_completion(
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=32000  # Llama 3.3 70B supports up to 128K context
                )

            # Extract and parse response
            import json
            if isinstance(response, dict) and "choices" in response:
                content = response["choices"][0]["message"]["content"]

                # Try to extract JSON using a robust approach
                import re
                data = None

                # Strategy 1: Try direct JSON parse (if LLM followed instructions)
                try:
                    data = json.loads(content.strip())
                    print(f"[UnifiedDomainAnalyzer] Successfully parsed JSON directly")
                except json.JSONDecodeError:
                    pass

                # Strategy 2: Look for JSON in code blocks (```json ... ```)
                if data is None:
                    code_block_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', content)
                    if code_block_match:
                        try:
                            data = json.loads(code_block_match.group(1))
                            print(f"[UnifiedDomainAnalyzer] Successfully extracted JSON from code block")
                        except json.JSONDecodeError:
                            pass

                # Strategy 3: Find the first complete JSON object
                if data is None:
                    # Try to find a JSON object with balanced braces
                    start_idx = content.find('{')
                    if start_idx != -1:
                        brace_count = 0
                        in_string = False
                        escape = False

                        for i in range(start_idx, len(content)):
                            char = content[i]

                            if escape:
                                escape = False
                                continue

                            if char == '\\':
                                escape = True
                                continue

                            if char == '"' and not escape:
                                in_string = not in_string
                                continue

                            if not in_string:
                                if char == '{':
                                    brace_count += 1
                                elif char == '}':
                                    brace_count -= 1
                                    if brace_count == 0:
                                        json_str = content[start_idx:i+1]
                                        try:
                                            data = json.loads(json_str)
                                            print(f"[UnifiedDomainAnalyzer] Successfully extracted JSON using brace matching")
                                            break
                                        except json.JSONDecodeError:
                                            pass

                # If all strategies failed
                if data is None:
                    print(f"[UnifiedDomainAnalyzer] Failed to parse JSON, returning empty analysis")
                    print(f"[UnifiedDomainAnalyzer] Response preview: {content[:500]}")
                    data = {"events": [], "commands": [], "read_models": [], "user_interactions": [], "automations": []}
            elif isinstance(response, dict):
                data = response
            else:
                data = json.loads(response.strip())

            # Parse results
            events = self._parse_events(data.get("events", []))
            commands = data.get("commands", [])
            read_models = data.get("read_models", [])
            user_interactions = data.get("user_interactions", [])
            automations = data.get("automations", [])

            print(f"[UnifiedDomainAnalyzer] LLM returned: {len(events)} events, {len(commands)} commands, {len(read_models)} read models")
            if len(commands) == 0:
                print(f"[UnifiedDomainAnalyzer] WARNING: No commands extracted! Check LLM response.")
                print(f"[UnifiedDomainAnalyzer] Raw data keys: {list(data.keys())}")

            return {
                "events": events,
                "commands": commands,
                "read_models": read_models,
                "user_interactions": user_interactions,
                "automations": automations
            }

        except Exception as e:
            import traceback
            print(f"Error in unified domain analysis: {e}")
            traceback.print_exc()
            return {
                "events": [],
                "commands": [],
                "read_models": [],
                "user_interactions": [],
                "automations": []
            }

    async def _fix_validation_errors(self, analysis: Dict[str, Any], validation_issues: List) -> Dict[str, Any]:
        """Make a separate LLM call to fix validation errors."""
        import json

        # Build error descriptions with specific fix options
        errors = [issue for issue in validation_issues if issue.severity == 'error']

        error_descriptions = []
        for issue in errors:
            error_descriptions.append(f"\nERROR: {issue.message}")

            # Provide specific fix options based on error type
            if 'missing_event' in issue.details:
                missing_event = issue.details['missing_event']
                command = issue.details.get('command', '')
                error_descriptions.append(f"Fix by choosing ONE option:")
                error_descriptions.append(f'1. Add event to events list: {{"name": "{missing_event}", "event_type": "system_event", "description": "...", "actor": "System", "affected_entity": "Game"}}')
                error_descriptions.append(f'2. Change command "{command}" to reference an existing event instead')

            elif 'missing_command' in issue.details:
                missing_command = issue.details['missing_command']
                error_descriptions.append(f"Fix by adding command: {missing_command}")

            elif 'missing_read_model' in issue.details:
                missing_read_model = issue.details['missing_read_model']
                interaction = issue.details.get('interaction', '')
                available_read_models = issue.details.get('available_read_models', [])
                error_descriptions.append(f"Fix user interaction '{interaction}' by choosing ONE option:")
                error_descriptions.append(f'1. Add read model to read_models list: {{"name": "{missing_read_model}", "description": "...", "data_fields": ["..."]}}')
                if available_read_models:
                    error_descriptions.append(f'2. Change viewed_read_model to use an existing read model: {available_read_models[:3]}')
                error_descriptions.append(f'3. Set viewed_read_model to null if no read model is needed for this interaction')

            elif issue.category == 'orphaned':
                event_name = issue.details.get('event', '')
                error_descriptions.append(f"Fix event '{event_name}' by choosing ONE option:")
                error_descriptions.append(f'1. Add a command that triggers it: {{"name": "SomeCommand", "triggers_events": ["{event_name}"]}}')
                error_descriptions.append(f'2. Add an automation that produces it: {{"name": "...", "trigger_event": "...", "result_events": ["{event_name}"]}}')
                error_descriptions.append(f'3. Change event_type to "integration" if it\'s an external event')
                error_descriptions.append(f'4. Remove the event if it\'s not needed')

        errors_text = "\n".join(error_descriptions)

        # Convert analysis to JSON-serializable format
        serializable_analysis = {
            "events": [
                {
                    "name": e.name if hasattr(e, 'name') else e.get('name'),
                    "event_type": e.event_type.value if hasattr(e, 'event_type') else e.get('event_type'),
                    "description": e.description if hasattr(e, 'description') else e.get('description'),
                    "actor": e.actor if hasattr(e, 'actor') else e.get('actor'),
                    "affected_entity": e.affected_entity if hasattr(e, 'affected_entity') else e.get('affected_entity')
                }
                for e in analysis.get('events', [])
            ],
            "commands": analysis.get('commands', []),
            "read_models": analysis.get('read_models', []),
            "user_interactions": analysis.get('user_interactions', []),
            "automations": analysis.get('automations', [])
        }

        prompt = f"""You are fixing validation errors in an event model.

CURRENT EVENT MODEL (with errors):
{json.dumps(serializable_analysis, indent=2)}

VALIDATION ERRORS THAT MUST BE FIXED:
{errors_text}

YOUR TASK:
Return the COMPLETE corrected event model as JSON with ALL sections (events, commands, read_models, user_interactions, automations).
Make the minimum changes necessary to fix the errors.
Preserve all existing correct data.

Return ONLY the JSON, no explanation."""

        try:
            response = await self.llm.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=64000  # Llama 3.3 70B supports up to 128K context
            )

            # Extract and parse response
            if isinstance(response, dict) and "choices" in response:
                content = response["choices"][0]["message"]["content"]
                finish_reason = response["choices"][0].get("finish_reason", "unknown")

                if finish_reason == "length":
                    print("[UnifiedDomainAnalyzer] WARNING: Fix response was truncated due to max_tokens limit")
                    print("[UnifiedDomainAnalyzer] Consider increasing max_tokens or simplifying the event model")

                # Extract JSON using same robust method as _analyze_batch
                import re
                data = None

                # Strategy 1: Try direct JSON parse
                try:
                    data = json.loads(content.strip())
                    print("[UnifiedDomainAnalyzer] Successfully parsed fix JSON directly")
                except json.JSONDecodeError:
                    pass

                # Strategy 2: Look for JSON in code blocks
                if data is None:
                    code_block_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', content)
                    if code_block_match:
                        try:
                            data = json.loads(code_block_match.group(1))
                            print("[UnifiedDomainAnalyzer] Successfully extracted fix JSON from code block")
                        except json.JSONDecodeError:
                            pass

                # Strategy 3: Find the first complete JSON object with brace matching
                if data is None:
                    start_idx = content.find('{')
                    if start_idx != -1:
                        brace_count = 0
                        in_string = False
                        escape = False

                        for i in range(start_idx, len(content)):
                            char = content[i]

                            if escape:
                                escape = False
                                continue

                            if char == '\\':
                                escape = True
                                continue

                            if char == '"' and not escape:
                                in_string = not in_string
                                continue

                            if not in_string:
                                if char == '{':
                                    brace_count += 1
                                elif char == '}':
                                    brace_count -= 1
                                    if brace_count == 0:
                                        json_str = content[start_idx:i+1]
                                        try:
                                            data = json.loads(json_str)
                                            print("[UnifiedDomainAnalyzer] Successfully extracted fix JSON using brace matching")
                                            break
                                        except json.JSONDecodeError as e:
                                            print(f"[UnifiedDomainAnalyzer] Failed to parse fix response: {e}")
                                            # Print the problematic area
                                            if hasattr(e, 'pos'):
                                                start = max(0, e.pos - 200)
                                                end = min(len(json_str), e.pos + 200)
                                                print(f"[UnifiedDomainAnalyzer] JSON context around error: ...{json_str[start:end]}...")

                if data is None:
                    print("[UnifiedDomainAnalyzer] No valid JSON found in fix response, keeping original")
                    return analysis

                fixed_data = data
            else:
                print("[UnifiedDomainAnalyzer] Unexpected fix response format, keeping original")
                return analysis

            # Parse events (they need to be DomainEvent objects)
            fixed_data["events"] = self._parse_events(fixed_data.get("events", []))

            # Preserve fields that weren't sent to the LLM for fixing
            for key in ["swimlanes", "chapters", "wireframes", "data_flow", "slices", "event_model_validation", "event_model_markdown"]:
                if key in analysis and key not in fixed_data:
                    fixed_data[key] = analysis[key]

            print(f"[UnifiedDomainAnalyzer] Applied fixes: {len(fixed_data.get('events', []))} events, {len(fixed_data.get('commands', []))} commands")
            return fixed_data

        except Exception as e:
            print(f"[UnifiedDomainAnalyzer] Error fixing validation errors: {e}")
            return analysis

    async def _consolidate_event_model(self, root_task, combined_model: Dict[str, Any], atomic_tasks: List) -> Dict[str, Any]:
        """
        Make a final LLM call to consolidate and complete the event model from multiple batches.
        This ensures the model is comprehensive and coherent.
        """
        try:
            # Convert events to serializable format
            serializable_events = [
                {
                    "name": e.name if hasattr(e, 'name') else e.get('name'),
                    "event_type": e.event_type.value if hasattr(e, 'event_type') else e.get('event_type'),
                    "description": e.description if hasattr(e, 'description') else e.get('description'),
                    "actor": e.actor if hasattr(e, 'actor') else e.get('actor'),
                    "affected_entity": e.affected_entity if hasattr(e, 'affected_entity') else e.get('affected_entity')
                }
                for e in combined_model.get('events', [])
            ]

            current_model_summary = f"""
Current Event Model (from {len(atomic_tasks)} tasks):
- Events: {len(combined_model.get('events', []))} - {[e['name'] for e in serializable_events[:10]]}{'...' if len(serializable_events) > 10 else ''}
- Commands: {len(combined_model.get('commands', []))} - {[c['name'] for c in combined_model.get('commands', [])[:10]]}{'...' if len(combined_model.get('commands', [])) > 10 else ''}
- Read Models: {len(combined_model.get('read_models', []))} - {[r['name'] for r in combined_model.get('read_models', [])[:10]]}{'...' if len(combined_model.get('read_models', [])) > 10 else ''}
- Automations: {len(combined_model.get('automations', []))}
"""

            # Sample of tasks for context (first 10 and last 10)
            task_samples = atomic_tasks[:10] + (atomic_tasks[-10:] if len(atomic_tasks) > 10 else [])
            task_descriptions = "\n".join([f"- {t.description}" for t in task_samples])

            prompt = f"""You are completing and consolidating an Event Model for a software project.

PROJECT: {root_task.description if root_task else ""}

CURRENT MODEL STATUS:
{current_model_summary}

SAMPLE TASKS (showing {len(task_samples)} of {len(atomic_tasks)} total tasks):
{task_descriptions}

YOUR TASK:
Review the current event model and ensure it is COMPLETE and COMPREHENSIVE for all {len(atomic_tasks)} tasks.

The model was generated in batches, so it may be missing:
1. Important events that weren't captured from all task batches
2. Commands needed for complete functionality
3. Read models for displaying system state
4. Automations for background processes
5. User interactions linking UI to commands

INSTRUCTIONS:
1. Keep all existing events, commands, read models that are correct
2. ADD any missing components needed for a complete system
3. Ensure ALL commands reference existing events in triggers_events
4. Ensure ALL automations reference existing events
5. Ensure read models cover key system state queries
6. Use proper naming: Events (past tense), Commands (imperative)

Return the COMPLETE event model as JSON with all 5 required sections.

IMPORTANT: Only include events that are ACTUALLY triggered by commands or automations, or are external (integration type).

Return ONLY valid JSON, no explanation:
{{
  "events": [...],
  "commands": [...],
  "read_models": [...],
  "user_interactions": [...],
  "automations": [...]
}}"""

            response = await self.llm.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=32000,  # Llama 3.3 70B supports up to 128K context
                temperature=0.3
            )

            # Parse response
            import re
            import json

            content = response.get("content", "")
            if isinstance(content, list):
                content = content[0].get("text", "") if content else ""

            # Extract JSON using same robust method as _analyze_batch
            data = None

            # Strategy 1: Try direct JSON parse
            try:
                data = json.loads(content.strip())
                print(f"[UnifiedDomainAnalyzer] Successfully parsed consolidated JSON directly")
            except json.JSONDecodeError:
                pass

            # Strategy 2: Look for JSON in code blocks
            if data is None:
                code_block_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', content)
                if code_block_match:
                    try:
                        data = json.loads(code_block_match.group(1))
                        print(f"[UnifiedDomainAnalyzer] Successfully extracted consolidated JSON from code block")
                    except json.JSONDecodeError:
                        pass

            # Strategy 3: Find the first complete JSON object with brace matching
            if data is None:
                start_idx = content.find('{')
                if start_idx != -1:
                    brace_count = 0
                    in_string = False
                    escape = False

                    for i in range(start_idx, len(content)):
                        char = content[i]

                        if escape:
                            escape = False
                            continue

                        if char == '\\':
                            escape = True
                            continue

                        if char == '"' and not escape:
                            in_string = not in_string
                            continue

                        if not in_string:
                            if char == '{':
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    json_str = content[start_idx:i+1]
                                    try:
                                        data = json.loads(json_str)
                                        print(f"[UnifiedDomainAnalyzer] Successfully extracted consolidated JSON using brace matching")
                                        break
                                    except json.JSONDecodeError:
                                        pass

            if data:
                # Parse events to DomainEvent objects
                data["events"] = self._parse_events(data.get("events", []))
                print(f"[UnifiedDomainAnalyzer] Consolidated model: {len(data.get('events', []))} events, {len(data.get('commands', []))} commands")
                return data
            else:
                print("[UnifiedDomainAnalyzer] Failed to parse consolidation response, keeping original")
                return combined_model

        except Exception as e:
            print(f"[UnifiedDomainAnalyzer] Error consolidating event model: {e}")
            return combined_model

    def _parse_events(self, events_data: List[Dict]) -> List[DomainEvent]:
        """Parse events from response"""
        events = []
        for event_data in events_data:
            try:
                # Source task ID will be unknown for batched analysis
                source_task_id = "batch_analysis"

                # Preserve payload in metadata
                metadata = {}
                if "payload" in event_data:
                    metadata["payload"] = event_data["payload"]

                # Map LLM-generated event type to canonical value
                raw_event_type = event_data["event_type"]
                mapped_event_type = EVENT_TYPE_MAPPING.get(raw_event_type, raw_event_type)

                event = DomainEvent(
                    name=event_data["name"],
                    event_type=EventType(mapped_event_type),
                    description=event_data["description"],
                    source_task_id=source_task_id,
                    actor=event_data.get("actor"),
                    affected_entity=event_data.get("affected_entity"),
                    triggers=[],
                    metadata=metadata
                )
                events.append(event)
            except Exception as e:
                print(f"Error parsing event: {e}")
                continue
        return events

    def _deduplicate_events(self, events: List[DomainEvent]) -> List[DomainEvent]:
        """Deduplicate DomainEvent objects by name, keeping first occurrence."""
        seen = set()
        result = []
        for event in events:
            if event.name and event.name not in seen:
                seen.add(event.name)
                result.append(event)
        return result

    def _deduplicate_by_name(self, items: List[Dict]) -> List[Dict]:
        """Deduplicate dict items by name, keeping first occurrence."""
        seen = set()
        result = []
        for item in items:
            name = item.get("name")
            if name and name not in seen:
                seen.add(name)
                result.append(item)
        return result

    def _deduplicate_user_interactions(self, interactions: List[Dict]) -> List[Dict]:
        """Deduplicate user interactions by (action, triggers_command) tuple."""
        seen = set()
        result = []
        for interaction in interactions:
            action = interaction.get("action")
            triggers_command = interaction.get("triggers_command")
            key = (action, triggers_command)
            if key and key not in seen:
                seen.add(key)
                result.append(interaction)
        return result

    async def _detect_swimlanes_and_chapters(self, root_task, event_model: Dict[str, Any]) -> Dict[str, Any]:
        """Detect swimlanes and chapters using the swimlane_detector module."""
        from app.analyzer.swimlane_detector import detect_swimlanes_and_chapters
        return await detect_swimlanes_and_chapters(self.llm, root_task, event_model)

    async def _generate_wireframes_and_dataflow(self, root_task, event_model: Dict[str, Any]) -> Dict[str, Any]:
        """Generate wireframes and data flow using the wireframe_generator module."""
        from app.analyzer.wireframe_generator import generate_wireframes_and_dataflow
        return await generate_wireframes_and_dataflow(self.llm, root_task, event_model)

    async def _validate_and_fix_data_flow(self, root_task, event_model: Dict[str, Any]) -> Dict[str, Any]:
        """Validate data flow and use LLM to fix any issues."""
        from app.analyzer.data_flow_validator import DataFlowValidator
        import json

        validator = DataFlowValidator()

        # Try validation and fixes up to 3 times
        max_retries = 3
        for retry in range(max_retries):
            is_valid, issues = validator.validate(event_model)

            errors = [issue for issue in issues if issue.severity == 'error']
            warnings = [issue for issue in issues if issue.severity == 'warning']

            if is_valid:
                print(f"[DataFlowValidator] Validation passed with {len(warnings)} warnings")
                if warnings:
                    for warning in warnings[:5]:  # Show first 5 warnings
                        print(f"[DataFlowValidator] Warning: {warning.message}")
                break

            if retry == max_retries - 1:
                print(f"[DataFlowValidator] Validation failed after {max_retries} attempts, proceeding with {len(errors)} errors")
                # Store validation errors in metadata for frontend display
                event_model['data_flow_validation'] = {
                    'valid': False,
                    'errors': [
                        {
                            'severity': e.severity,
                            'category': e.category,
                            'message': e.message,
                            'details': e.details,
                            'suggestions': e.suggestions
                        }
                        for e in errors
                    ],
                    'warnings': [
                        {
                            'severity': w.severity,
                            'category': w.category,
                            'message': w.message,
                            'details': w.details,
                            'suggestions': w.suggestions
                        }
                        for w in warnings
                    ]
                }
                break

            # Try to fix errors
            print(f"[DataFlowValidator] Found {len(errors)} errors, attempting to fix (attempt {retry + 1}/{max_retries})")
            event_model = await self._fix_data_flow_errors(event_model, errors)

        return event_model

    async def _fix_data_flow_errors(self, event_model: Dict[str, Any], errors: List) -> Dict[str, Any]:
        """Use LLM to fix data flow validation errors."""
        import json

        # Build error descriptions
        error_descriptions = []
        for error in errors[:10]:  # Limit to first 10 errors to avoid token overflow
            error_descriptions.append(f"\nERROR: {error.message}")
            error_descriptions.append(f"Category: {error.category}")
            error_descriptions.append(f"Details: {json.dumps(error.details, indent=2)}")
            error_descriptions.append(f"Suggestions:")
            for suggestion in error.suggestions:
                error_descriptions.append(f"  - {suggestion}")

        errors_text = "\n".join(error_descriptions)

        # Convert event model to serializable format
        serializable_model = {
            "events": [
                {
                    "name": e.name if hasattr(e, 'name') else e.get('name'),
                    "event_type": e.event_type.value if hasattr(e, 'event_type') else e.get('event_type'),
                    "description": e.description if hasattr(e, 'description') else e.get('description'),
                    "actor": e.actor if hasattr(e, 'actor') else e.get('actor'),
                    "affected_entity": e.affected_entity if hasattr(e, 'affected_entity') else e.get('affected_entity'),
                    "payload": e.metadata.get('payload', []) if hasattr(e, 'metadata') else e.get('payload', [])
                }
                for e in event_model.get('events', [])
            ],
            "commands": event_model.get('commands', []),
            "read_models": event_model.get('read_models', []),
            "wireframes": event_model.get('wireframes', [])
        }

        prompt = f"""You are fixing DATA FLOW VALIDATION errors in an event model.

DATA FLOW VALIDATION ensures that all data has a proper source throughout the entire flow:
UI → Command → Event → Read Model → UI

CURRENT EVENT MODEL (with errors):
{json.dumps(serializable_model, indent=2)[:15000]}

DATA FLOW ERRORS THAT MUST BE FIXED:
{errors_text}

YOUR TASK:
Return the COMPLETE corrected event model with ALL sections.
For each error, apply ONE of the suggested fixes.

CRITICAL - You MUST preserve the schema structure:
- Commands MUST have 'parameters' array with 'name', 'type', 'description', 'required', and 'source' objects
- Events MUST have 'payload' array with 'name', 'type', 'description', and 'source' objects
- Read Models MUST have 'fields' array with 'name', 'type', 'description', and 'source' objects with 'events' array
- Sources MUST have 'type' and appropriate details ('from', 'details', 'events')

Example command parameter with source:
{{"name": "productId", "type": "string", "description": "Product to add", "required": true, "source": {{"type": "ui_input", "details": "productSelector component"}}}}

Example event payload field with source:
{{"name": "productId", "type": "string", "description": "Product added", "source": {{"type": "command_parameter", "from": "AddItem.productId"}}}}

Example read model field with source:
{{"name": "items", "type": "array", "description": "Cart items", "source": {{"type": "event_field", "from": "ItemAdded.items", "events": ["ItemAdded", "ItemRemoved"]}}}}

Return ONLY valid JSON with the complete event model (events, commands, read_models, wireframes)."""

        try:
            response = await self.llm.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=64000,
                temperature=0.2
            )

            # Extract JSON
            import re
            if isinstance(response, dict) and "choices" in response:
                content = response["choices"][0]["message"]["content"]
            else:
                print("[DataFlowValidator] Unexpected response format")
                return event_model

            data = None

            # Try direct parse
            try:
                data = json.loads(content.strip())
                print("[DataFlowValidator] Successfully parsed fix JSON directly")
            except json.JSONDecodeError:
                pass

            # Try code block extraction
            if data is None:
                code_block_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', content)
                if code_block_match:
                    try:
                        data = json.loads(code_block_match.group(1))
                        print("[DataFlowValidator] Successfully extracted fix JSON from code block")
                    except json.JSONDecodeError:
                        pass

            # Try brace matching
            if data is None:
                start_idx = content.find('{')
                if start_idx != -1:
                    brace_count = 0
                    in_string = False
                    escape = False

                    for i in range(start_idx, len(content)):
                        char = content[i]

                        if escape:
                            escape = False
                            continue

                        if char == '\\':
                            escape = True
                            continue

                        if char == '"' and not escape:
                            in_string = not in_string
                            continue

                        if not in_string:
                            if char == '{':
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    json_str = content[start_idx:i+1]
                                    try:
                                        data = json.loads(json_str)
                                        print("[DataFlowValidator] Successfully extracted fix JSON using brace matching")
                                        break
                                    except json.JSONDecodeError:
                                        pass

            if data:
                # Parse events back to DomainEvent objects
                data["events"] = self._parse_events(data.get("events", []))

                # Preserve other parts of event model that weren't in the fix
                for key in ['chapters', 'swimlanes', 'data_flow', 'user_interactions', 'automations']:
                    if key in event_model and key not in data:
                        data[key] = event_model[key]

                print(f"[DataFlowValidator] Applied fixes to event model")
                return data
            else:
                print("[DataFlowValidator] Failed to parse fix response, keeping original")
                return event_model

        except Exception as e:
            print(f"[DataFlowValidator] Error fixing data flow: {e}")
            return event_model

