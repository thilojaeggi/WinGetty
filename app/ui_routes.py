from app import db, htmx
from flask import Blueprint, jsonify, render_template, request, redirect, url_for
from app.models import Package, PackageVersion, Installer

ui = Blueprint('ui', __name__)

@ui.route('/')
def index():
    return redirect(url_for('ui.packages'))

@ui.route('/packages')
def packages():
    page = request.args.get('page', 1, type=int)
    packages = Package.query.paginate(page=page, per_page=10)
    available_pages = packages.pages
    packages = packages.items
    if htmx:
        return render_template('packages_rows.j2', packages=packages)
    return render_template('packages.j2', packages=packages, page=page, pages=available_pages)

@ui.route('/setup')
def setup():
    return render_template('setup.j2')

@ui.route('/settings')
def settings():
    return render_template('settings.j2')

@ui.route('/package/<identifier>', methods=['GET'])
def package(identifier):
    package = Package.query.filter_by(identifier=identifier).first()
    return render_template('package.j2', package=package)
