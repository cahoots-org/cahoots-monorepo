"""
Code changes handler for tests
"""

from datetime import datetime
from uuid import uuid4

# Import event classes
from ..test_imports import (
    CodeChangeImplemented,
    CodeChangeProposed,
    CodeChangeReviewed,
    EventMetadata,
)

# Import view class
from ..views.code_change_views import CodeChangesView


class CodeChangesHandler:
    """Handler for code changes commands in tests"""

    def __init__(self, event_store, view_store):
        self.event_store = event_store
        self.view_store = view_store

    def handle_propose_code_change(self, cmd):
        """Handle propose code change command"""
        # Create a unique ID for this change
        change_id = uuid4()

        # Create the event
        event = CodeChangeProposed(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(),
            project_id=cmd.project_id,
            change_id=change_id,
            files=cmd.files,
            description=cmd.description,
            reasoning=cmd.reasoning,
            proposed_by=cmd.proposed_by,
        )

        # Store the event
        self.event_store.append(event)

        # Manually update the view
        view = self.view_store.get_view(cmd.project_id, CodeChangesView)
        if view is None:
            view = CodeChangesView(cmd.project_id)

        # Apply the event to update the view
        view.apply_event(event)

        # Save the updated view
        self.view_store.save_view(cmd.project_id, view)

        print(f"Code change proposed: {change_id}")
        print(f"Files affected: {cmd.files}")
        print(f"Proposed by: {cmd.proposed_by}")

        # Return the event
        return [event]

    def handle_review_code_change(self, cmd):
        """Handle review code change command"""
        # Get the view to check current state
        view = self.view_store.get_view(cmd.project_id, CodeChangesView)

        # Validate the change exists
        if cmd.change_id not in view.changes:
            raise ValueError("Code change not found")

        # Check if the reviewer is the same as the proposer (prevent self-review)
        change = view.changes[cmd.change_id]
        if change["proposed_by"] == cmd.reviewed_by:
            raise ValueError("Code change cannot be reviewed by the proposer")

        # Create the event
        event = CodeChangeReviewed(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(),
            project_id=cmd.project_id,
            change_id=cmd.change_id,
            status=cmd.status,
            comments=cmd.comments,
            suggested_changes=cmd.suggested_changes,
            reviewed_by=cmd.reviewed_by,
        )

        # Store the event
        self.event_store.append(event)

        # Apply the event to update the view
        view.apply_event(event)

        # Save the updated view
        self.view_store.save_view(cmd.project_id, view)

        print(f"Code change reviewed: {cmd.change_id}")
        print(f"Status: {cmd.status}")
        print(f"Reviewed by: {cmd.reviewed_by}")

        # Return the event
        return [event]

    def handle_implement_code_change(self, cmd):
        """Handle implement code change command"""
        # Get the view to check current state
        view = self.view_store.get_view(cmd.project_id, CodeChangesView)

        # Validate the change exists
        if cmd.change_id not in view.changes:
            raise ValueError("Code change not found")

        # Check if the change is approved
        change = view.changes[cmd.change_id]
        if change.get("status") != "approved":
            raise ValueError("Only approved changes can be implemented")

        # Create the event
        event = CodeChangeImplemented(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(),
            project_id=cmd.project_id,
            change_id=cmd.change_id,
            implemented_by=cmd.implemented_by,
        )

        # Store the event
        self.event_store.append(event)

        # Apply the event to update the view
        view.apply_event(event)

        # Save the updated view
        self.view_store.save_view(cmd.project_id, view)

        print(f"Code change implemented: {cmd.change_id}")
        print(f"Implemented by: {cmd.implemented_by}")

        # Return the event
        return [event]
