import logging
import os
import boto3
from flask import (
    Blueprint,
    Response,
    jsonify,
    render_template,
    request,
    redirect,
    stream_with_context,
    url_for,
    current_app,
    send_from_directory,
    flash,
)
from flask_login import current_user, login_required
from werkzeug.http import parse_range_header
from werkzeug.utils import secure_filename
from looseversion import LooseVersion
import requests
from app import db
from app.decorators import permission_required
from app.forms import AddInstallerForm, AddPackageForm, AddVersionForm
from app.models import (
    AccessLog,
    DownloadLog,
    InstallerSwitch,
    Package,
    PackageVersion,
    Installer,
    Permission,
    Role,
    Setting,
    User,
)

from semver import Version

from app.utils import (
    create_installer,
    custom_secure_filename,
    save_file,
    basedir,
    delete_installer_util,
)
from app.constants import installer_switches
from botocore.exceptions import ClientError

api = Blueprint("api", __name__)


@api.route("/")
def index():
    return "API is running, see documentation for more information", 200


URL_EXPIRATION_SECONDS = 3600


@api.get("/packages")
@login_required
@permission_required("view:package")
def packages():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("limit", 10, type=int)
    search_query = request.args.get("search", "", type=str)

    query = Package.query

    if search_query:
        search = "%{}%".format(search_query)
        query = query.filter(
            db.or_(
                Package.name.ilike(search),
                Package.identifier.ilike(search),
                Package.publisher.ilike(search),
            )
        )

    paginated_packages = query.paginate(page=page, per_page=per_page, error_out=False)
    packages = paginated_packages.items

    return jsonify(
        {
            "packages": [package.to_dict() for package in packages],
            "total": paginated_packages.total,
            "pages": paginated_packages.pages,
            "current_page": paginated_packages.page,
        }
    )


@api.get("/package/<identifier>")
@login_required
@permission_required("view:package", resource_type="Package", resource_id_key="identifier")
def package(identifier):
    # Use identifier and check if its the id or the package identifier
    if identifier.isdigit():
        package = Package.query.get(identifier)
    else:
        package = Package.query.filter_by(identifier=identifier).first()
    if package is None:
        return "Package not found", 404
    return jsonify(package.to_dict())


@api.get("/package/<identifier>/versions")
@login_required
@permission_required("view:version")
def package_versions(identifier):
    package = Package.query.filter_by(identifier=identifier).first()
    if package is None:
        return "Package not found", 404
    return jsonify([version.to_dict() for version in package.versions])


@api.get("/package/<identifier>/version/<version>")
@login_required
@permission_required("view:version")
def package_version(identifier, version):
    version = PackageVersion.query.filter_by(
        identifier=identifier, version_code=version
    ).first()
    if version is None:
        return "Version not found", 404
    return jsonify(version.to_dict())


@api.get("/package/<identifier>/version/<version>/installers")
@login_required
@permission_required("view:installer")
def package_installers(identifier, version):
    version = PackageVersion.query.filter_by(
        identifier=identifier, version_code=version
    ).first()
    if version is None:
        return "Version not found", 404
    return jsonify([installer.to_dict() for installer in version.installers])


@api.get("/package/<identifier>/version/<version>/installer/<installer>")
@login_required
@permission_required("view:installer")
def package_installer(identifier, version, installer):
    installer = Installer.query.filter_by(id=installer).first()
    if installer is None:
        return "Installer not found", 404
    return jsonify(installer.to_dict())


@api.get("/installer/<installer_id>")
@login_required
@permission_required("view:installer")
def get_installer_by_id(installer_id):
    installer = Installer.query.get(installer_id)
    if installer is None:
        return "Installer not found", 404
    return jsonify(installer.to_dict())


@api.get("/version/<version_id>")
@login_required
@permission_required("view:version")
def get_version_by_id(version_id):
    version = PackageVersion.query.get(version_id)
    if version is None:
        return "Version not found", 404
    return jsonify(version.to_dict())


