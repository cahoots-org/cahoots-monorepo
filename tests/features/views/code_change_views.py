"""
Code change view classes for tests
"""
from uuid import UUID
from typing import Dict, List

class CodeChangesView:
    """View for code changes in a project"""
    def __init__(self, project_id=None):
        self.project_id = project_id
        self.changes = {}
        self.pending_changes = {}
        self.implemented_changes = {}
        self.changes_by_file = {}

    def apply_event(self, event):
        """Apply an event to update this view"""
        # Import event classes here to avoid circular imports
        from ..test_imports import CodeChangeProposed, CodeChangeReviewed, CodeChangeImplemented
        
        # Handle code change proposed
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

        # Handle code change reviewed
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

        # Handle code change implemented
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