import hashlib
from flask import current_app

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