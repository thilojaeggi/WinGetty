
from operator import or_
import os
from flask import Blueprint, jsonify, render_template, request, redirect, url_for, current_app, send_from_directory, flash
from flask_login import login_required
from sqlalchemy import and_
from werkzeug.http import parse_range_header
from werkzeug.utils import secure_filename

from app.utils import create_installer, save_file, basedir
from app import db
from app.models import InstallerSwitch, Package, PackageVersion, Installer, User


winget = Blueprint('winget', __name__)

@winget.route('/')
def index():
    return "WinGet API is running, see documentation for more information", 200

@winget.route('/information')
def information():
    return jsonify({"Data": {"SourceIdentifier": current_app.config["REPO_NAME"], "ServerSupportedVersions": ["1.4.0", "1.5.0"]}})
    
@winget.route('/packageManifests/<name>', methods=['GET'])
def get_package_manifest(name):
    package = Package.query.filter_by(identifier=name).first()
    if package is None:
        return jsonify({}), 204
    return jsonify(package.generate_output())



@winget.route('/manifestSearch', methods=['POST'])
def manifestSearch():
    request_data = request.get_json()
    current_app.logger.info(f"Received manifestSearch request: {request_data}")

    maximum_results = request_data.get('MaximumResults', 50)
    query = request_data.get('Query', {})
    filters = request_data.get('Filters', [])
    inclusions = request_data.get('Inclusions', [])

    # Initialize the base query
    packages_query = Package.query

    # If there is a keyword and match type from Query, apply them first
    if query:
        keyword = query.get('KeyWord')
        match_type = query.get('MatchType')
        like_expression = f'%{keyword}%' if match_type != "Exact" else keyword
        packages_query = packages_query.filter(
            or_(
                Package.name.ilike(like_expression),
                Package.identifier.ilike(like_expression)
            )
        )

    combined_filters = filters + inclusions


    # Apply inclusions to the query
    inclusion_filters = []
    for inclusion in combined_filters:
        package_match_field = inclusion.get('PackageMatchField')
        request_match = inclusion.get('RequestMatch')
        
        if not all([package_match_field, request_match]):
            continue  # Skip if filter is incomplete

        # Map the PackageMatchField to the database field
        db_field_map = {
            'PackageName': 'name',
            'PackageIdentifier': 'identifier',
            'PackageFamilyName': 'identifier',
            'ProductCode': 'identifier',  # Not implemented in the database yet
            'Moniker': 'name'            # Not implemented in the database yet
        }

        db_field = db_field_map.get(package_match_field)
        if not db_field:
            current_app.logger.error(f"Unsupported PackageMatchField: {package_match_field}, skipping.")
            continue

        keyword_filter = request_match.get('KeyWord')
        match_type_filter = request_match.get('MatchType')
        filter_expression = f'%{keyword_filter}%' if match_type_filter != "Exact" else keyword_filter

        if match_type_filter == "Exact":
            inclusion_filters.append(getattr(Package, db_field) == keyword_filter)
        elif match_type_filter in ["Partial", "Substring", "CaseInsensitive"]:
            inclusion_filters.append(getattr(Package, db_field).ilike(filter_expression))
        else:
            current_app.logger.error("Invalid match type in filters provided.")
            return jsonify({"error": "Invalid match type in filters"}), 400

    if inclusion_filters:
        packages_query = packages_query.filter(and_(*inclusion_filters))

    # Apply maximum_results limit
    packages_query = packages_query.limit(maximum_results)
    packages = packages_query.all()

    if not packages:
        current_app.logger.info("No packages found.")
        return jsonify({}), 204

    # Generate output data and check if there are any installers available
    output_data = [
        package.generate_output_manifest_search()
        for package in packages
        if package.versions and any(version.installers for version in package.versions)
    ]

    if not output_data:
        current_app.logger.info("Found packages, but no installers available.")
        return jsonify({}), 204

    current_app.logger.info(f"Returning {len(output_data)} packages.")

    return jsonify({"Data": output_data})