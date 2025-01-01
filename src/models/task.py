# src/models/task.py
from pydantic import BaseModel
from transitions.extensions.asyncio import AsyncMachine
from typing import List, Optional, Dict, Any, ClassVar
import asyncio

class Task(BaseModel):
    # Model fields
    id: str
    title: str
    description: str
    requires_ux: bool = False
    status: str = "pending"
    metadata: Dict[str, Any] = {}
    
    # Allow dynamic fields for state machine
    model_config = {
        "extra": "allow"
    }
    
    # State machine configuration
    states: ClassVar[List[str]] = ['pending', 'in_progress', 'blocked', 'review', 'testing', 'completed', 'failed']
    
    transitions: ClassVar[List[Dict[str, Any]]] = [
        # Basic flow
        { 'trigger': 'start_work', 'source': 'pending', 'dest': 'in_progress' },
        { 'trigger': 'submit_for_review', 'source': 'in_progress', 'dest': 'review' },
        { 'trigger': 'start_testing', 'source': 'review', 'dest': 'testing' },
        { 'trigger': 'mark_complete', 'source': 'testing', 'dest': 'completed' },
        
        # Error handling
        { 'trigger': 'block', 'source': ['pending', 'in_progress', 'review'], 'dest': 'blocked' },
        { 'trigger': 'fail', 'source': ['in_progress', 'review', 'testing'], 'dest': 'failed' },
        
        # Recovery paths
        { 'trigger': 'resume', 'source': 'blocked', 'dest': 'in_progress' },
        { 'trigger': 'retry', 'source': 'failed', 'dest': 'in_progress' },
        
        # Review feedback loop
        { 'trigger': 'request_changes', 'source': 'review', 'dest': 'in_progress' },
        { 'trigger': 'resubmit', 'source': 'in_progress', 'dest': 'review' },
        
        # Testing feedback loop
        { 'trigger': 'fix_test_issues', 'source': 'testing', 'dest': 'in_progress' }
    ]
    
    def __init__(self, **data):
        super().__init__(**data)
        self.machine = AsyncMachine(
            model=self,
            states=self.states,
            transitions=self.transitions,
            initial=self.status,
            auto_transitions=False,
            send_event=True
        )
        
        # Set up state change callbacks
        self.machine.on_enter_in_progress('_log_progress')
        self.machine.on_enter_review('_notify_reviewer')
        self.machine.on_enter_testing('_notify_tester')
        self.machine.on_enter_completed('_update_metrics')
        
    async def _log_progress(self, event: Dict[str, Any]):
        """Log progress updates with metadata."""
        self.metadata['last_progress'] = {
            'timestamp': event.kwargs.get('timestamp'),
            'actor': event.kwargs.get('actor'),
            'details': event.kwargs.get('details', {})
        }
        
    async def _notify_reviewer(self, event: Dict[str, Any]):
        """Notify code reviewer when ready for review."""
        self.metadata['review'] = {
            'requested_at': event.kwargs.get('timestamp'),
            'requested_by': event.kwargs.get('actor'),
            'pr_url': event.kwargs.get('pr_url')
        }
        
    async def _notify_tester(self, event: Dict[str, Any]):
        """Notify tester when ready for testing."""
        self.metadata['testing'] = {
            'started_at': event.kwargs.get('timestamp'),
            'assigned_to': event.kwargs.get('tester'),
            'test_plan': event.kwargs.get('test_plan', {})
        }
        
    async def _update_metrics(self, event: Dict[str, Any]):
        """Update task completion metrics."""
        self.metadata['completion'] = {
            'completed_at': event.kwargs.get('timestamp'),
            'duration': event.kwargs.get('duration'),
            'complexity_score': event.kwargs.get('complexity', 1)
        }
    
    def to_dict(self) -> dict:
        """Convert task to dictionary representation."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "requires_ux": self.requires_ux,
            "status": self.status,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Task':
        """Create task from dictionary representation."""
        return cls(**data)
    
    def get_state_graph(self) -> str:
        """Generate a GraphViz DOT representation of the state machine."""
        return self.machine.get_graph().draw('task_states.png', prog='dot')