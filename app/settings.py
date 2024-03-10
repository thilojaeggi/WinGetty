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
            "value": "",
        },
        {
            "name": "Use S3 for storage",
            "description": "This will allow you to use Amazon S3 for storage.",
            "key": "use_s3",
            "type": "boolean",
            "value": "False",
        },
        {
            "name": "S3 bucket",
            "description": "The name of the S3 bucket to use.",
            "key": "bucket_name",
            "type": "string",
            "value": "",
            "depends_on": "use_s3",
        },
        {
            "name": "Enable uplink",
            "description": "Enable this to use a public WinGet repository as an uplink.",
            "key": "enable_uplink",
            "type": "boolean",
            "value": "False",
        },
        {
            "name": "Uplink URL",
            "description": "The URL of a public WinGet repository to use as an uplink.",
            "key": "uplink_url",
            "type": "string",
            "value": "",
            "depends_on": "enable_uplink",
        },
    ]

    for setting in repository_settings:
        get_or_create(Setting, **setting)


def create_all():
    """Entry function to create settings."""
    current_app.logger.info("Creating settings...")
    try:
        create_settings()
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        current_app.logger.info("Settings already exist.")
