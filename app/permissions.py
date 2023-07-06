import itertools
from app.models import Permission, Role
from app import db

def create_all():
    create_default_roles()
    create_permissions()

def create_default_roles():
    roles = [
        Role(name='admin'),
        Role(name='user'),
        Role(name='viewer')
    ]
    db.session.add_all(roles)
    db.session.commit()

def create_permissions():
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

    # Combine all permissions to one big list
    all_permissions = (
        package_permissions +
        version_permissions +
        installer_permissions +
        installer_switch_permissions +
        role_permissions +
        permission_permissions +
        user_permissions +
        own_user_permissions
    )

    # Create all permissions
    permissions = [Permission(name=permission) for permission in all_permissions]
    db.session.add_all(permissions)
    db.session.commit()

    admin_role = Role.query.filter_by(name='admin').first()
    user_role = Role.query.filter_by(name='user').first()
    viewer_role = Role.query.filter_by(name='viewer').first()

    # For each permission assign to the correct role
    admin_role.permissions = Permission.query.all()

    user_role_permissions = Permission.query.filter(
        Permission.name.in_(all_permissions),
        ~Permission.name.in_(role_permissions + permission_permissions + user_permissions)
    ).all()
    user_role.permissions = user_role_permissions
    # All permissions that start with 'view:' are allowed for the viewer role except those in role_permissions and permission_permissions and user_permissions
    # All permissions that start with 'view:' are allowed for the viewer role except those in role_permissions and permission_permissions and user_permissions
    viewer_role_permissions = Permission.query.filter(
        Permission.name.in_(all_permissions),
        Permission.name.like('view:%'),
        ~Permission.name.in_(role_permissions + permission_permissions + user_permissions)
    ).all()
    viewer_role.permissions = viewer_role_permissions

    db.session.commit()


