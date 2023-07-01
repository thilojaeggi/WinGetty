import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_htmx import HTMX
from datetime import datetime
from distutils.version import LooseVersion
from config import settings
from dynaconf import FlaskDynaconf
from flask_login import LoginManager
from flask_bcrypt import Bcrypt




db = SQLAlchemy()
htmx = HTMX()
dynaconf = FlaskDynaconf()
login_manager = LoginManager()
bcrypt = Bcrypt()
migrate = Migrate()


def sort_versions(versions):
    return sorted(versions, key=lambda x: LooseVersion(x.version_code), reverse=True)

def page_not_found(e):
  return render_template('error/404.j2',error=True), 404

def internal_server_error(e):
    return render_template('error/500.j2',error=True), 500

def favicon():
    return url_for('static', filename='img/favicon.ico')

def current_year():
    return {'now': datetime.now}



def create_app():
    app = Flask(__name__)
    
    app.config.from_object(settings)
    app.register_error_handler(404, page_not_found)
    app.register_error_handler(500, internal_server_error)

    db.init_app(app)
    from app.models import User, Package, PackageVersion, Installer, InstallerSwitch
    migrate.init_app(app, db)
    htmx.init_app(app)
    dynaconf.init_app(app)
    bcrypt.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = ''
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from app.ui_routes import ui
    from app.api_routes import api
    from app.auth_routes import auth
    from app.winget_routes import winget

    app.register_blueprint(ui)
    app.register_blueprint(api, url_prefix='/api')
    app.register_blueprint(winget, url_prefix='/wg')
    app.register_blueprint(auth)

    app.jinja_env.filters['sort_versions'] = sort_versions

    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow()}
    
    @app.route('/favicon.ico')
    def favicon():
        return url_for('static', filename='img/favicon.ico')


    return app