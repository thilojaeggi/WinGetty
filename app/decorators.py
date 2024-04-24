from app.models.log import AccessLog
from flask import current_app, jsonify, request, flash, redirect
from flask_login import current_user
from functools import wraps
from app import db, oauth
from flask import abort
from authlib.integrations.flask_client import OAuth

from app.models.setting import Setting

# Decorator to check if the user is authenticated

def permission_required(permission, resource_type=None, resource_id_key=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)  # User is not authenticated

            resource_id = None

            # Retrieve the resource ID if specified
            if resource_id_key:
                resource_id = kwargs.get(resource_id_key)
                print(f"Checking permission for resource ID: {resource_id}")  # Debug output

            user_role = current_user.role

            # Check if the user's role has the required permission, potentially limited to a specific resource
            if resource_id:
                has_perm = user_role.has_permission(permission, resource_id=resource_id)
            else:
                has_perm = user_role.has_permission(permission)

            print(f"Permission check for '{permission}' with resource ID '{resource_id}': {has_perm}")  # Debug output

            if not has_perm:
                if request.content_type == 'application/json':
                    return jsonify({"error": "You're missing permissions to access this resource."}), 403
                flash("You're missing permissions to access this resource.", 'error')
                return redirect(request.referrer)

            # Log access
            access = AccessLog(user_id=current_user.id, ip_address=request.remote_addr, user_agent=request.user_agent.string, action=f"Accessed {request.path} with request method {request.method}")
            db.session.add(access)
            db.session.commit()
            return func(*args, **kwargs)
        return wrapper
    return decorator

def oidc_config_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        oidc_settings = {setting.key: setting.get_value() for setting in Setting.query.filter(Setting.key.in_([
            "OIDC_ENABLED", "OIDC_CLIENT_ID", "OIDC_CLIENT_SECRET", "OIDC_SERVER_METADATA_URL"
        ])).all()}

        if oidc_settings.get("OIDC_ENABLED", False):
            current_app.oidc_provider = oauth.create_client('oidc')  # Ensure this client is recreated on demand
            current_app.oidc_provider.update(
                client_id=oidc_settings["OIDC_CLIENT_ID"],
                client_secret=oidc_settings["OIDC_CLIENT_SECRET"],
                server_metadata_url=oidc_settings["OIDC_SERVER_METADATA_URL"],
                client_kwargs={'scope': 'openid email profile'}
            )
        return f(*args, **kwargs)
    return decorated_function