"""
Domain Glossary for FastAPI SaaS Boilerplate

### User
An individual with login credentials, email address, and authentication status. A User can create Organizations and be a member of multiple Organizations.

### Organization  
A business entity with its own plan tier, members, invitations, and billing. Organizations have hierarchy through MemberRoles (owner, admin, member, viewer).

### Member
The relationship between a User and an Organization, with permissions defined by MemberRole. Membership establishes access control boundaries within an Organization.

### MemberRole
Enumeration of organizational roles with increasing privilege:
- OWNER: Full control, can transfer ownership
- ADMIN: Can manage all members except other owners
- MEMBER: Can access resources but not manage team
- VIEWER: Read-only access to organization resources

### PlanTier
Pricing tiers with assigned limits:
- FREE: Limited to 5 members, 3 projects, basic features
- PRO: 50 members, unlimited projects, priority support
- ENTERPRISE: Unlimited members, security features enabled

### Resource
Something within an Organization that can be accessed (projects, audit logs, billing, etc.)

### Permission
The capability granted to a MemberRole to perform an action on a Resource

### Ownership
The relationship between User and Organization where the User has sole administrative control

## Key Constraints

- Role-based access control uses a numeric hierarchy: VIEWER(0) < MEMBER(1) < ADMIN(2) < OWNER(3)
- Plan limits enforce quotas on organizational resources
- Permission checks verify both membership and role hierarchy before allowing actions
- All organizational operations go through Member validation first
"""