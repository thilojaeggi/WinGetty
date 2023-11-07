import os
import boto3
from flask import (
    Blueprint, Response, jsonify, render_template, request,
    redirect, stream_with_context, url_for, current_app, send_from_directory, flash
)
from flask_login import login_required
from werkzeug.http import parse_range_header
from werkzeug.utils import secure_filename
import requests
from app import db
from app.decorators import permission_required
from app.forms import AddInstallerForm, AddPackageForm, AddVersionForm
from app.models import InstallerSwitch, Package, PackageVersion, Installer, Permission, Role, User
from app.utils import create_installer, save_file, basedir, delete_installer_util
from app.constants import installer_switches
api = Blueprint('api', __name__)
s3_client = boto3.client('s3')
@api.route('/')
def index():
    return "API is running, see documentation for more information", 200
URL_EXPIRATION_SECONDS = 3600

@api.route('/generate_presigned_url', methods=['POST'])
def generate_presigned_url():
    try:
        # Extract file information from the request
        file_name = request.form.get('file_name')
        file_extension = file_name.rsplit('.', 1)[1]
        content_type = request.form.get('content_type')

        

        # Specify the S3 object key where the file will be uploaded
        publisher = secure_filename(request.form.get('publisher'))
        identifier = secure_filename(request.form.get('identifier'))
        # Get version from db either by id or by name from the request
        version = secure_filename(request.form.get('installer-version'))


        architecture = secure_filename(request.form.get('installer-architecture'))
        scope = request.form.get('installer-installer_scope')  # Add this to the request form
        # Define the S3 object key with the same format as 'scope.file_extension'
        s3_object_key = f'packages/{publisher}/{identifier}/{version}/{architecture}/{scope}.{file_extension}'

        # Generate a pre-signed URL for S3 uploads
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={'Bucket': current_app.config['BUCKET_NAME'], 'Key': s3_object_key, 'ContentType': content_type},
            ExpiresIn=URL_EXPIRATION_SECONDS
        )

        # Return the pre-signed URL and other information in the response
        return jsonify({
            'presigned_url': presigned_url,
            'content_type': content_type,
            'file_name': file_name,
            'file_path': s3_object_key  # Include the S3 object key for reference
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api.route('/add_package', methods=['POST'])
@login_required
@permission_required('add:package')
def add_package():
    form = AddPackageForm(meta={'csrf': False})
    installer_form = form.installer
    
    if not form.validate_on_submit():
        validation_errors = form.errors
        return str("Form validation error"), 500
            
    name = form.name.data
    publisher = secure_filename(form.publisher.data)
    identifier = form.identifier.data
    version = installer_form.version.data
    file = installer_form.file.data
    external_url = installer_form.url.data
    is_aws = installer_form.is_aws.data
    

    package = Package(identifier=identifier, name=name, publisher=publisher)
    if file or external_url and version:
        current_app.logger.info("File and version found")
        installer = create_installer(publisher, identifier, version, installer_form)
        if installer is None:
            return "Error creating installer", 500

        version_code = PackageVersion(version_code=version, package_locale="en-US", short_description=name, identifier=identifier)
        version_code.installers.append(installer)
        package.versions.append(version_code)
        
    try:
        db.session.add(package)
        db.session.commit()
        current_app.logger.info(f"Package {package.identifier} added successfully")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Database error: {e}")
        return "Database error", 500

    flash('Package added successfully.', 'success')
    return "Package added", 200

@api.route('/package/<identifier>', methods=['POST'])
@login_required
@permission_required('edit:package')
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
@login_required
@permission_required('delete:package')
def delete_package(identifier):
    package = Package.query.filter_by(identifier=identifier).first()
    if package is None:
        return "Package not found", 404

    for version in package.versions:
        for installer in version.installers:
            delete_installer_util(package, installer, version)
        db.session.delete(version)
    db.session.delete(package)
    try:
        db.session.commit()
        current_app.logger.info(f"Package {package.identifier} deleted successfully")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Database error: {e}")
        return "Database error", 500

    response = Response()
    redirect_url = url_for('ui.packages')
    response.headers['HX-Redirect'] = redirect_url
    return response


@api.route('/package/<identifier>/add_version', methods=['POST'])
@login_required
@permission_required('add:version')
def add_version(identifier):
    form = AddVersionForm(meta={'csrf': False})

    installer_form = form.installer

    if not form.validate_on_submit():
        validation_errors = form.errors
        current_app.logger.warning(f"Validation errors: {validation_errors}")
        return jsonify(validation_errors), 400
    
    version = installer_form.version.data
    
    

    package = Package.query.filter_by(identifier=identifier).first()
    if package is None:
        return "Package not found", 404
    file = installer_form.file.data
    external_url = installer_form.url.data
    version = PackageVersion(version_code=version, package_locale="en-US", short_description=package.name, identifier=identifier)
    if file or external_url and version:
        current_app.logger.info("File and version found")
        installer = create_installer(package.publisher, identifier, version.version_code, installer_form)
        if installer is None:
            return "Error creating installer", 500

        version.installers.append(installer)

    package.versions.append(version)
    try:
        db.session.commit()
        current_app.logger.info(f"Version {version.version_code} added successfully to package {package.identifier}")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Database error: {e}")
        return "Database error", 500

    return redirect(request.referrer)


@api.route('/package/<identifier>/add_installer', methods=['POST'])
@login_required
@permission_required('add:installer')
def add_installer(identifier):
    form = AddInstallerForm(meta={'csrf': False})
    installer_form = form.installer

    if not form.validate_on_submit():
        validation_errors = form.errors
        current_app.logger.warning(f"Validation errors: {validation_errors}")
        return jsonify(validation_errors), 400
    
    
    
    
    package = Package.query.filter_by(identifier=identifier).first()
    if package is None:
        return "Package not found", 404
    
    # get version by id
    version = PackageVersion.query.filter_by(version_code=installer_form.version.data).first()
    if version is None:
        return "Package version not found", 404

    if installer_form.file or installer_form.url.data and version:
        current_app.logger.info("File and version found")
        installer = create_installer(package.publisher, identifier, version.version_code, installer_form)
        if installer is None:
            return "Error creating installer", 500

        version.installers.append(installer)
        db.session.commit()

        return redirect(request.referrer)
    

@api.route('/package/<identifier>/edit_installer', methods=['POST'])
@login_required
@permission_required('edit:installer')
def edit_installer(identifier):
    id = request.form['installer_id']
    # Get installer
    installer = Installer.query.filter_by(id=id).first()
    if installer is None:
        return "Installer not found", 404
    
    current_app.logger.info(f"Installer found: {installer}")

    current_app.logger.info("Going through installer switches to update them")
    for field_name in installer_switches:
        current_app.logger.info(f"Field name: {field_name}")
        if field_name in request.form:
            current_app.logger.info(f"Field name found {field_name}")
            field_value = request.form.get(field_name)
            installer_switch = InstallerSwitch.query.filter_by(installer_id=id, parameter=field_name).first()
            if installer_switch is None:
                installer_switch = InstallerSwitch()
                installer_switch.parameter = field_name                
                installer_switch.value = field_value
                installer.switches.append(installer_switch)
            else:
                installer_switch.value = field_value
        else:
            # If the field name isn't in the request form, check if it exists in the database and delete it if it does
            installer_switch = InstallerSwitch.query.filter_by(installer_id=id, parameter=field_name).first()
            if installer_switch is not None:
                db.session.delete(installer_switch)

        db.session.commit()

    return redirect(request.referrer)

                



@api.route('/package/<identifier>/<version>/<installer>', methods=['DELETE'])
@login_required
@permission_required('delete:installer')
def delete_installer(identifier, version, installer):
    package = Package.query.filter_by(identifier=identifier).first()
    if package is None:
        current_app.logger.warning("Package not found")
        return "Package not found", 404
    
    version = PackageVersion.query.filter_by(identifier=identifier, version_code=version).first()
    if version is None:
        current_app.logger.warning("Version not found")
        return "Version not found", 404

    installer = Installer.query.filter_by(id=installer).first()
    if installer is None:
        current_app.logger.warning("Installer not found")
        return "Installer not found", 404
    
    delete_installer_util(package, installer, version)

    
    db.session.delete(installer)
    db.session.commit()

    return "", 200

@api.route('/package/<identifier>/<version>', methods=['DELETE'])
@login_required
@permission_required('delete:version')
def delete_version(identifier, version):
    package = Package.query.filter_by(identifier=identifier).first()
    if package is None:
        current_app.logger.warning("Package not found")
        return "Package not found", 404
    
    version = PackageVersion.query.filter_by(identifier=identifier, version_code=version).first()
    if version is None:
        current_app.logger.warning("Version not found")
        return "Version not found", 404

    for installer in version.installers:
        delete_installer_util(package, installer, version)
    db.session.delete(version)
    try:
        db.session.commit()
        current_app.logger.info(f"Version {version.version_code} successfully removed from package {package.identifier}")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Database error: {e}")
        return "Database error", 500

    return "", 200

@api.route('/update_user', methods=['POST'])
@login_required
@permission_required('edit:own_user')
def update_user():
    id = request.form['id']
    username = request.form['username'].lower().replace(" ", "")
    email = request.form['email'].lower().replace(" ", "")
    password = request.form['password']    

    user = User.query.filter_by(id=id).first()
    if user is None:
        return "User not found", 404
    
    # Check that email or username or both aren't used by another user before updating except for the current user
    if User.query.filter(User.id != id, User.email == email).first():
        flash('Email already in use', 'error')
        return redirect(request.referrer)
    if User.query.filter(User.id != id, User.username == username).first():
        flash('Username already in use', 'error')
        return redirect(request.referrer)
    
    user.username = username
    user.email = email
    if password:
        user.set_password(password)
        db.session.commit()
        flash('Password changed, please login again.', 'success')
        return redirect(url_for('auth.logout'))
    


    try:
        db.session.commit()
        current_app.logger.info(f"User {user.username} updated successfully")
    except Exception as error:
        current_app.logger.error(f"Database error: {error}")
        db.session.rollback()

    flash('User updated successfully.', 'success')
    return redirect(request.referrer)

@api.route('/change_role/<user>', methods=['POST'])
@login_required
@permission_required('edit:user')
def change_role(user):
    role_id = request.form['role_id']

    user = User.query.filter_by(id=user).first()
    if user is None:
        return "User not found", 404
    
    role = Role.query.filter_by(id=role_id).first()
    if role is None:
        return "Role not found", 404
    old_role = user.role
    user.role = role
    try:
        db.session.commit()
        current_app.logger.info(f"Changed role from user {user.username} to {role.name} from {old_role.name}")
    except Exception as error:
        current_app.logger.error(f"Database error: {error}")
        db.session.rollback()
    flash('Role changed successfully.', 'success')
    response = Response()
    redirect_url = url_for('ui.users')  # Replace 'index' with the endpoint you want to redirect to
    response.headers['HX-Redirect'] = redirect_url
    return response

@api.route('/add_user', methods=['POST'])
@login_required
@permission_required('add:user')
def add_user():
    username = request.form['username'].lower().replace(" ", "")
    email = request.form['email'].lower().replace(" ", "")
    password = request.form['password']
    role = request.form['role']

    # Check that email or username or both aren't used by another user before updating except for the current user
    if User.query.filter(User.email == email).first():
        flash('Email already in use', 'error')
        return redirect(request.referrer)
    if User.query.filter(User.username == username).first():
        flash('Username already in use', 'error')
        return redirect(request.referrer)

    role = Role.query.filter_by(id=role).first()
    if role is None:
        flash('Role not found', 'error')
        return redirect(request.referrer)
    
    user = User(username=username, email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    try:
        db.session.commit()
        current_app.logger.info(f"User {user.username} added successfully")
    except Exception as error:
        current_app.logger.error(f"Database error: {error}")
        db.session.rollback()
        flash('Database error', 'error')
        return redirect(request.referrer)
    
    flash('User added successfully.', 'success')
    return redirect(request.referrer)



@api.route('/add_role', methods=['POST'])
@login_required
@permission_required('add:role')
def add_role():
    name = request.form['name'].lower().replace(" ", "")
    permissions = request.form['permissions'].split(',')
    role = Role(name=name)
    for permission in permissions:
        permission = Permission.query.filter_by(name=permission).first()
        role.permissions.append(permission)
    db.session.add(role)

    try:
        db.session.commit()
    except Exception as error:
        db.session.rollback()
        message = str(error.orig)
        flash(message, 'error')
        return redirect(request.referrer)
    
    flash('Role added successfully.', 'success')
    return redirect(request.referrer)

@api.route('/delete_role/<id>', methods=['DELETE'])
@login_required
@permission_required('delete:role')
def delete_role(id):
    role = Role.query.filter_by(id=id).first()
    if role is None:
        return "Role not found", 404
    # Check if any users have this role
    users = User.query.filter_by(role_id=id).all()
    if users:
        return "Role has users assigned to it, please remove them first", 400
    db.session.delete(role)
    try:
        db.session.commit()
        current_app.logger.info(f"Role {role.name} deleted successfully")
    except Exception as error:
        current_app.logger.error(f"Database error: {error}")
        db.session.rollback()

    return "", 200



@api.route('/delete_user/<id>', methods=['DELETE'])
@login_required
@permission_required('delete:user')
def delete_user(id):
    user = User.query.filter_by(id=id).first()
    
    if user is None:
        return "User not found", 404
    db.session.delete(user)
    try:
        db.session.commit()
        current_app.logger.info(f"User {user.username} deleted")
    except Exception as error:
        current_app.logger.error(f"Database error: {error}")
        db.session.rollback()


    return "", 200

@api.route('/download/<identifier>/<version>/<architecture>/<scope>')
def download(identifier, version, architecture, scope):
    # TODO: Improve this function to be more efficient, also when a package's publisher is renamed the file won't be found anymore
    package = Package.query.filter_by(identifier=identifier).first()
    if package is None:
        current_app.logger.warning("Package not found")
        return "Package not found", 404
    
    # Get version of package and also match package
    version_code = PackageVersion.query.filter_by(version_code=version, identifier=identifier).first()
    if version_code is None:
        current_app.logger.warning("Version not found")
        return "Package version not found", 404
    # Get installer of package version and also match architecture and identifier
    installer = Installer.query.filter_by(version_id=version_code.id, architecture=architecture, scope=scope).first()
    if installer is None:
        current_app.logger.warning("Installer not found")
        return "Installer not found", 404
    
    if current_app.config['USE_S3'] and installer.external_url is None:
        current_app.logger.info("Downloading from S3")
        # Generate a pre-signed URL for the S3 object
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': current_app.config['BUCKET_NAME'],
                'Key': 'packages/' + package.publisher + '/' + package.identifier + '/' + version_code.version_code + '/' + installer.architecture + '/' + installer.file_name,
                'ResponseContentDisposition': 'attachment; filename=' + installer.file_name,
                'ResponseContentType': 'application/octet-stream'
            },
            ExpiresIn=URL_EXPIRATION_SECONDS
        )

        # Increment the download count and commit to the database
        package.download_count += 1
        db.session.commit()

        # Redirect the client to the pre-signed URL
        return redirect(presigned_url)

    # If the installer has an external URL, redirect the client to it
    if installer.external_url:
        current_app.logger.info("Downloading from external URL")
        # Increment the download count and commit to the database
        package.download_count += 1
        db.session.commit()

        # Redirect the client to the pre-signed URL
        return redirect(installer.external_url)


    installer_path = os.path.join(basedir, 'packages', package.publisher, package.identifier, version_code.version_code, installer.architecture)

    current_app.logger.info("Starting download for package:")
    current_app.logger.info(f"Package name: {package.name}")
    current_app.logger.info(f"Package identifier: {package.identifier}")
    current_app.logger.info(f"Package version: {version_code.version_code}")
    current_app.logger.info(f"Architecture: {installer.architecture}")
    current_app.logger.info(f"Installer file name: {installer.file_name}")
    current_app.logger.info(f"Installer SHA256: {installer.installer_sha256}")
    current_app.logger.info(f"Installer path: {installer_path + '/' + installer.file_name}")
    if installer.external_url:
        current_app.logger.info(f"External URL: {installer.external_url}")

    # Check if the Range header is present
    range_header = request.headers.get('Range')

    is_partial = range_header is not None
    if is_partial:
        request.range = parse_range_header(range_header)
        if request.range is None:
            current_app.logger.warning("Invalid range header")
            return "Invalid range header", 400

    # Only add to download_count for a whole file download not part of it (winget uses range)
    if (is_partial and range_header and range_header == "bytes=0-1") or not is_partial:
        package.download_count += 1
        db.session.commit()

        

    return send_from_directory(installer_path, installer.file_name, as_attachment=True)