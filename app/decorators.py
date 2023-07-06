from functools import wraps
from flask import abort, flash, redirect, request
from flask_login import current_user

def permission_required(permission):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Check if the current user has the required role
            if not current_user.is_authenticated:
                abort(401)  # Return an unauthorized status code if the user is not authenticated

            user_role = current_user.role  # Replace 'role' with the actual attribute representing the user's role
            # print all permissions for the user's role
            print(f'User role: {user_role.name}')
            print(f'User permissions: {[permission.name for permission in user_role.permissions]}')
            # Check if the user's role has the required permission
            if not user_role.has_permission(permission):
                # flash error message
                flash("You\\'re missing permissions to access this resource.", 'error')
                return redirect(request.referrer)
            return func(*args, **kwargs)
        return wrapper
    return decorator
