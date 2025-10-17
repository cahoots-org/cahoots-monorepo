"""Tests for Event Model Markdown Generator"""

import pytest
from app.analyzer.event_model_markdown_generator import EventModelMarkdownGenerator
from app.analyzer.event_extractor import DomainEvent, EventType


def test_generate_complete_event_model():
    """Test generating a complete event model with all slice types"""

    # Create test event
    event1 = DomainEvent(
        name="ItemAdded",
        event_type=EventType.USER_ACTION,
        description="User adds item to cart",
        source_task_id="test-1",
        actor="User",
        affected_entity="Cart",
        triggers=[],
        metadata={}
    )

    event2 = DomainEvent(
        name="CartSubmitted",
        event_type=EventType.USER_ACTION,
        description="User submits cart for checkout",
        source_task_id="test-2",
        actor="User",
        affected_entity="Cart",
        triggers=[],
        metadata={}
    )

    analysis = {
        "events": [event1, event2],
        "commands": [
            {
                "name": "AddItem",
                "description": "Add item to shopping cart",
                "input_data": ["productId", "quantity", "price"],
                "triggers_events": ["ItemAdded"]
            },
            {
                "name": "SubmitCart",
                "description": "Submit cart for order processing",
                "input_data": ["cartId"],
                "triggers_events": ["CartSubmitted"]
            }
        ],
        "read_models": [
            {
                "name": "CartItems",
                "description": "Display items currently in cart",
                "data_fields": ["items", "totalPrice", "itemCount"]
            }
        ],
        "user_interactions": [
            {
                "action": "Click 'Add to Cart' button",
                "triggers_command": "AddItem",
                "viewed_read_model": "ProductDetails"
            }
        ],
        "automations": [
            {
                "name": "Publish cart to order system",
                "trigger_event": "CartSubmitted",
                "result_events": ["ExternalCartPublished"]
            }
        ]
    }

    generator = EventModelMarkdownGenerator()
    markdown = generator.generate(analysis, "Shopping Cart System")

    # Verify structure
    assert "# Event Model" in markdown
    assert "Shopping Cart System" in markdown

    # Verify overview table
    assert "## Overview" in markdown
    assert "| Events | 2 |" in markdown
    assert "| Commands | 2 |" in markdown
    assert "| Read Models | 1 |" in markdown

    # Verify State Change slices
    assert "## State Change Slices" in markdown
    assert "### Slice: AddItem" in markdown
    assert "| **Type** | State Change |" in markdown
    assert "| **Command** | `AddItem` |" in markdown
    assert "| **Input Data** | productId, quantity, price |" in markdown
    assert "`ItemAdded`" in markdown

    # Verify State View slices
    assert "## State View Slices" in markdown
    assert "### Slice: CartItems" in markdown
    assert "| **Type** | State View (Query) |" in markdown
    assert "| **Read Model** | `CartItems` |" in markdown

    # Verify Automation slices
    assert "## Automation Slices" in markdown
    assert "### Slice: Publish cart to order system" in markdown
    assert "| **Type** | Automation (Background Process) |" in markdown
    assert "`CartSubmitted`" in markdown

    # Verify Event Catalog
    assert "## Event Catalog" in markdown
    assert "| `ItemAdded` |" in markdown
    assert "| `CartSubmitted` |" in markdown

    # Verify Information Completeness Check section
    assert "## Information Completeness Check" in markdown
    assert "Information Completeness Check" in markdown

    # Verify GWT placeholders
    assert "#### Given/When/Then" in markdown
    assert "| Scenario | Given | When | Then |" in markdown


def test_generate_minimal_event_model():
    """Test generating event model with minimal data"""

    event = DomainEvent(
        name="UserRegistered",
        event_type=EventType.USER_ACTION,
        description="User completes registration",
        source_task_id="test-1",
        actor="User",
        affected_entity="User",
        triggers=[],
        metadata={}
    )

    analysis = {
        "events": [event],
        "commands": [
            {
                "name": "RegisterUser",
                "description": "Create new user account",
                "input_data": ["email", "password"],
                "triggers_events": ["UserRegistered"]
            }
        ],
        "read_models": [],
        "user_interactions": [],
        "automations": []
    }

    generator = EventModelMarkdownGenerator()
    markdown = generator.generate(analysis, "User Management")

    # Verify basic structure
    assert "# Event Model" in markdown
    assert "User Management" in markdown
    assert "## State Change Slices" in markdown
    assert "### Slice: RegisterUser" in markdown

    # Verify no empty sections for missing components
    # State View and Automation sections should not be present if empty
    # (or should be present but empty - implementation dependent)


def test_generate_event_catalog():
    """Test event catalog generation with multiple events"""

    events = [
        DomainEvent(
            name="ItemAdded",
            event_type=EventType.USER_ACTION,
            description="Item added to cart",
            source_task_id="test-1",
            actor="User",
            affected_entity="Cart",
            triggers=[],
            metadata={}
        ),
        DomainEvent(
            name="ItemRemoved",
            event_type=EventType.USER_ACTION,
            description="Item removed from cart",
            source_task_id="test-2",
            actor="User",
            affected_entity="Cart",
            triggers=[],
            metadata={}
        ),
        DomainEvent(
            name="PriceChanged",
            event_type=EventType.SYSTEM_EVENT,
            description="Product price updated",
            source_task_id="test-3",
            actor="System",
            affected_entity="Product",
            triggers=[],
            metadata={}
        )
    ]

    analysis = {
        "events": events,
        "commands": [],
        "read_models": [],
        "user_interactions": [],
        "automations": []
    }

    generator = EventModelMarkdownGenerator()
    markdown = generator.generate(analysis)

    # Verify catalog table
    assert "## Event Catalog" in markdown
    assert "| Event | Type | Actor | Affected Entity | Description |" in markdown
    assert "| `ItemAdded` | user_action | User | Cart |" in markdown
    assert "| `ItemRemoved` | user_action | User | Cart |" in markdown
    assert "| `PriceChanged` | system_event | System | Product |" in markdown


def test_empty_analysis():
    """Test generating markdown from empty analysis"""

    analysis = {
        "events": [],
        "commands": [],
        "read_models": [],
        "user_interactions": [],
        "automations": []
    }

    generator = EventModelMarkdownGenerator()
    markdown = generator.generate(analysis, "Empty System")

    # Should still have basic structure
    assert "# Event Model" in markdown
    assert "Empty System" in markdown
    assert "## Overview" in markdown
    assert "| Events | 0 |" in markdown
    assert "## Information Completeness Check" in markdown
