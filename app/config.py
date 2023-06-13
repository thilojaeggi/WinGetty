import os
from .utils import basedir

class Config:
    # Database configuration
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'database.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Repo configuration
    REPO_NAME = "WinGetty"

    # Version
    VERSION = "0.0.1"


