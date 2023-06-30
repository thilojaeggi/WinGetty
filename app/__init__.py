import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_htmx import HTMX
from datetime import datetime
from distutils.version import LooseVersion
from config import settings
from dynaconf import FlaskDynaconf
from flask_login import LoginManager

db = SQLAlchemy()
htmx = HTMX()
dynaconf = FlaskDynaconf()
login_manager = LoginManager()

def sort_versions(versions):
    return sorted(versions, key=lambda x: LooseVersion(x.version_code), reverse=True)

def page_not_found(e):
  return render_template('error/404.j2',error=True), 404

def internal_server_error(e):
    return render_template('error/500.j2',error=True), 500



def create_app():
    app = Flask(__name__)
    app.config.from_object(settings)
    app.register_error_handler(404, page_not_found)
    app.register_error_handler(500, internal_server_error)


    db.init_app(app)
    htmx.init_app(app)
    dynaconf.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = ''
    login_manager.init_app(app)

    from app.models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from app.ui_routes import ui
    from app.api_routes import api
    from app.auth_routes import auth
    app.register_blueprint(ui)
    app.register_blueprint(api, url_prefix='/api')
    app.register_blueprint(auth)

    app.jinja_env.filters['sort_versions'] = sort_versions

    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow()}
    
    @app.route('/favicon.ico')
    def favicon():
        return url_for('static', filename='img/favicon.ico')

    with app.app_context():
        db.create_all()
    return app