from flask import current_app
from app.models import Permission, Role, User
from app import db
from sqlalchemy.exc import IntegrityError

from app.models.access.permission import ResourceType
import logging

logging.basicConfig(level=logging.INFO)
def get_or_create(model, **kwargs):
    """Get an instance if it exists, otherwise create and return an instance."""
    instance = model.query.filter_by(**kwargs).first()
    if instance:
        return instance
    else:
        instance = model(**kwargs)
        db.session.add(instance)
        return instance
    
def get_or_create_permission(permission):
    try:
        instance = Permission.query.filter_by(name=permission.name).first()
        if instance:
            # also update if new value is None
            if permission.resource_type and instance.resource_type != permission.resource_type or permission.resource_type is None:
                instance.resource_type = permission.resource_type
                db.session.commit()
            return instance
        else:
            db.session.add(permission)
            db.session.commit()
            return permission
    except Exception as e:
        current_app.logger.error(f'Error managing permission: {str(e)}')
        db.session.rollback()
        raise



def create_default_roles():
    """Create default roles."""
    role_names = ['admin', 'user', 'viewer']
    roles = {}
    for role_name in role_names:
        roles[role_name] = get_or_create(Role, name=role_name)
    return roles

def create_permissions():
    """Create permissions and assign them to roles."""
    print([e.value for e in ResourceType])
    package_permissions = [
        Permission(name='view:package', resource_type=ResourceType.PACKAGE.value),
        Permission(name='add:package'),
        Permission(name='edit:package', resource_type=ResourceType.PACKAGE.value),
        Permission(name='delete:package', resource_type=ResourceType.PACKAGE.value),
    ]

    version_permissions = [
        Permission(name='view:version', resource_type=ResourceType.VERSION.value),
        Permission(name='add:version', resource_type=ResourceType.VERSION.value),
        Permission(name='edit:version', resource_type=ResourceType.VERSION.value),
        Permission(name='delete:version', resource_type=ResourceType.VERSION.value),

    ]

    installer_permissions = [
        Permission(name='view:installer', resource_type=ResourceType.INSTALLER.value),
        Permission(name='add:installer', resource_type=ResourceType.INSTALLER.value),
        Permission(name='edit:installer', resource_type=ResourceType.INSTALLER.value),
        Permission(name='delete:installer', resource_type=ResourceType.INSTALLER.value),
    ]

    installer_switch_permissions = [
        Permission(name='view:installer_switch', resource_type=ResourceType.INSTALLER.value),
        Permission(name='add:installer_switch', resource_type=ResourceType.INSTALLER.value),
        Permission(name='edit:installer_switch', resource_type=ResourceType.INSTALLER.value),
        Permission(name='delete:installer_switch', resource_type=ResourceType.INSTALLER.value),
    ]

    role_permissions = [
        Permission(name='view:role'),
        Permission(name='add:role'),
        Permission(name='edit:role'),
        Permission(name='delete:role'),
    ]

    permission_permissions = [
        Permission(name='view:permission'),
        Permission(name='add:permission'),
        Permission(name='edit:permission'),
        Permission(name='delete:permission'),
    ]

    user_permissions = [
        Permission(name='view:user', resource_type=ResourceType.USER.value),
        Permission(name='add:user', resource_type=ResourceType.USER.value),
        Permission(name='edit:user', resource_type=ResourceType.USER.value),
        Permission(name='delete:user', resource_type=ResourceType.USER.value),
    ]

    own_user_permissions = [
        Permission(name='view:own_user'),
        Permission(name='edit:own_user'),
        
    ]

    settings_permissions = [
        Permission(name='view:settings'),
        Permission(name='edit:settings'),
    ]

    # Combine all permissions to one big list
    permissions = (
        package_permissions +
        version_permissions +
        installer_permissions +
        installer_switch_permissions +
        role_permissions +
        permission_permissions +
        user_permissions +
        own_user_permissions +
        settings_permissions
    )
    roles = create_default_roles()

    for perm in permissions:
        permission = get_or_create_permission(perm)


        
        # Assign permissions to roles using your filtering logic:
        if permission not in roles['admin'].permissions:
            roles['admin'].permissions.append(permission)
        
        if perm.name not in ['add:role', 'edit:role', 'delete:role', 'add:permission', 'edit:permission', 'delete:permission', 'add:user', 'edit:user', 'delete:user', 'edit:settings'] and \
           permission not in roles['user'].permissions:
            roles['user'].permissions.append(permission)
        
        if perm.name.startswith('view:') and \
           perm not in ['view:role', 'view:permission', 'view:user'] and \
           permission not in roles['viewer'].permissions:
            roles['viewer'].permissions.append(permission)

    # Assign roles to users:
    if not User.query.filter_by(role=roles['admin']).first():
        first_user = User.query.first()
        if first_user:
            first_user.role = roles['admin']
    
    for user in User.query.filter_by(role=None):
        user.role = roles['viewer']

def create_all():
    """Entry function to create roles and permissions."""
    current_app.logger.info('Creating roles and permissions...')
    try:
        create_default_roles()
        create_permissions()
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        current_app.logger.info('Roles and permissions already exist.')

