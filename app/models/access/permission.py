from dataclasses import dataclass
from app import db
import enum
from .associations import roles_permissions

# Define sqlalchemy enum for resource types
class ResourceType(str, enum.Enum):
    PACKAGE = "package"
    VERSION = "version"
    INSTALLER = "installer"
    INSTALLER_SWITCH = "installer_switch"
    USER = "user"
    ROLE = "role"
    PERMISSION = "permission"




class Permission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)
    resource_type = db.Column(db.Enum(ResourceType), nullable=True)

    # Define relationship with Role through the association table
    roles = db.relationship("Role", secondary=roles_permissions, back_populates="permissions")

    
