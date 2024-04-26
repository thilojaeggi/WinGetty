import logging
from sqlalchemy import exists
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
        """Check if the role has the specified permission, optionally limited to a specific resource or any resource of the type."""
        PermissionAlias = aliased(Permission)
        RolePermissionAlias = aliased(roles_permissions)

        # Query for general permission without resource_id
        general_permission_query = db.session.query(RolePermissionAlias).join(
            PermissionAlias, RolePermissionAlias.c.permission_id == PermissionAlias.id
        ).filter(
            RolePermissionAlias.c.role_id == self.id,
            PermissionAlias.name == name,
            RolePermissionAlias.c.resource_id.is_(None)
        )

        if resource_id is not None:
            # Query for specific permission with resource_id
            specific_permission_query = db.session.query(RolePermissionAlias).join(
                PermissionAlias, RolePermissionAlias.c.permission_id == PermissionAlias.id
            ).filter(
                RolePermissionAlias.c.role_id == self.id,
                PermissionAlias.name == name,
                RolePermissionAlias.c.resource_id == resource_id
            )

            # Check if specific permission exists, otherwise fallback to general permission
            return db.session.query(
                exists(specific_permission_query.statement) | exists(general_permission_query.statement)
            ).scalar()

        return db.session.query(exists(general_permission_query.statement)).scalar()



