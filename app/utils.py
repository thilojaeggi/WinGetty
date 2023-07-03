import hashlib
import os
from flask import current_app, request
from werkzeug.utils import secure_filename
from app.models import Installer, InstallerSwitch
from app.constants import installer_switches


basedir = os.path.abspath(os.path.dirname(__file__))

def create_installer(file, publisher, identifier, version, architecture, installer_type):
    file_name = secure_filename(file.filename)
    hash = save_file(file, file_name, publisher, identifier, version, architecture)
    if hash is None:
        return None

    installer = Installer(architecture=architecture, installer_type=installer_type, file_name=file_name, installer_sha256=hash, scope="user")
    for field_name in installer_switches:
        debugPrint(f"Checking for field name {field_name}")
        if field_name in request.form:
            debugPrint(f"Field name found {field_name}")
            installer_switch = InstallerSwitch()
            installer_switch.key = field_name
            installer_switch.value = request.form.get(field_name)
            installer.switches.append(installer_switch)

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
    # Create directory if it doesn't exist
    save_directory = os.path.join(basedir, 'packages', publisher, identifier, version, architecture)
        # Create directory if it doesn't exist
    if not os.path.exists(save_directory):
        os.makedirs(save_directory)
    # Save file
    file_path = os.path.join(save_directory, file_name)
    file.save(file_path)
    # Get file hash
    hash = calculate_sha256(file_path)
    return hash