@api.route("/generate_presigned_url", methods=["POST"])
@login_required
@permission_required("add:installer")
def generate_presigned_url():
    try:
        # Extract file information from the request
        file_name = request.form.get("file_name")
        file_extension = file_name.rsplit(".", 1)[1]
        content_type = request.form.get("content_type")

        # Specify the S3 object key where the file will be uploaded
        publisher = custom_secure_filename(request.form.get("publisher"))
        identifier = custom_secure_filename(request.form.get("identifier"))
        # Get version from db either by id or by name from the request
        version = custom_secure_filename(request.form.get("installer-version"))

        architecture = custom_secure_filename(
            request.form.get("installer-architecture")
        )
        scope = request.form.get(
            "installer-installer_scope"
        )  # Add this to the request form
        # Define the S3 object key with the same format as 'scope.file_extension'
        s3_object_key = f"packages/{publisher}/{identifier}/{version}/{architecture}/{scope}.{file_extension}"

        s3_client = boto3.client(
            "s3",
            endpoint_url=Setting.get("S3_ENDPOINT").get_value(),
            aws_access_key_id=Setting.get("S3_ACCESS_KEY_ID").get_value(),
            aws_secret_access_key=Setting.get("S3_SECRET_ACCESS_KEY").get_value(),
            config=boto3.session.Config(signature_version="s3v4"),
            region_name=Setting.get("S3_REGION").get_value(),
        )

        # Generate a pre-signed URL for S3 uploads
        presigned_url = s3_client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": Setting.get("S3_BUCKET_NAME").get_value(),
                "Key": s3_object_key,
                "ContentType": content_type,
            },
            ExpiresIn=URL_EXPIRATION_SECONDS,
        )
        log = AccessLog(
            user_id=current_user.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
            action=f"Generated presigned URL for {file_name} with content type {content_type} and S3 object key {s3_object_key} ",
        )
        db.session.add(log)
        # Return the pre-signed URL and other information in the response
        return jsonify(
            {
                "presigned_url": presigned_url,
                "content_type": content_type,
                "file_name": file_name,
                "file_path": s3_object_key,  # Include the S3 object key for reference
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api.route("/add_package", methods=["POST"])
@login_required
@permission_required("add:package")
def add_package():
    form = AddPackageForm(meta={"csrf": False})
    installer_form = form.installer

    if not form.validate_on_submit():
        validation_errors = form.errors
        return str("Form validation error"), 500

    name = form.name.data
    publisher = custom_secure_filename(form.publisher.data)
    identifier = form.identifier.data
    version = installer_form.version.data
    file = installer_form.file.data
    external_url = installer_form.url.data
    is_aws = installer_form.is_aws.data

    package = Package(identifier=identifier, name=name, publisher=publisher)

    if file or external_url and version:
        current_app.logger.info("File and version found")
        if not current_user.role.has_permission("add:installer"):
            current_app.logger.warning("User doesn't have permission to add installer")
            return "User doesn't have permission to add installer", 403

        installer = create_installer(publisher, identifier, version, installer_form)
        if installer is None:
            return "Error creating installer", 500
        
        try:
            # Check using LooseVersion to see if the version is a valid version number
            LooseVersion(version)
        except ValueError:
            return Response("Invalid version number, please use a valid semver version", 400)

        version_code = PackageVersion(
            version_code=version,
            package_locale="en-US",
            short_description=name,
            identifier=identifier,
        )
        version_code.installers.append(installer)
        package.versions.append(version_code)
    log = AccessLog(
        user_id=current_user.id,
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent"),
        action=f"Added package {package.identifier}",
    )
    db.session.add(log)
    try:
        db.session.add(package)
        db.session.commit()
        current_app.logger.info(f"Package {package.identifier} added successfully")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Database error: {e}")
        return "Database error", 500

    flash("Package added successfully.", "success")
    return "Package added", 200


@api.route("/package/<identifier>", methods=["POST"])
@login_required
@permission_required("edit:package")
def update_package(identifier):
    package = Package.query.filter_by(identifier=identifier).first()
    if package is None:
        return "Package not found", 404
    name = request.form["name"]
    publisher = request.form["publisher"]
    package.name = name
    package.publisher = publisher
    log = AccessLog(
        user_id=current_user.id,
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent"),
        action=f"Updated package {package.identifier} with name {package.name} and publisher {package.publisher}",
    )
    db.session.add(log)
    db.session.commit()
    return redirect(request.referrer)


@api.delete("/package/<identifier>")
@login_required
@permission_required("delete:package")
def delete_package(identifier):
    package = Package.query.filter_by(identifier=identifier).first()
    if package is None:
        return "Package not found", 404
    db.session.delete(package)
    log = AccessLog(
        user_id=current_user.id,
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent"),
        action=f"Deleted package {package.identifier}",
    )
    db.session.add(log)
    db.session.commit()
    return "", 204


@api.route("/package/<identifier>/add_version", methods=["POST"])
@login_required
@permission_required("add:version")
def add_version(identifier):
    form = AddVersionForm(meta={"csrf": False})

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
    # Check that version is a valid version number
    try:
        LooseVersion(version)
    except ValueError:
        return Response("Invalid version number, please use a valid semver version", 400)

    version = PackageVersion(
        version_code=version,
        package_locale="en-US",
        short_description=package.name,
        identifier=identifier,
    )
    if file or external_url and version:
        current_app.logger.info("File and version found")
        if not current_user.role.has_permission("add:installer"):
            current_app.logger.warning("User doesn't have permission to add installer")
            return "User doesn't have permission to add installer", 403
        installer = create_installer(
            package.publisher, identifier, version.version_code, installer_form
        )
        if installer is None:
            return "Error creating installer", 500

        version.installers.append(installer)

    package.versions.append(version)
    log = AccessLog(
        user_id=current_user.id,
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent"),
        action=f"Added version {version.version_code} to package {package.identifier}",
    )
    db.session.add(log)
    try:
        db.session.commit()
        current_app.logger.info(
            f"Version {version.version_code} added successfully to package {package.identifier}"
        )
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Database error: {e}")
        return "Database error", 500

    return redirect(request.referrer)


@api.route("/package/<identifier>/add_installer", methods=["POST"])
@login_required
@permission_required("add:installer")
def add_installer(identifier):
    form = AddInstallerForm(meta={"csrf": False})
    installer_form = form.installer

    if not form.validate_on_submit():
        validation_errors = form.errors
        current_app.logger.warning(f"Validation errors: {validation_errors}")
        return jsonify(validation_errors), 400

    package = Package.query.filter_by(identifier=identifier).first()
    if package is None:
        return "Package not found", 404

    # get version by id
    version = PackageVersion.query.filter_by(
        version_code=installer_form.version.data
    ).first()
    if version is None:
        return "Package version not found", 404

    if installer_form.file or installer_form.url.data and version:
        current_app.logger.info("File and version found")
        installer = create_installer(
            package.publisher, identifier, version.version_code, installer_form
        )
        if installer is None:
            return "Error creating installer", 500

        version.installers.append(installer)
        log = AccessLog(
            user_id=current_user.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
            action=f"Added installer {installer.file_name} to package {package.identifier}",
        )
        db.session.add(log)
        db.session.commit()

        return redirect(request.referrer)


@api.route("/package/<identifier>/edit_installer", methods=["POST"])
@login_required
@permission_required("edit:installer")
def edit_installer(identifier):
    id = request.form["installer_id"]
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
            installer_switch = InstallerSwitch.query.filter_by(
                installer_id=id, parameter=field_name
            ).first()
            if installer_switch is None:
                installer_switch = InstallerSwitch()
                installer_switch.parameter = field_name
                installer_switch.value = field_value
                installer.switches.append(installer_switch)
            else:
                installer_switch.value = field_value
        else:
            # If the field name isn't in the request form, check if it exists in the database and delete it if it does
            installer_switch = InstallerSwitch.query.filter_by(
                installer_id=id, parameter=field_name
            ).first()
            if installer_switch is not None:
                db.session.delete(installer_switch)
        log = AccessLog(
            user_id=current_user.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
            action=f"Updated installer {installer.file_name} from package {identifier}",
        )
        db.session.add(log)
        db.session.commit()

    return redirect(request.referrer)


@api.route("/package/<identifier>/<version>/<installer>", methods=["DELETE"])
@login_required
@permission_required("delete:installer")
def delete_installer(identifier, version, installer):
    package = Package.query.filter_by(identifier=identifier).first()
    if package is None:
        current_app.logger.warning("Package not found")
        return "Package not found", 404

    version = PackageVersion.query.filter_by(
        identifier=identifier, version_code=version
    ).first()
    if version is None:
        current_app.logger.warning("Version not found")
        return "Version not found", 404

    installer = Installer.query.filter_by(id=installer).first()
    if installer is None:
        current_app.logger.warning("Installer not found")
        return "Installer not found", 404

    delete_installer_util(package, installer, version)

    db.session.delete(installer)
    log = AccessLog(
        user_id=current_user.id,
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent"),
        action=f"Deleted installer {installer.file_name} from package {package.identifier}",
    )
    db.session.add(log)
    db.session.commit()

    return "", 200


@api.route("/package/<identifier>/<version>", methods=["DELETE"])
@login_required
@permission_required("delete:version")
def delete_version(identifier, version):
    package = Package.query.filter_by(identifier=identifier).first()
    if package is None:
        current_app.logger.warning("Package not found")
        return "Package not found", 404
    version = PackageVersion.query.filter_by(
        identifier=identifier, version_code=version
    ).first()
    if version is None:
        current_app.logger.warning("Version not found")
        return "Version not found", 404

    for installer in version.installers:
        delete_installer_util(package, installer, version)
    db.session.delete(version)
    log = AccessLog(
        user_id=current_user.id,
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent"),
        action=f"Deleted version {version.version_code} from package {package.identifier}",
    )
    db.session.add(log)
    try:
        db.session.commit()
        current_app.logger.info(
            f"Version {version.version_code} successfully removed from package {package.identifier}"
        )
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Database error: {e}")
        return "Database error", 500

    return "", 200


@api.route("/update_user", methods=["POST"])
@login_required
@permission_required("edit:own_user")
def update_user():
    id = request.form["id"]
    username = request.form["username"].lower().replace(" ", "")
    email = request.form["email"].lower().replace(" ", "")
    password = request.form["password"]

    user = User.query.filter_by(id=id).first()
    if user is None:
        return "User not found", 404

    # Check that email or username or both aren't used by another user before updating except for the current user
    if User.query.filter(User.id != id, User.email == email).first():
        flash("Email already in use", "error")
        return redirect(request.referrer)
    if User.query.filter(User.id != id, User.username == username).first():
        flash("Username already in use", "error")
        return redirect(request.referrer)

    user.username = username
    user.email = email
    if password:
        user.set_password(password)
        db.session.commit()
        flash("Password changed, please login again.", "success")
        return redirect(url_for("auth.logout"))
    log = AccessLog(
        user_id=current_user.id,
        action=f"Updated user {user.username} with email {user.email} and role {user.role.name} ",
    )
    db.session.add(log)
    try:
        db.session.commit()
        current_app.logger.info(f"User {user.username} updated successfully")

    except Exception as error:
        current_app.logger.error(f"Database error: {error}")
        db.session.rollback()

    flash("User updated successfully.", "success")
    return redirect(request.referrer)


@api.route("/change_role/<user>", methods=["POST"])
@login_required
@permission_required("edit:user")
def change_role(user):
    role_id = request.form["role_id"]

    user = User.query.filter_by(id=user).first()
    if user is None:
        return "User not found", 404

    role = Role.query.filter_by(id=role_id).first()
    if role is None:
        return "Role not found", 404
    old_role = user.role
    user.role = role
    log = AccessLog(
        user_id=current_user.id,
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent"),
        action=f"Changed role of user {user.username} from {old_role.name} to {role.name}",
    )
    db.session.add(log)
    try:

        db.session.commit()
        current_app.logger.info(
            f"Changed role from user {user.username} to {role.name} from {old_role.name}"
        )
        flash("Role changed successfully.", "success")
    except Exception as error:
        current_app.logger.error(f"Database error: {error}")
        db.session.rollback()
        flash("Database error", "error")
    response = Response()
    redirect_url = url_for("ui.users")
    response.headers["HX-Redirect"] = redirect_url
    return response


@api.route("/add_user", methods=["POST"])
@login_required
@permission_required("add:user")
def add_user():
    username = request.form["username"].lower().replace(" ", "")
    email = request.form["email"].lower().replace(" ", "")
    password = request.form["password"]
    role = request.form["role"]

    # Check that email or username or both aren't used by another user before updating except for the current user
    if User.query.filter(User.email == email).first():
        flash("Email already in use", "error")
        return redirect(request.referrer)
    if User.query.filter(User.username == username).first():
        flash("Username already in use", "error")
        return redirect(request.referrer)

    role = Role.query.filter_by(id=role).first()
    if role is None:
        flash("Role not found", "error")
        return redirect(request.referrer)

    user = User(username=username, email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    log = AccessLog(
        user_id=current_user.id,
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent"),
        action=f"Added user {user.username}",
    )
    db.session.add(log)
    try:
        db.session.commit()
        current_app.logger.info(f"User {user.username} added successfully")
    except Exception as error:
        current_app.logger.error(f"Database error: {error}")
        db.session.rollback()
        flash("Database error", "error")
        return redirect(request.referrer)

    flash("User added successfully.", "success")
    return redirect(request.referrer)


@api.route("/update_setting", methods=["POST"])
@login_required
@permission_required("edit:settings")
def update_setting():
    data = request.json

    if not data or "key" not in data:
        return jsonify(message="Invalid data"), 400

    key = data["key"]
    value = data.get("value", "false")

    setting = Setting.query.filter_by(key=key).first()
    if setting is None:
        return jsonify(message="Setting not found"), 404

    # Update the setting's value
    setting.set_value(value)
    log = AccessLog(
        user_id=current_user.id,
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent"),
        action=f"Updated setting {setting.key} to {setting.value}",
    )
    db.session.add(log)
    db.session.commit()

    return jsonify(setting.to_dict())


@api.get("/settings")
@login_required
@permission_required("view:settings")
def settings():
    # Return settings as json
    settings = Setting.query.all()
    # If config IS_CLOUD is set to True, remove the S3 settings
    if current_app.config["IS_CLOUD"]:
        settings = [
            setting
            for setting in settings
            if "s3" not in setting.key and "uplink" not in setting.key
        ]

    settings = sorted(settings, key=lambda x: x.position)
    return jsonify([setting.to_dict() for setting in settings])


@api.get("/whoami")
@login_required
def whoami():
    return jsonify(current_user.to_dict())


@api.route("/add_role", methods=["POST"])
@login_required
@permission_required("add:role")
def add_role():
    name = request.form["name"].lower().replace(" ", "")
    permissions = request.form["permissions"].split(",")
    role = Role(name=name)
    for permission in permissions:
        permission = Permission.query.filter_by(name=permission).first()
        role.permissions.append(permission)
    db.session.add(role)
    log = AccessLog(
        user_id=current_user.id,
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent"),
        action=f"Added role {role.name}",
    )
    db.session.add(log)
    try:
        db.session.commit()
    except Exception as error:
        db.session.rollback()
        message = str(error.orig)
        flash(message, "error")
        return redirect(request.referrer)

    flash("Role added successfully.", "success")
    return redirect(request.referrer)


@api.route("/delete_role/<id>", methods=["DELETE"])
@login_required
@permission_required("delete:role")
def delete_role(id):
    role = Role.query.filter_by(id=id).first()
    if role is None:
        return "Role not found", 404
    # Check if any users have this role
    users = User.query.filter_by(role_id=id).all()
    if users:
        return "Role has users assigned to it, please remove them first", 400
    db.session.delete(role)
    log = AccessLog(
        user_id=current_user.id,
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent"),
        action=f"Deleted role {role.name}",
    )
    db.session.add(log)
    try:
        db.session.commit()
        current_app.logger.info(f"Role {role.name} deleted successfully")
    except Exception as error:
        current_app.logger.error(f"Database error: {error}")
        db.session.rollback()

    return "", 200


@api.route("/delete_user/<id>", methods=["DELETE"])
@login_required
@permission_required("delete:user")
def delete_user(id):
    user = User.query.filter_by(id=id).first()

    if user is None:
        return "User not found", 404
    db.session.delete(user)
    log = AccessLog(
        user_id=current_user.id,
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent"),
        action=f"Deleted user {user.username}",
    )
    db.session.add(log)

    try:
        db.session.commit()
        current_app.logger.info(f"User {user.username} deleted")
    except Exception as error:
        current_app.logger.error(f"Database error: {error}")
        db.session.rollback()

    return "", 200


@api.route("/download/<identifier>/<version>/<architecture>/<scope>")
def download(identifier, version, architecture, scope):
    # TODO: Improve this function to be more efficient, also when a package's publisher is renamed the file won't be found anymore
    package = Package.query.filter_by(identifier=identifier).first()
    if package is None:
        current_app.logger.warning("Package not found")
        return "Package not found", 404

    # Get version of package and also match package
    version_code = PackageVersion.query.filter_by(
        version_code=version, identifier=identifier
    ).first()
    if version_code is None:
        current_app.logger.warning("Version not found")
        return "Package version not found", 404
    # Get installer of package version and also match architecture and identifier
    installer = Installer.query.filter_by(
        version_id=version_code.id, architecture=architecture, scope=scope
    ).first()
    if installer is None:
        current_app.logger.warning("Installer not found")
        return "Installer not found", 404

    # Log the download
    ip_address = request.remote_addr
    user_agent = request.headers.get("User-Agent")
    download_log = DownloadLog(
        installer=installer, ip_address=ip_address, user_agent=user_agent
    )
    db.session.add(download_log)

    if Setting.get("USE_S3").get_value() and installer.external_url is None:
        current_app.logger.info("Downloading from S3")
        # Generate a pre-signed URL for the S3 object
        s3_client = boto3.client(
            "s3",
            endpoint_url=Setting.get("S3_ENDPOINT").get_value(),
            aws_access_key_id=Setting.get("S3_ACCESS_KEY_ID").get_value(),
            aws_secret_access_key=Setting.get("S3_SECRET_ACCESS_KEY").get_value(),
            config=boto3.session.Config(signature_version="s3v4"),
            region_name=Setting.get("S3_REGION").get_value(),
        )

        presigned_url = s3_client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": Setting.get("S3_BUCKET_NAME").get_value(),
                "Key": "packages/"
                + package.publisher
                + "/"
                + package.identifier
                + "/"
                + version_code.version_code
                + "/"
                + installer.architecture
                + "/"
                + installer.file_name,
                "ResponseContentDisposition": "attachment; filename="
                + installer.file_name,
                "ResponseContentType": "application/octet-stream",
            },
            ExpiresIn=URL_EXPIRATION_SECONDS,
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

    installer_path = os.path.join(
        basedir,
        "packages",
        package.publisher,
        package.identifier,
        version_code.version_code,
        installer.architecture,
    )

    current_app.logger.info("Starting download for package:")
    current_app.logger.info(f"Package name: {package.name}")
    current_app.logger.info(f"Package identifier: {package.identifier}")
    current_app.logger.info(f"Package version: {version_code.version_code}")
    current_app.logger.info(f"Architecture: {installer.architecture}")
    current_app.logger.info(f"Installer file name: {installer.file_name}")
    current_app.logger.info(f"Installer SHA256: {installer.installer_sha256}")
    current_app.logger.info(
        f"Installer path: {installer_path + '/' + installer.file_name}"
    )
    if installer.external_url:
        current_app.logger.info(f"External URL: {installer.external_url}")

    # Check if the Range header is present
    range_header = request.headers.get("Range")

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


@api.route("/downloadLog")
@login_required
def download_log():
    download_logs = DownloadLog.query.all()
    download_logs = sorted(download_logs, key=lambda x: x.date, reverse=True)
    return jsonify([download_log.to_dict() for download_log in download_logs])


@api.route("accessLog")
@login_required
def access_log():
    access_logs = AccessLog.query.all()
    access_logs = sorted(access_logs, key=lambda x: x.date, reverse=True)
    return jsonify([access_log.to_dict() for access_log in access_logs])


@api.route("/get_latest_version")
def get_latest_version():
    # Get the lateest version of the app from GitHub releases
    response = requests.get(
        "https://api.github.com/repos/thilojaeggi/WinGetty/releases/latest"
    )
    if response.status_code != 200:
        return "Error fetching latest version", 500
    data = response.json()
    # Strip v from the version number
    version = data["tag_name"].lstrip("v")
    # Check if the version is newer than the current version
    if version != current_app.config["VERSION"]:
        return jsonify({"current_version": current_app.config["VERSION"], "latest_version": version})
    return "", 204

@api.route("/permissions")
@login_required
def permissions():
    permissions = Permission.query.all()
    return jsonify([permission.to_dict() for permission in permissions])