from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional
from uuid import UUID

from sdlc.domain.events import Event, EventMetadata


class TestEvent(Event):
    """Test event for BDD scenarios"""
    def __init__(self, event_id: UUID, timestamp: datetime, metadata: Optional[EventMetadata],
                 aggregate_id: str, data: dict):
        super().__init__(event_id, timestamp, metadata)
        self._aggregate_id = aggregate_id
        self.data = data

    @property
    def aggregate_id(self) -> str:
        """Get the aggregate ID for this event"""
        return self._aggregate_id 