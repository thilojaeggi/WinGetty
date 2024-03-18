from flask import current_app
from app.models import Permission, Role, User
from app import db
from sqlalchemy.exc import IntegrityError

def get_or_create(model, **kwargs):
    """Get an instance if it exists, otherwise create and return an instance."""
    instance = model.query.filter_by(**kwargs).first()
    if instance:
        return instance
    else:
        instance = model(**kwargs)
        db.session.add(instance)
        return instance

def create_default_roles():
    """Create default roles."""
    role_names = ['admin', 'user', 'viewer']
    roles = {}
    for role_name in role_names:
        roles[role_name] = get_or_create(Role, name=role_name)
    return roles

def create_permissions():
    """Create permissions and assign them to roles."""
    package_permissions = [
        'view:package',
        'add:package',
        'edit:package',
        'delete:package'
    ]

    version_permissions = [
        'view:version',
        'add:version',
        'edit:version',
        'delete:version'
    ]

    installer_permissions = [
        'view:installer',
        'add:installer',
        'edit:installer',
        'delete:installer'
    ]

    installer_switch_permissions = [
        'view:installer_switch',
        'add:installer_switch',
        'edit:installer_switch',
        'delete:installer_switch'
    ]

    role_permissions = [
        'view:role',
        'add:role',
        'edit:role',
        'delete:role',
    ]

    permission_permissions = [
        'view:permission',
        'add:permission',
        'edit:permission',
        'delete:permission',
    ]

    user_permissions = [
        'view:user',
        'add:user',
        'edit:user',
        'delete:user',
    ]

    own_user_permissions = [
        'view:own_user',
        'edit:own_user',
    ]

    settings_permissions = [
        'view:settings',
        'edit:settings',
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

    for permission_name in permissions:
        permission = get_or_create(Permission, name=permission_name)
        
        # Assign permissions to roles using your filtering logic:
        if permission not in roles['admin'].permissions:
            roles['admin'].permissions.append(permission)
        
        if permission_name not in ['add:role', 'edit:role', 'delete:role', 'add:permission', 'edit:permission', 'delete:permission', 'add:user', 'edit:user', 'delete:user', 'edit:settings'] and \
           permission not in roles['user'].permissions:
            roles['user'].permissions.append(permission)
        
        if permission_name.startswith('view:') and \
           permission_name not in ['view:role', 'view:permission', 'view:user'] and \
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

