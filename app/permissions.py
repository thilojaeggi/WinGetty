from app.models import Permission, Role, User
from app import db
from sqlalchemy.exc import IntegrityError

def create_all():
    create_default_roles()
    create_permissions()

def create_default_roles():
    # Create the default roles if they don't exist
    admin_role = Role.query.filter_by(name='admin').first()
    if not admin_role:
        admin_role = Role(name='admin')
        db.session.add(admin_role)

    user_role = Role.query.filter_by(name='user').first()
    if not user_role:
        user_role = Role(name='user')
        db.session.add(user_role)

    viewer_role = Role.query.filter_by(name='viewer').first()
    if not viewer_role:
        viewer_role = Role(name='viewer')
        db.session.add(viewer_role)
    
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
    for permission in all_permissions:
        existing_permission = Permission.query.filter_by(name=permission).first()
        if not existing_permission:
            print(f'Creating permission: {permission}')
            new_permission = Permission(name=permission)
            try:
                db.session.add(new_permission)
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                print(f"Permission {permission} already exists.")

    admin_role = Role.query.filter_by(name='admin').first()
    user_role = Role.query.filter_by(name='user').first()
    viewer_role = Role.query.filter_by(name='viewer').first()

    # Assign the permissions to the roles if they are not already assigned to the role
    admin_role_permissions = [
    permission for permission in Permission.query.filter(
        Permission.name.in_(all_permissions)
    ) if permission not in admin_role.permissions
    ]
    admin_role.permissions.extend(admin_role_permissions)

    user_role_permissions = [
        permission for permission in Permission.query.filter(
        Permission.name.in_(all_permissions),
        ~Permission.name.in_(role_permissions + permission_permissions + user_permissions)
        ) if permission not in user_role.permissions
    ]

    user_role.permissions.extend(user_role_permissions)


    # Assign the permissions to the viewer role if they are not already assigned
    viewer_role_permissions = [
        permission for permission in Permission.query.filter(
            Permission.name.like('view:%'),
            ~Permission.name.in_(role_permissions + permission_permissions + user_permissions)
        ) if permission not in viewer_role.permissions
    ]
    viewer_role.permissions.extend(viewer_role_permissions)

    # if no user with the admin role exists, assign the admin role to the first user
    if not User.query.filter_by(role=admin_role).first():
        first_user = User.query.first()
        if first_user:
            first_user.role = admin_role
    # all other users get the viewer role
    for user in User.query.filter_by(role=None):
        user.role = viewer_role

    db.session.commit()


