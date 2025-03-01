"""
Organization repository for tests
"""
from uuid import uuid4

class EventStoreOrganizationRepository:
    """Repository for organizations based on event store"""
    
    def __init__(self, event_store):
        self.event_store = event_store
    
    def get_by_id(self, organization_id):
        """Get organization by ID"""
        # Stub implementation for tests
        return {'id': organization_id, 'name': 'Test Organization'}
    
    def get_all(self):
        """Get all organizations"""
        # Stub implementation
        return [{'id': uuid4(), 'name': 'Test Organization'}]
    
    def save(self, organization):
        """Save organization"""
        # Stub implementation
        pass 