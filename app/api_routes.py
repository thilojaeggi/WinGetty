import os
from flask import Blueprint, jsonify, render_template, request, redirect, url_for, current_app, send_from_directory, flash
from app.utils import calculate_sha256, debugPrint, save_file, basedir
from app import db
from app.models import Package, PackageVersion, Installer
from werkzeug.http import parse_range_header

api = Blueprint('api', __name__)

@api.route('/add_package', methods=['POST'])
def add_package():
    name = request.form['name'].strip()
    identifier = request.form['identifier'].strip()
    publisher = request.form['publisher'].strip()
    architecture = request.form['architecture']
    installer_type = request.form['type']
    version = request.form['version'].strip()
    file = request.files['file']
    
    if not all([name, identifier, publisher]) or (file and not all([architecture, installer_type, version])):
        return "Missing required fields", 400

    package = Package(identifier=identifier, name=name, publisher=publisher)
    if file and version:
        debugPrint("File and version found")
        hash = save_file(file, publisher, identifier, version, architecture)
        version_code = PackageVersion(version_code=version, package_locale="en-US", short_description=name,identifier=identifier)
        installer = Installer(architecture=architecture, installer_type=installer_type, file_name=file.filename, installer_sha256=hash, scope="user")        
        version_code.installers.append(installer)
        package.versions.append(version_code)
    db.session.add(package)
    db.session.commit()
    flash('Package added successfully.', 'success')
    return "Package added", 200

@api.route('/package/<identifier>', methods=['POST'])
def update_package(identifier):
    package = Package.query.filter_by(identifier=identifier).first()
    if package is None:
        return "Package not found", 404
    name = request.form['name']
    publisher = request.form['publisher']
    package.name = name
    package.publisher = publisher
    db.session.commit()
    return redirect(request.referrer)

@api.route('/package/<identifier>', methods=['DELETE'])
def delete_package(identifier):
    # Delete package with all versions and installers, lastly delete the identifier folder in packages
    package = Package.query.filter_by(identifier=identifier).first()
    if package is None:
        return "Package not found", 404
    
    for version in package.versions:
        for installer in version.installers:
            os.remove(os.path.join(basedir, 'packages', package.publisher, package.identifier, version.version_code, installer.architecture, installer.file_name))
            db.session.delete(installer)
        db.session.delete(version)
    db.session.delete(package)
    db.session.commit()

    return "", 200


@api.route('/package/<identifier>/add-version', methods=['POST'])
def add_version(identifier):
    version = request.form['version']
    architecture = request.form['architecture']
    installer_type = request.form['type']

    package = Package.query.filter_by(identifier=identifier).first()
    if package is None:
        return "Package not found", 404
    file = request.files['file']
    version_code = PackageVersion(version_code=version, package_locale="en-US", short_description=package.name,identifier=identifier)
    if file and version:
        debugPrint("File and version found")
        hash = save_file(file, package.publisher, identifier, version, architecture)
        if hash is None:
            return "Error saving file", 500
        installer = Installer(architecture=architecture, installer_type=installer_type, file_name=file.filename, installer_sha256=hash, scope="user")        
        version_code.installers.append(installer)

    
    package.versions.append(version_code)
    db.session.commit()

    return redirect(request.referrer)


@api.route('/package/<identifier>/add-installer', methods=['POST'])
def add_installer(identifier):
    architecture = request.form['architecture']
    installer_type = request.form['type']
    version = request.form['version']

    file = request.files['file']
    package = Package.query.filter_by(identifier=identifier).first()
    if package is None:
        return "Package not found", 404
    
    version = PackageVersion.query.filter_by(identifier=identifier, version_code=version).first()
    if version is None:
        return "Version not found", 404

    if file:
        debugPrint("File found")
        hash = save_file(file, package.publisher, package.identifier, version.version_code, architecture)
        if hash is None:
            return "Error saving file", 500
        installer = Installer(architecture=architecture, installer_type=installer_type, file_name=file.filename, installer_sha256=hash, scope="user")        
        version.installers.append(installer)
        db.session.commit()

        return redirect(request.referrer)

@api.route('/package/<identifier>/<version>/<installer>', methods=['DELETE'])
def delete_installer(identifier, version, installer):
    package = Package.query.filter_by(identifier=identifier).first()
    if package is None:
        print("Package not found")
        return "Package not found", 404
    
    version = PackageVersion.query.filter_by(identifier=identifier, version_code=version).first()
    if version is None:
        print("Version not found")
        return "Version not found", 404

    installer = Installer.query.filter_by(id=installer).first()
    if installer is None:
        return "Installer not found", 404
    
    os.remove(os.path.join(basedir, 'packages', package.publisher, package.identifier, version.version_code, installer.architecture, installer.file_name))
    db.session.delete(installer)
    db.session.commit()

    return "", 200


@api.route('/information')
def information():
    return jsonify({"Data": {"SourceIdentifier": current_app.config["REPO_NAME"], "ServerSupportedVersions": ["1.4.0"]}})
    
@api.route('/packageManifests/<name>', methods=['GET'])
def get_package_manifest(name):
    package = Package.query.filter_by(identifier=name).first()
    if package is None:
        return jsonify({}), 204
    return jsonify(package.generate_output())



@api.route('/manifestSearch', methods=['POST'])
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

@api.route('/download/<identifier>/<version>/<architecture>')
def download(identifier, version, architecture):
    package = Package.query.filter_by(identifier=identifier).first()
    if package is None:
        return "Package not found", 404
    
    # Get version of package and also match package
    version_code = PackageVersion.query.filter_by(version_code=version, identifier=identifier).first()
    if version_code is None:
        return "Package version not found", 404
    # Get installer of package version and also match architecture and identifier
    installer = Installer.query.filter_by(version_id=version_code.id, architecture=architecture).first()
    if installer is None:
        return "Installer not found", 404

    
    

    installer_path = os.path.join(basedir, 'packages', package.publisher, package.identifier, version_code.version_code, installer.architecture)
    file_path = os.path.join(installer_path, installer.file_name)
    debugPrint("Starting download for package:")
    debugPrint(f"Package name: {package.name}")
    debugPrint(f"Package identifier: {package.identifier}")
    debugPrint(f"Package version: {version_code.version_code}")
    debugPrint(f"Architecture: {installer.architecture}")
    debugPrint(f"Installer file name: {installer.file_name}")
    debugPrint(f"Installer SHA256: {installer.installer_sha256}")
    debugPrint(f"Download URL: {installer_path}")


    # Check if the Range header is present
    range_header = request.headers.get('Range')

    is_partial = range_header is not None
    if is_partial:
        request.range = parse_range_header(range_header)
        if request.range is None:
            return "Invalid range header", 400

    # Only add to download_count for a whole file download not part of it (winget uses range)
    if (is_partial and range_header and range_header == "bytes=0-1") or not is_partial:
        package.download_count += 1
        db.session.commit()

    return send_from_directory(installer_path, installer.file_name, as_attachment=True)