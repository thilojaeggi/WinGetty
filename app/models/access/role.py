from sqlalchemy.orm import aliased
from app import db
from app.models.access.permission import Permission
from .associations import roles_permissions

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)
    permissions = db.relationship("Permission", secondary=roles_permissions, back_populates="roles")
    users = db.relationship("User", back_populates="role")

    def user_count(self):
        """Return the number of users assigned to this role."""
        return len(self.users)

    def has_permission(self, name, resource_id=None):
        """Check if the role has the specified permission, optionally limited to a specific resource."""
        permission_query = db.session.query(Permission).\
            join(roles_permissions, (roles_permissions.c.permission_id == Permission.id) & (roles_permissions.c.role_id == self.id)).\
            filter(Permission.name == name)
        
        if resource_id is not None:
            # Fetch the resource type associated with this permission
            resource_type = Permission.query.with_entities(Permission.resource_type).filter_by(name=name).scalar()
            if resource_type:
                permission_query = permission_query.filter(roles_permissions.c.resource_type == resource_type,
                                                           roles_permissions.c.resource_id == resource_id)
        else:
            # Check for permission regardless of resource specifics
            permission_query = permission_query.filter(roles_permissions.c.resource_id == None)

        # Check if any permission exists that meets all conditions
        return db.session.query(permission_query.exists()).scalar()
