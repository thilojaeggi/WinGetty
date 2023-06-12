import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from distutils.version import LooseVersion


db = SQLAlchemy()
basedir = os.path.abspath(os.path.dirname(__file__))

def sort_versions(versions):
    return sorted(versions, key=lambda x: LooseVersion(x.version_code), reverse=True)


def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] =\
            'sqlite:///' + os.path.join(basedir, 'database.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    from app.ui_routes import ui
    from app.api_routes import api
    app.register_blueprint(ui)
    app.register_blueprint(api)
    
    

    app.jinja_env.filters['sort_versions'] = sort_versions

    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow()}

    with app.app_context():
        db.create_all()
    return app