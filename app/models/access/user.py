from flask_login import UserMixin
from app import db, bcrypt
from app.models.access.permission import Permission
from app.models.access.role import Role
from app.models.access.associations import roles_permissions

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(100), unique=True)
    email = db.Column(db.String(100), unique=True)
    role_id = db.Column(db.Integer, db.ForeignKey("role.id"))
    password = db.Column(db.String(100))
    role = db.relationship("Role", back_populates="users")

    def set_password(self, password):
        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")
        self.password = hashed_password

    def to_dict(self):
            # Query permissions through the association table
            permissions_query = db.session.query(
                Permission.name, 
                Permission.resource_type,
                roles_permissions.c.resource_id
            ).join(
                roles_permissions, 
                roles_permissions.c.permission_id == Permission.id
            ).filter(
                roles_permissions.c.role_id == self.role_id
            )

            # Execute the query and build the permissions list
            permissions = [
                {
                    "name": perm.name,
                    "resource_type": perm.resource_type, 
                    "resource_id": perm.resource_id
                } for perm in permissions_query.all()
            ]

            return {
                "id": self.id,
                "username": self.username,
                "email": self.email,
                "role": self.role.name,
                "permissions": permissions,
            }