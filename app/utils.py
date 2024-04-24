import hashlib
import logging
import os
import re
import requests
from flask import current_app, request
from werkzeug.utils import secure_filename
from app.models import Installer, InstallerSwitch, NestedInstallerFile, Setting
from app.constants import installer_switches
import boto3
from app.models.access.permission import Permission
from app.models.access.role import roles_permissions
from app.permissions import get_or_create

from app import db

URL_EXPIRATION_SECONDS = 3600
basedir = os.path.abspath(os.path.dirname(__file__))
from botocore.exceptions import ClientError


def get_file_hash_from_url(
    url, max_content_length=1024 * 1024 * 1024 * 10
):  # Default max content length set to 10GB
    """Download file from the given URL and return its SHA256 hash."""

    # Ensure the URL uses HTTPS
    if not url.startswith("https://"):
        raise ValueError("URL must use HTTPS.")

    response = requests.get(url, stream=True, timeout=15)  # Timeout set to 10 seconds
    response.raise_for_status()  # Ensure we got an OK response

    # Check if the content length exceeds the max content length
    content_length = int(response.headers.get("content-length", 0))
    if content_length > max_content_length:
        raise ValueError(
            f"Content length exceeds allowed limit of {max_content_length} bytes."
        )

    hash_sha256 = hashlib.sha256()
    for chunk in response.iter_content(chunk_size=4096):
        hash_sha256.update(chunk)

    return hash_sha256.hexdigest()


def create_installer(publisher, identifier, version, installer_form):
    file = installer_form.file.data
    external_url = installer_form.url.data
    is_aws = installer_form.is_aws.data
    architecture = installer_form.architecture.data
    installer_type = installer_form.installer_type.data
    scope = installer_form.installer_scope.data
    nestedinstallertype = installer_form.nestedinstallertype.data
    nestedinstallerpath = installer_form.nestedinstallerpath.data

    # If file is provided, save the file
    if file:
        file_name = custom_secure_filename(file.filename)
        file_name = f"{scope}." + file_name.rsplit(".", 1)[1]
        hash = save_file(file, file_name, publisher, identifier, version, architecture)
        if hash is None:
            return "Error saving file", 500
    elif not file and external_url and is_aws:
        current_app.logger.info("Installer is on AWS")
        file_name = external_url
        s3_object_key = (
            f"packages/{publisher}/{identifier}/{version}/{architecture}/{file_name}"
        )
        external_url = None

        # Generate a pre-signed URL for S3 uploads
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
                "Key": s3_object_key,
            },
            ExpiresIn=URL_EXPIRATION_SECONDS,
        )
        current_app.logger.info(
            f"Getting file hash from presigned URL: {presigned_url}"
        )
        hash = get_file_hash_from_url(presigned_url)
    # If no file is provided, but an external_url is available, use that
    elif external_url:
        current_app.logger.info("Getting file hash from external URL")
        hash = get_file_hash_from_url(external_url)
        file_name = None

    else:
        current_app.logger.error("No file or external URL provided")
        raise ValueError("Either a file or an external URL must be provided.")

    installer = Installer(
        architecture=architecture,
        installer_type=installer_type,
        file_name=file_name,
        external_url=external_url,
        installer_sha256=hash,
        scope=scope,
    )

    for field_name in installer_switches:
        current_app.logger.debug(f"Checking for field name {field_name}")
        if field_name in request.form:
            current_app.logger.debug(f"Field name found {field_name}")
            field_value = request.form.get(field_name)
            installer_switch = InstallerSwitch()
            installer_switch.parameter = field_name
            installer_switch.value = field_value
            installer.switches.append(installer_switch)

    if nestedinstallertype is not None and nestedinstallerpath is not None:
        installer.nested_installer_type = nestedinstallertype
        nested_installer_file = NestedInstallerFile(
            relative_file_path=nestedinstallerpath
        )
        installer.nested_installer_files.append(nested_installer_file)
    elif nestedinstallertype is not None or nestedinstallerpath is not None:
        return "Nested installer type and path should be provided together", 500

    return installer


def calculate_sha256(filename):
    sha256_hash = hashlib.sha256()

    with open(filename, "rb") as file:
        # Read the file in chunks to efficiently handle large files
        for chunk in iter(lambda: file.read(4096), b""):
            sha256_hash.update(chunk)

    return sha256_hash.hexdigest()


def delete_installer_util(package, installer, version):
    if not installer.external_url and installer.file_name:
        base_path = [
            "packages",
            package.publisher,
            package.identifier,
            version.version_code,
            installer.architecture,
        ]
        if Setting.get("USE_S3").get_value():
            s3_key = "/".join(base_path + [installer.file_name])
            current_app.logger.info(f"Deleting file from S3: {s3_key}")
            s3_client = boto3.client(
                "s3",
                endpoint_url=Setting.get("S3_ENDPOINT").get_value(),
                aws_access_key_id=Setting.get("S3_ACCESS_KEY_ID").get_value(),
                aws_secret_access_key=Setting.get("S3_SECRET_ACCESS_KEY").get_value(),
                config=boto3.session.Config(signature_version="s3v4"),
                region_name=Setting.get("S3_REGION").get_value(),
            )
            s3_client.delete_object(
                Bucket=Setting.get("S3_BUCKET_NAME").get_value(), Key=s3_key
            )
        else:
            # Construct the file system path
            installer_path = os.path.join(basedir, *base_path, installer.file_name)
            if os.path.exists(installer_path):
                current_app.logger.info(
                    f"Deleting file from local file system: {installer_path}"
                )
                os.remove(installer_path)


def save_file(file, file_name, publisher, identifier, version, architecture):
    publisher = custom_secure_filename(publisher)
    identifier = custom_secure_filename(identifier)
    version = custom_secure_filename(version)
    architecture = custom_secure_filename(architecture)

    # Create directory if it doesn't exist
    save_directory = os.path.join(
        basedir, "packages", publisher, identifier, version, architecture
    )
    if not os.path.exists(save_directory):
        os.makedirs(save_directory)

    # Save file locally
    file_path = os.path.join(save_directory, file_name)
    file.save(file_path)

    # Get file hash
    hash = calculate_sha256(file_path)
    return hash


# Custom secure filename function to allow for more characters (e.g. '+' in NotePad++ installer)
def custom_secure_filename(filename):
    filename = re.sub(r"[^\w\.\+\-]", "_", filename)
    return filename


def assign_permission_to_role(role, permission_name, resource_type=None, resource_id=None):
    permission = get_or_create(Permission, name=permission_name)
    association = {
        'role_id': role.id,
        'permission_id': permission.id,
        'resource_type': resource_type.value if resource_type else None,
        'resource_id': resource_id
    }
    db.session.execute(roles_permissions.insert().values(association))
    db.session.commit()

