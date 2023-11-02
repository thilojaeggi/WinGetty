import hashlib
import os
import requests
from flask import current_app, request
from werkzeug.utils import secure_filename
from app.models import Installer, InstallerSwitch, NestedInstallerFile
from app.constants import installer_switches
import boto3
s3_client = boto3.client('s3')
URL_EXPIRATION_SECONDS = 3600
basedir = os.path.abspath(os.path.dirname(__file__))


def get_file_hash_from_url(url, max_content_length=1024 * 1024 * 1024 * 10):  # Default max content length set to 10GB
    """Download file from the given URL and return its SHA256 hash."""
    
    # Ensure the URL uses HTTPS
    if not url.startswith("https://"):
        raise ValueError("URL must use HTTPS.")
    
    response = requests.get(url, stream=True, timeout=15)  # Timeout set to 10 seconds
    response.raise_for_status()  # Ensure we got an OK response
    
    # Check if the content length exceeds the max content length
    content_length = int(response.headers.get('content-length', 0))
    if content_length > max_content_length:
        raise ValueError(f"Content length exceeds allowed limit of {max_content_length} bytes.")
    
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
        file_name = secure_filename(file.filename)
        file_name = f'{scope}.' + file_name.rsplit('.', 1)[1]
        hash = save_file(file, file_name, publisher, identifier, version, architecture)
        if hash is None:
            return "Error saving file", 500
    elif not file and external_url and is_aws:
        file_name = external_url
        s3_object_key = f'packages/{publisher}/{identifier}/{version}/{architecture}/{file_name}'
        external_url = None

        # Generate a pre-signed URL for S3 uploads
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': current_app.config['BUCKET_NAME'], 'Key': s3_object_key},
            ExpiresIn=URL_EXPIRATION_SECONDS
        )
        
        hash = get_file_hash_from_url(presigned_url)
    # If no file is provided, but an external_url is available, use that
    elif external_url:
        print("Found external url")
        hash = get_file_hash_from_url(external_url)
        file_name = None

        
    else:
        print("Either a file or an external URL must be provided.")
        raise ValueError("Either a file or an external URL must be provided.")
    
    installer = Installer(
        architecture=architecture,
        installer_type=installer_type,
        file_name=file_name,
        external_url=external_url,
        installer_sha256=hash,
        scope=scope
    )

    for field_name in installer_switches:
        debugPrint(f"Checking for field name {field_name}")
        if field_name in request.form:
            debugPrint(f"Field name found {field_name}")
            field_value = request.form.get(field_name)
            installer_switch = InstallerSwitch()
            installer_switch.parameter = field_name
            installer_switch.value = field_value
            installer.switches.append(installer_switch)

    if nestedinstallertype is not None and nestedinstallerpath is not None:
        installer.nested_installer_type = nestedinstallertype
        nested_installer_file = NestedInstallerFile(relative_file_path=nestedinstallerpath)
        installer.nested_installer_files.append(nested_installer_file)
    elif nestedinstallertype is not None or nestedinstallerpath is not None:
        return "Nested installer type and path should be provided together", 500

    return installer

def calculate_sha256(filename):
    sha256_hash = hashlib.sha256()

    with open(filename, 'rb') as file:
        # Read the file in chunks to efficiently handle large files
        for chunk in iter(lambda: file.read(4096), b''):
            sha256_hash.update(chunk)

    return sha256_hash.hexdigest()

def debugPrint(message):
    if current_app.config['DEBUG']:
        print(message)

def save_file(file, file_name, publisher, identifier, version, architecture):
    publisher = secure_filename(publisher)
    identifier = secure_filename(identifier)
    version = secure_filename(version)
    architecture = secure_filename(architecture)


    # Create directory if it doesn't exist
    save_directory = os.path.join(basedir, 'packages', publisher, identifier, version, architecture)
    if not os.path.exists(save_directory):
        os.makedirs(save_directory)

    # Save file locally
    file_path = os.path.join(save_directory, file_name)
    file.save(file_path)

    # Get file hash
    hash = calculate_sha256(file_path)
    return hash