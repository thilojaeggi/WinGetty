import enum
from app import db


roles_permissions = db.Table(
    "roles_permissions",
    db.Column("role_id", db.Integer, db.ForeignKey("role.id"), primary_key=True),
    db.Column(
        "permission_id", db.Integer, db.ForeignKey("permission.id"), primary_key=True
    ),
    db.Column("resource_id", db.Integer, nullable=True),
)
