from flask_login import current_user, login_required
from app import db, htmx
from flask import Blueprint, current_app, jsonify, render_template, request, redirect, url_for
from app.models import DownloadLog, Package, PackageVersion, Installer, Permission, Role, Setting, User
from app.decorators import permission_required
import os
ui = Blueprint('ui', __name__)

@ui.route('/')
def index():
    # If user is logged in, redirect to packages else redirect to login
    if current_user.is_authenticated:
        return redirect(url_for('ui.packages'))
    return redirect(url_for('auth.login'))


@ui.route('/packages')
@login_required
@permission_required('view:package')
def packages():

    return render_template('packages.j2')


@ui.route('/setup')
@login_required
def setup():
    return render_template('setup.j2')

@ui.route('/settings')
@login_required
@permission_required('view:settings')
def settings():
    settings = db.session.query(Setting).all()
    return render_template('settings.j2', settings=settings)


@ui.route('/access')
@login_required
@permission_required('view:own_user')
def users():
    users = User.query.all()
    roles = Role.query.all()
    permissions = Permission.query.all()
    return render_template('access.j2', users=users, roles=roles, permissions=permissions)


@ui.route('/package/<identifier>', methods=['GET'])
@login_required
@permission_required('view:package')
def package(identifier):
    package = Package.query.filter_by(identifier=identifier).first()
    if not package:
        return redirect(url_for('ui.packages'))
    
    return render_template('package.j2', package=package)

@ui.route('/logs')
@login_required
def logs():
    return render_template('logs.j2')
    