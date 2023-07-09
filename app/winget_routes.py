
import os
from flask import Blueprint, jsonify, render_template, request, redirect, url_for, current_app, send_from_directory, flash
from flask_login import login_required
from werkzeug.http import parse_range_header
from werkzeug.utils import secure_filename

from app.utils import create_installer, debugPrint, save_file, basedir
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
    # Output all post request data
    request_data = request.get_json()
    debugPrint(request_data)

    maximum_results = request_data.get('MaximumResults')
    fetch_all_manifests = request_data.get('FetchAllManifests')
        
    query = request_data.get('Query')
    if query is not None:
        keyword = query.get('KeyWord')
        match_type = query.get('MatchType')

    inclusions = request_data.get('Inclusions')
    if inclusions is not None:
        package_match_field = inclusions[0].get('PackageMatchField')
        request_match = inclusions[0].get('RequestMatch')
        if query is None:
            keyword = request_match.get('KeyWord')
            match_type = request_match.get('MatchType')

    filters = request_data.get('Filters')
    if filters is not None:
        package_match_field_filter = filters[0].get('PackageMatchField')
        request_match_filter = filters[0].get('RequestMatch')
        keyword_filter = request_match_filter.get('KeyWord')
        match_type_filter = request_match_filter.get('MatchType')


    # Get packages by keyword and match type (exact or partial)
    packages = []
    if keyword is not None and match_type is not None:
        if match_type == "Exact":
            packages_query = Package.query.filter_by(identifier=keyword)
            # Also search for package name if no package identifier is found
            if packages_query.first() is None:
                debugPrint("No package found with identifier, searching for package name")
                packages_query = Package.query.filter_by(name=keyword)
        elif match_type == "Partial" or match_type == "Substring":
            packages_query = Package.query.filter(Package.name.ilike(f'%{keyword}%'))
            # Also search for package identifier if no package name is found
            if packages_query.first() is None:
                debugPrint("No package found with name, searching for package identifier")
                packages_query = Package.query.filter(Package.identifier.ilike(f'%{keyword}%'))
        else:
            return jsonify({}), 204

        if maximum_results is not None:
            packages_query = packages_query.limit(maximum_results)
        
        packages = packages_query.all()

    if not packages:
        return jsonify({}), 204


    output_data = []
    for package in packages:
        # If a package is added to the output without any version associated with it WinGet will error out
        if len(package.versions) > 0:
            output_data.append(package.generate_output_manifest_search())
    
    output = {"Data": output_data}
    debugPrint(output)
    return jsonify(output)

