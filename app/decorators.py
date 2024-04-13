from functools import wraps
from flask import abort, flash, redirect, request
from flask_login import current_user

from app.models import AccessLog

from app import db

def permission_required(permission):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Check if the current user has the required role
            if not current_user.is_authenticated:
                abort(401)  # Return an unauthorized status code if the user is not authenticated

            user_role = current_user.role

            # Check if the user's role has the required permission
            if not user_role.has_permission(permission):
                # If not html return error code and message
                if request.content_type == 'application/json':
                    print("You\'re missing permissions to access this resource.")
                    return "You\'re missing permissions to access this resource.", 403
                # flash error message
                flash("You\'re missing permissions to access this resource.", 'error')
                return redirect(request.referrer)
            
            # If permission is granted log the page access
            access = AccessLog(user_id=current_user.id, ip_address=request.remote_addr, user_agent=request.user_agent.string, action=f"Accessed {request.path} with request method {request.method}")
            db.session.add(access)
            db.session.commit()
            return func(*args, **kwargs)
        return wrapper
    return decorator
