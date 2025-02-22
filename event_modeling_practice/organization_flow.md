# Organization Management Event Flow

## Events
1. OrganizationCreated
   - organizationId: UUID
   - name: String
   - createdAt: DateTime
   - createdBy: UUID

2. OrganizationNameUpdated
   - organizationId: UUID
   - newName: String
   - updatedAt: DateTime
   - updatedBy: UUID

3. OrganizationMemberAdded
   - organizationId: UUID
   - userId: UUID
   - role: String
   - addedAt: DateTime
   - addedBy: UUID

4. OrganizationMemberRemoved
   - organizationId: UUID
   - userId: UUID
   - removedAt: DateTime
   - removedBy: UUID

## Commands
1. CreateOrganization
   - name: String
   - createdBy: UUID

2. UpdateOrganizationName
   - organizationId: UUID
   - newName: String
   - updatedBy: UUID

3. AddOrganizationMember
   - organizationId: UUID
   - userId: UUID
   - role: String
   - addedBy: UUID

4. RemoveOrganizationMember
   - organizationId: UUID
   - userId: UUID
   - removedBy: UUID

## Views/Projections
1. OrganizationDetailsView
   - organizationId: UUID
   - name: String
   - createdAt: DateTime
   - updatedAt: DateTime
   - memberCount: Integer

2. OrganizationMembersView
   - organizationId: UUID
   - members: List<Member>
     - userId: UUID
     - role: String
     - addedAt: DateTime

## Workflows
1. Create New Organization
   ```
   Command: CreateOrganization
   Event: OrganizationCreated
   View: Update OrganizationDetailsView
   ```

2. Update Organization Name
   ```
   Command: UpdateOrganizationName
   Event: OrganizationNameUpdated
   View: Update OrganizationDetailsView
   ```

3. Add Member to Organization
   ```
   Command: AddOrganizationMember
   Event: OrganizationMemberAdded
   Views: 
   - Update OrganizationDetailsView (increment memberCount)
   - Update OrganizationMembersView (add member)
   ```

4. Remove Member from Organization
   ```
   Command: RemoveOrganizationMember
   Event: OrganizationMemberRemoved
   Views:
   - Update OrganizationDetailsView (decrement memberCount)
   - Update OrganizationMembersView (remove member)
   ```

## Business Rules
1. Organization names must be unique
2. Only organization admins can add/remove members
3. The last admin cannot be removed
4. A user cannot be added twice to the same organization 