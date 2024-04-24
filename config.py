
from dynaconf import Dynaconf

import os

from flask import logging


def load_config(app, prefix='WINGETTY_'):
    for key in os.environ:
        if key.startswith(prefix):
            # Remove the prefix and set the value in the app's config
            setting_key = key[len(prefix):]  # Strip the prefix
            # if flask is in debug mode, log the setting
            app.logger.debug(f"Setting {setting_key} to {os.environ[key]}")
            # Ignore keys that are VERSION or REPO_NAME
            if setting_key in ['VERSION']:
                continue
            setting_value = os.environ[key]
            if setting_value.isdigit():
                setting_value = int(setting_value)  # Convert numbers to integers
            
            app.config[setting_key] = setting_value

class Config:
    """Base configuration with defaults (can be overridden by environment variables)."""
    SECRET_KEY = 'secret'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///database.db'
    VERSION = '1.1.0-alpha'
    IS_CLOUD = False
    PREFERRED_URL_SCHEME = 'https'


    @staticmethod
    def init_app(app):
        load_config(app)  # Load config from environment variables



# `envvar_prefix` = export envvars with `export DYNACONF_FOO=bar`.
# `settings_files` = Load these files in the order.
