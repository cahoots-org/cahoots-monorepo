"""
Organization view classes for tests
"""

class OrganizationView:
    def __init__(self, organization_id):
        self.organization_id = organization_id

class OrganizationMembersView:
    """View of organization members"""
    def __init__(self, organization_id=None):
        self.organization_id = organization_id
        self.roles = {'admin': [], 'member': [], 'developer': [], 'guest': []}
        self.members = {}
    
    def apply_event(self, event):
        """Apply an event to update this view"""
        # Import event classes here to avoid circular imports
        from ..handlers.organization_handler import OrganizationCreated, OrganizationMemberAdded, OrganizationMemberRemoved, OrganizationMemberRoleChanged
        
        # Handle organization created
        if isinstance(event, OrganizationCreated):
            if event.created_by not in self.members:
                self.members[event.created_by] = {
                    'id': event.created_by,
                    'role': 'admin',
                    'added_at': event.timestamp,
                    'added_by': event.created_by
                }
                if event.created_by not in self.roles['admin']:
                    self.roles['admin'].append(event.created_by)
        
        # Handle member added
        elif isinstance(event, OrganizationMemberAdded):
            if event.user_id not in self.members:
                self.members[event.user_id] = {
                    'id': event.user_id,
                    'role': event.role,
                    'added_at': event.timestamp,
                    'added_by': event.added_by
                }
                
                # Initialize the role list if it doesn't exist
                if event.role not in self.roles:
                    self.roles[event.role] = []
                    
                # Only add to the role list if not already there
                if event.user_id not in self.roles[event.role]:
                    self.roles[event.role].append(event.user_id)
        
        # Handle member removed
        elif isinstance(event, OrganizationMemberRemoved):
            if event.user_id in self.members:
                role = self.members[event.user_id]['role']
                if event.user_id in self.roles[role]:
                    self.roles[role].remove(event.user_id)
                del self.members[event.user_id]
        
        # Handle member role changed
        elif isinstance(event, OrganizationMemberRoleChanged):
            if event.user_id in self.members:
                old_role = self.members[event.user_id]['role']
                if event.user_id in self.roles[old_role]:
                    self.roles[old_role].remove(event.user_id)
                self.members[event.user_id]['role'] = event.new_role
                
                # Initialize the role list if it doesn't exist
                if event.new_role not in self.roles:
                    self.roles[event.new_role] = []
                    
                # Only add to the role list if not already there
                if event.user_id not in self.roles[event.new_role]:
                    self.roles[event.new_role].append(event.user_id)

class OrganizationDetailsView:
    """Detailed view of an organization"""
    def __init__(self, organization_id=None):
        self.organization_id = organization_id
        self.name = ""
        self.description = ""
        self.status = "active"
        self.created_at = None
        self.archived_at = None
        self.member_count = 0
        self.admin_count = 0
    
    def apply_event(self, event):
        """Apply an event to update this view"""
        # Import event classes here to avoid circular imports
        from ..handlers.organization_handler import OrganizationCreated, OrganizationMemberAdded, OrganizationMemberRemoved, OrganizationMemberRoleChanged
        
        # Handle organization created
        if isinstance(event, OrganizationCreated):
            self.name = event.name
            self.description = event.description
            self.created_at = event.timestamp
            self.member_count = 1
            self.admin_count = 1
        
        # Handle member added
        elif isinstance(event, OrganizationMemberAdded):
            self.member_count += 1
            if event.role == 'admin':
                self.admin_count += 1
        
        # Handle member removed
        elif isinstance(event, OrganizationMemberRemoved):
            self.member_count -= 1
            # Would need to check role in a separate view to update admin_count
        
        # Handle member role changed
        elif isinstance(event, OrganizationMemberRoleChanged):
            if event.old_role == 'admin':
                self.admin_count -= 1
            if event.new_role == 'admin':
                self.admin_count += 1

class OrganizationAuditLogView:
    """View of organization audit log"""
    def __init__(self, organization_id=None):
        self.organization_id = organization_id
        self.entries = []  # Initialize entries as an empty list
    
    def apply_event(self, event):
        """Apply an event to update this view"""
        # Import event classes here to avoid circular imports
        from ..handlers.organization_handler import OrganizationCreated, OrganizationMemberAdded, OrganizationMemberRemoved, OrganizationMemberRoleChanged
        
        # Add all events to the audit log
        self.entries.append({
            'event_id': event.event_id,
            'timestamp': event.timestamp,
            'event_type': event.__class__.__name__
        }) 