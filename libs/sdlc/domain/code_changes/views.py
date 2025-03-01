from dataclasses import dataclass, field
from typing import Dict, List
from uuid import UUID

from ..events import Event
from .events import CodeChangeProposed, CodeChangeReviewed, CodeChangeImplemented


@dataclass
class CodeChangesView:
    project_id: UUID
    changes: Dict[UUID, Dict] = field(default_factory=dict)
    pending_changes: Dict[UUID, Dict] = field(default_factory=dict)
    implemented_changes: Dict[UUID, Dict] = field(default_factory=dict)
    changes_by_file: Dict[str, List[UUID]] = field(default_factory=dict)

    def apply_event(self, event: Event) -> None:
        """Update view based on events"""
        if isinstance(event, CodeChangeProposed):
            change_data = {
                'id': event.change_id,
                'files': event.files,
                'description': event.description,
                'reasoning': event.reasoning,
                'proposed_by': event.proposed_by,
                'status': 'proposed',
                'timestamp': event.timestamp
            }
            self.changes[event.change_id] = change_data
            self.pending_changes[event.change_id] = change_data
            
            # Update changes by file index
            for file in event.files:
                if file not in self.changes_by_file:
                    self.changes_by_file[file] = []
                self.changes_by_file[file].append(event.change_id)

        elif isinstance(event, CodeChangeReviewed):
            if event.change_id in self.changes:
                self.changes[event.change_id].update({
                    'status': event.status,
                    'comments': event.comments,
                    'suggested_changes': event.suggested_changes,
                    'reviewed_by': event.reviewed_by,
                    'review_timestamp': event.timestamp
                })
                if event.change_id in self.pending_changes:
                    self.pending_changes[event.change_id].update({
                        'status': event.status,
                        'comments': event.comments,
                        'suggested_changes': event.suggested_changes,
                        'reviewed_by': event.reviewed_by,
                        'review_timestamp': event.timestamp
                    })

        elif isinstance(event, CodeChangeImplemented):
            if event.change_id in self.changes:
                self.changes[event.change_id].update({
                    'status': 'implemented',
                    'implemented_by': event.implemented_by,
                    'implementation_timestamp': event.timestamp
                })
                if event.change_id in self.pending_changes:
                    change_data = self.pending_changes.pop(event.change_id)
                    change_data.update({
                        'status': 'implemented',
                        'implemented_by': event.implemented_by,
                        'implementation_timestamp': event.timestamp
                    })
                    self.implemented_changes[event.change_id] = change_data 