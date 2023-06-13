import hashlib
import os
from flask import current_app

basedir = os.path.abspath(os.path.dirname(__file__))

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

def save_file(file, publisher, identifier, version, architecture):
    # Create directory if it doesn't exist
    save_directory = os.path.join(basedir, 'packages', publisher, identifier, version, architecture)
        # Create directory if it doesn't exist
    if not os.path.exists(save_directory):
        os.makedirs(save_directory)
    # Save file
    file_path = os.path.join(save_directory, file.filename)
    file.save(file_path)
    # Get file hash
    hash = calculate_sha256(file_path)
    return hash