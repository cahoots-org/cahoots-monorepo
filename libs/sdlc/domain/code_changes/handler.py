from datetime import datetime
from typing import List
from uuid import UUID, uuid4

from ..events import EventMetadata
from .commands import ImplementCodeChange, ProposeCodeChange, ReviewCodeChange
from .events import CodeChangeImplemented, CodeChangeProposed, CodeChangeReviewed


class CodeChangesHandler:
    """Handler for code changes-related commands"""

    def __init__(self, event_store, view_store):
        self.event_store = event_store
        self.view_store = view_store

    def handle_propose_code_change(self, cmd: ProposeCodeChange) -> List[CodeChangeProposed]:
        """Handle ProposeCodeChange command"""
        change_id = uuid4()

        event = CodeChangeProposed(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(correlation_id=cmd.correlation_id),
            project_id=cmd.project_id,
            change_id=change_id,
            files=cmd.files,
            description=cmd.description,
            reasoning=cmd.reasoning,
            proposed_by=cmd.proposed_by,
        )

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]

    def handle_review_code_change(self, cmd: ReviewCodeChange) -> List[CodeChangeReviewed]:
        """Handle ReviewCodeChange command"""
        # Get events for the project
        events = self.event_store.get_events_for_aggregate(cmd.project_id)
        if not events:
            raise ValueError(f"No project found with id {cmd.project_id}")

        # Find the proposal event for this change
        proposed_event = next(
            (
                e
                for e in events
                if isinstance(e, CodeChangeProposed) and e.change_id == cmd.change_id
            ),
            None,
        )

        if not proposed_event:
            raise ValueError(f"No code change found with id {cmd.change_id}")

        # Check if reviewer is the same as proposer
        if proposed_event.proposed_by == cmd.reviewed_by:
            raise ValueError("Code change cannot be reviewed by the proposer")

        event = CodeChangeReviewed(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(correlation_id=cmd.correlation_id),
            project_id=cmd.project_id,
            change_id=cmd.change_id,
            status=cmd.status,
            comments=cmd.comments,
            suggested_changes=cmd.suggested_changes,
            reviewed_by=cmd.reviewed_by,
        )

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]

    def handle_implement_code_change(self, cmd: ImplementCodeChange) -> List[CodeChangeImplemented]:
        """Handle ImplementCodeChange command"""
        # Get events for the project
        events = self.event_store.get_events_for_aggregate(cmd.project_id)
        if not events:
            raise ValueError(f"No project found with id {cmd.project_id}")

        # Find relevant events for this change
        change_events = [
            e
            for e in events
            if isinstance(e, (CodeChangeProposed, CodeChangeReviewed))
            and getattr(e, "change_id", None) == cmd.change_id
        ]

        if not change_events:
            raise ValueError(f"No code change found with id {cmd.change_id}")

        # Check if change is approved
        review_event = next((e for e in change_events if isinstance(e, CodeChangeReviewed)), None)

        if not review_event or review_event.status != "approved":
            raise ValueError("Code change must be approved before implementation")

        event = CodeChangeImplemented(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            metadata=EventMetadata(correlation_id=cmd.correlation_id),
            project_id=cmd.project_id,
            change_id=cmd.change_id,
            implemented_by=cmd.implemented_by,
        )

        self.event_store.append(event)
        self.view_store.apply_event(event)

        return [event]
