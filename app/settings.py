from flask import current_app
from app.models import Permission, Role, Setting, User
from app import db
from sqlalchemy.exc import IntegrityError


def get_or_create(model, **kwargs):
    """Get an instance if it exists, otherwise create and return an instance.
    Update the instance if name or description is different."""
    key = kwargs.get("key")
    instance = model.query.filter_by(key=key).first()
    if instance:
        # Check for changes in name or description
        if "name" in kwargs and instance.name != kwargs["name"]:
            instance.name = kwargs["name"]
        if "description" in kwargs and instance.description != kwargs["description"]:
            instance.description = kwargs["description"]
        if "depends_on" in kwargs and instance.depends_on != kwargs["depends_on"]:
            instance.depends_on = kwargs["depends_on"]
        if "position" in kwargs and instance.position != kwargs["position"]:
            instance.position = kwargs["position"]
        return instance
    else:
        instance = model(**kwargs)
        db.session.add(instance)
        return instance


def create_settings():
    repository_settings = [
        {
            "name": "Repository name",
            "description": "The name of your repository.",
            "key": "repo_name",
            "type": "string",
            "value": "WinGetty",
            "position": 0,
        },
        {
            "name": "Enable registration",
            "description": "Enable this to allow users to register themselves.",
            "key": "enable_registration",
            "type": "boolean",
            "value": "False",
            "position": 1,
        },
        {
            "name": "Enable OIDC",
            "description": "Enable this to use OIDC for authentication.",
            "key": "oidc_enabled",
            "type": "boolean",
            "value": "False",
            "position": 2,
        },
        {
            "name": "OIDC Client ID",
            "description": "The client ID of your OIDC application",
            "key": "oidc_client_id",
            "type": "string",
            "value": "",
            "depends_on": "oidc_enabled",
            "position": 3,
        },
        {
            "name": "OIDC Client Secret",
            "description": "The client secret of your OIDC application",
            "key": "oidc_client_secret",
            "type": "string",
            "value": "",
            "depends_on": "oidc_enabled",
            "position": 4,
        },
        {
            "name": "OIDC Server Metadata URL",
            "description": "The server metadata URL of your OIDC application",
            "key": "oidc_server_metadata_url",
            "type": "string",
            "value": "",
            "depends_on": "oidc_enabled",
            "position": 5,
        },
        {
            "name": "Use S3 for storage",
            "description": "This will allow you to use Amazon S3 for storage.",
            "key": "use_s3",
            "type": "boolean",
            "value": "False",
            "position": 6,
        },
        {
            "name": "S3 Endpoint",
            "description": "The endpoint of the S3 bucket to use.",
            "key": "s3_endpoint",
            "type": "string",
            "value": "",
            "depends_on": "use_s3",
            "position": 7,
        },
        {
            "name": "S3 bucket",
            "description": "The name of the S3 bucket to use.",
            "key": "s3_bucket_name",
            "type": "string",
            "value": "",
            "depends_on": "use_s3",
            "position": 8,
        },
        {
            "name": "S3 Region",
            "description": "",
            "key": "s3_region",
            "type": "string",
            "value": "",
            "depends_on": "use_s3",
            "position": 9,
        },
        {
            "name": "S3 Access Key ID",
            "description": "",
            "key": "s3_access_key_id",
            "type": "string",
            "value": "",
            "depends_on": "use_s3",
            "position": 10,
        },
        {
            "name": "S3 Secret Access Key",
            "description": "",
            "key": "s3_secret_access_key",
            "type": "string",
            "value": "",
            "depends_on": "use_s3",
            "position": 11,
        },

    ]

    for setting in repository_settings:
        get_or_create(Setting, **setting)

    json_keys = {setting['key'] for setting in repository_settings}

    # Fetch all settings from the database
    all_settings = Setting.query.all()

    # Delete settings not found in the JSON configuration
    for setting in all_settings:
        if setting.key not in json_keys:
            db.session.delete(setting)

    

    

def create_all():
    """Entry function to create settings."""
    current_app.logger.info("Creating settings...")
    try:
        create_settings()
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        current_app.logger.info("Settings already exist.")
