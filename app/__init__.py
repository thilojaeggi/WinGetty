import json
import logging
import os
import sys
import semver

from flask_caching import Cache
import requests
from . import constants
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_migrate import Migrate, upgrade
from flask_sqlalchemy import SQLAlchemy
from flask_htmx import HTMX
from datetime import datetime
from packaging.version import parse as parse_version
from authlib.integrations.flask_client import OAuth

from sqlalchemy import MetaData
from config import Config
from dynaconf import FlaskDynaconf
from flask_login import LoginManager
from flask_bcrypt import Bcrypt

ascii_logo = r"""
 _       ___       ______     __  __       
| |     / (_)___  / ____/__  / /_/ /___  __
| | /| / / / __ \/ / __/ _ \/ __/ __/ / / /
| |/ |/ / / / / / /_/ /  __/ /_/ /_/ /_/ / 
|__/|__/_/_/ /_/\____/\___/\__/\__/\__, /  
                                  /____/   
"""

convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}
metadata = MetaData(naming_convention=convention)

oauth = None



db = SQLAlchemy(metadata=metadata)
htmx = HTMX()
dynaconf = FlaskDynaconf()
login_manager = LoginManager()
bcrypt = Bcrypt()
migrate = Migrate()
cache = Cache()
oauth = OAuth()



def sort_versions(versions):
    return sorted(versions, key=lambda x: parse_version(x), reverse=True)

def page_not_found(e):
  return render_template('error/404.j2',error=True), 404

def internal_server_error(e):
    return render_template('error/500.j2',error=True), 500

def favicon():
    return url_for('static', filename='img/favicon.ico')


def remove_none_values(value):
    if isinstance(value, list):
        return [remove_none_values(v) for v in value if v is not None]
    elif isinstance(value, dict):
        return {k: remove_none_values(v) for k, v in value.items() if v is not None}
    else:
        return value





class PrefixLoggerAdapter(logging.LoggerAdapter):
    """ A logger adapter that adds a prefix to every message """
    def process(self, msg: str, kwargs: dict) -> (str, dict):
        return (f'[{self.extra["prefix"]}] ' + msg, kwargs)

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    Config.init_app(app)

    if os.getenv('WINGETTY_SQLALCHEMY_DATABASE_URI'):
        app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('WINGETTY_SQLALCHEMY_DATABASE_URI')

    
    app.register_error_handler(404, page_not_found)
    app.register_error_handler(500, internal_server_error)

    db.init_app(app)
    from app.models import User, Package, PackageVersion, Installer, InstallerSwitch, Permission, Role, Setting
    migrate.init_app(app, db)
    htmx.init_app(app)
    bcrypt.init_app(app)
    app.config['CACHE_TYPE'] = 'SimpleCache'
    cache.init_app(app)
    oauth.init_app(app)

    @app.before_request
    def setup_oidc():
        if Setting.get("OIDC_ENABLED").get_value():
            app.oidc_provider = oauth.register(
                name='oidc',
                client_id=Setting.get("OIDC_CLIENT_ID").get_value(),
                client_secret=Setting.get("OIDC_CLIENT_SECRET").get_value(),
                server_metadata_url=Setting.get("OIDC_SERVER_METADATA_URL").get_value(),
                client_kwargs={'scope': 'openid email profile'},
            )
            app.extensions['oauth'] = oauth

    def get_latest_version():
        # Try to get cached version information first
        version_info = cache.get('version_info')
        if version_info is not None:
            return version_info

        # If not in cache, fetch from GitHub API
        try:
            response = requests.get("https://api.github.com/repos/thilojaeggi/WinGetty/releases/latest")
            response.raise_for_status()
            data = response.json()
            latest_version = data["tag_name"].lstrip("v")
            current_version = current_app.config["VERSION"]

            latest_version = semver.Version.parse(latest_version)
            current_version = semver.Version.parse(current_version)

            # Check if the latest version is newer than the current version using semver
            if semver.Version.compare(latest_version, current_version) > 0:
                version_info = {
                    "current_version": current_version,
                    "latest_version": latest_version,
                    "update_available": True
                }
            else:
                version_info = {
                    "update_available": False
                }

            # Cache the result for 24 hours as to not spam the GitHub API with requests
            cache.set('version_info', version_info, timeout=86400)
            return version_info
        except requests.RequestException as e:
            # In case of an error, provide an error message but report no update available
            return {
                "update_available": False,
                "error": str(e)
            }

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'You must be logged in to access this page.'
    login_manager.login_message_category = 'info'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from app.ui_routes import ui
    from app.api_routes import api
    from app.auth import auth
    from app.winget_routes import winget

    app.register_blueprint(ui)
    app.register_blueprint(api, url_prefix='/api')
    app.register_blueprint(winget, url_prefix='/wg')
    app.register_blueprint(auth)

    app.jinja_env.filters['sort_versions'] = sort_versions
    app.jinja_env.filters['remove_none_values'] = remove_none_values

    logFormatter = logging.Formatter('%(asctime)s - %(message)s')


    is_gunicorn = "gunicorn" in os.environ.get("SERVER_SOFTWARE", "")
    if is_gunicorn:
        gunicorn_logger = logging.getLogger('gunicorn.error')
        app.logger.handlers = gunicorn_logger.handlers
        app.logger.setLevel(gunicorn_logger.level)
        app.logger.info(ascii_logo + "Version: " + app.config['VERSION'])
        app.logger.info("Running in Gunicorn")
    else:
        app.logger.setLevel(logging.INFO)
        app.logger.info(ascii_logo + "Version: " + app.config['VERSION'])
        app.logger.info("Running in Flask")

    app.logger = PrefixLoggerAdapter(app.logger, {"prefix": "WinGetty"})

    app.logger.info("Logger initialized")
    app.add_template_global(constants.installer_switches, name='installer_switches')
    app.add_template_global(constants.simplified_architectures, name='architectures')
    app.add_template_global(constants.installer_types, name='installer_types')
    app.add_template_global(constants.installer_scopes, name='installer_scopes')
    app.add_template_global(constants.simplified_nested_installer_types, name='nested_installer_types')

    def get_settings():
        return {setting.key.upper(): setting.get_value() for setting in Setting.query.all()}
    
    @app.context_processor
    def inject_settings():
        return dict(global_settings=get_settings())
    
    @app.context_processor
    def inject_version():
        return dict(version_info=get_latest_version())

    @app.context_processor
    def inject_now():
        return {'now': datetime.now()}
    
    
    @app.route('/favicon.ico')
    def favicon():
        return url_for('static', filename='img/favicon.ico')
    

    
    # Hacky way to not trigger permissions/settings creation on flask db upgrade or testing as db is not yet initialized
    if 'db' not in sys.argv:
        with app.app_context():
            from app.permissions import create_all
            create_all()
            from app.settings import create_all
            create_all()
        
    return app