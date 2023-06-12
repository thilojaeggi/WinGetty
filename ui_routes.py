from app import db
from flask import Blueprint, jsonify, render_template, request, redirect, url_for

from models import Package, PackageVersion, Installer

ui = Blueprint('ui', __name__)

@ui.route('/')
def index():
    return redirect(url_for('ui.packages'))

@ui.route('/packages')
def packages():
    packages = Package.query.all()
    return render_template('packages.j2', packages=packages)

@ui.route('/settings')
def settings():
    return render_template('settings.j2')

@ui.route('/package/<identifier>')
def package(identifier):
    package = Package.query.filter_by(package_identifier=identifier).first()
    return render_template('package.j2', package=package)
