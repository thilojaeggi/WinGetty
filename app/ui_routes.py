from flask_login import login_required
from app import db, htmx
from flask import Blueprint, jsonify, render_template, request, redirect, url_for
from app.models import Package, PackageVersion, Installer, Role, User
from app.utils import debugPrint
from app.decorators import permission_required
import os
ui = Blueprint('ui', __name__)

@ui.route('/')
def index():
    return redirect(url_for('ui.packages'))


@ui.route('/packages')
@login_required
@permission_required('view:package')
def packages():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q')
    per_page = 10

    if search_query:
        packages = Package.query.filter(
            db.or_(
                Package.name.ilike(f'%{search_query}%'),
                Package.identifier.ilike(f'%{search_query}%')
            )
        )
    else:
        packages = Package.query

    total_pages = packages.paginate(page=1, per_page=per_page).pages
    if page < 1 or (total_pages > 0 and page > total_pages):
        return redirect(url_for('ui.packages', q=search_query, page=total_pages))

    packages_paginated = packages.paginate(page=page, per_page=per_page)
    available_pages = packages_paginated.pages
    packages = packages_paginated.items

    # Get total item count available
    package_count = packages_paginated.total
    
    debugPrint(f'Page: {page}')
    debugPrint(f'Available pages: {available_pages}')


    if htmx:
        return render_template('packages_rows.j2', packages=packages)
    
    

    return render_template('packages.j2', packages=packages, page=page, pages=available_pages, package_count=package_count)


@ui.route('/setup')
@login_required
def setup():
    return render_template('setup.j2')


@ui.route('/users')
@login_required
@permission_required('view:own_user')
def users():
    users = User.query.all()
    roles = Role.query.all()
    return render_template('users.j2', users=users, roles=roles)


@ui.route('/package/<identifier>', methods=['GET'])
@login_required
@permission_required('view:package')
def package(identifier):
    package = Package.query.filter_by(identifier=identifier).first()

        

    

    return render_template('package.j2', package=package)
