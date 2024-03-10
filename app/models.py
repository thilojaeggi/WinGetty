import dataclasses
from datetime import datetime
import json
from app import db, bcrypt
from flask import url_for, current_app
import os
from flask_login import UserMixin


@dataclasses.dataclass
class Package(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    identifier = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    publisher = db.Column(db.String(255), nullable=False)
    versions = db.relationship(
        "PackageVersion", backref="package", cascade="all, delete-orphan"
    )
    download_count = db.Column(db.Integer, default=0)

    def to_dict(self):
        return {
            "id": self.id,
            "identifier": self.identifier,
            "name": self.name,
            "publisher": self.publisher,
            "versions": [version.to_dict() for version in self.versions],
        }

    def generate_output(self):
        output = {
            "Data": {
                "PackageIdentifier": self.identifier,
                "Versions": self._get_version_data(),
            }
        }
        return output

    def _get_version_data(self):
        version_data = []
        for version in self.versions:
            data = {
                "PackageVersion": version.version_code,
                "DefaultLocale": self._get_default_locale(version),
                "Installers": self._get_installer_data(version),
            }
            # Only append version if there's at least one installer
            if data[ "Installers"]:
                version_data.append(data)
        return version_data

    def _get_default_locale(self, version):
        return {
            "PackageLocale": version.package_locale,
            "Publisher": self.publisher,
            "PackageName": self.name,
            "ShortDescription": version.short_description,
        }

    def _get_installer_data(self, version):
        installer_data = []
        for installer in version.installers:
            if installer.scope == "both":
                # If installer is for both user and machine, create two entries for each scope (user and machine) but use it with download url
                for scope in ["user", "machine"]:
                    data = {
                        "Architecture": installer.architecture,
                        "InstallerType": installer.installer_type,
                        "InstallerUrl": url_for(
                            "api.download",
                            identifier=self.identifier,
                            version=version.version_code,
                            architecture=installer.architecture,
                            scope=installer.scope,
                            _external=True,
                            _scheme="https",
                        ),
                        "InstallerSha256": installer.installer_sha256,
                        "Scope": scope,
                        "InstallerSwitches": self._get_installer_switches(installer),
                    }
                    if installer.installer_type == "zip":
                        data["NestedInstallerType"] = installer.nested_installer_type
                        data["NestedInstallerFiles"] = self._get_nested_installer_data(
                            installer
                        )
                    installer_data.append(data)
            else:
                data = {
                    "Architecture": installer.architecture,
                    "InstallerType": installer.installer_type,
                    "InstallerUrl": url_for(
                        "api.download",
                        identifier=self.identifier,
                        version=version.version_code,
                        architecture=installer.architecture,
                        scope=installer.scope,
                        _external=True,
                        _scheme="https",
                    ),
                    "InstallerSha256": installer.installer_sha256,
                    "Scope": installer.scope,
                    "InstallerSwitches": self._get_installer_switches(installer),
                }
                if installer.installer_type == "zip":
                    data["NestedInstallerType"] = installer.nested_installer_type
                    data["NestedInstallerFiles"] = self._get_nested_installer_data(
                        installer
                    )
                installer_data.append(data)
        return installer_data

    def _get_installer_switches(self, installer):
        switches = {}
        for switch in installer.switches:
            switches[switch.parameter] = switch.value
        return switches

    def _get_nested_installer_data(self, installer):
        nested_installer_data = []
        for nested_installer_file in installer.nested_installer_files:
            data = {
                "RelativeFilePath": nested_installer_file.relative_file_path,
                "PortableCommandAlias": nested_installer_file.portable_command_alias,
            }
            nested_installer_data.append(data)
        return nested_installer_data

    def generate_output_manifest_search(self):
        output = {
            "PackageIdentifier": self.identifier,
            "PackageName": self.name,
            "Publisher": self.publisher,
            "Versions": [],
        }

        for version in self.versions:
            version_data = {"PackageVersion": version.version_code}
            # Only append version if there's at least one installer
            if version.installers:
                output["Versions"].append(version_data)

        return output


class PackageVersion(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    identifier = db.Column(db.String(50), db.ForeignKey("package.identifier"))
    version_code = db.Column(db.String(50))
    default_locale = db.Column(db.String(50))
    package_locale = db.Column(db.String(50))
    short_description = db.Column(db.String(50))
    date_added = db.Column(db.DateTime, default=datetime.now())
    installers = db.relationship("Installer", backref="package_version", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "identifier": self.identifier,
            "version_code": self.version_code,
            "default_locale": self.default_locale,
            "package_locale": self.package_locale,
            "short_description": self.short_description,
            "date_added": self.date_added,
            "installers": [installer.to_dict() for installer in self.installers],
            "package_id": self.package.id,
        }


class Installer(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    version_id = db.Column(db.Integer, db.ForeignKey("package_version.id"))
    architecture = db.Column(db.String(50))
    installer_type = db.Column(db.String(50))
    file_name = db.Column(db.String(100), nullable=True)
    external_url = db.Column(db.String(255), nullable=True)
    installer_sha256 = db.Column(db.String(100))
    scope = db.Column(db.String(50))
    switches = db.relationship("InstallerSwitch", backref="installer", lazy=True)
    nested_installer_type = db.Column(db.String(50), nullable=True)
    nested_installer_files = db.relationship(
        "NestedInstallerFile", backref="installer", lazy=True
    )

    def to_dict(self):
        return {
            "id": self.id,
            "version_id": self.version_id,
            "architecture": self.architecture,
            "installer_type": self.installer_type,
            "file_name": self.file_name,
            "external_url": self.external_url,
            "installer_sha256": self.installer_sha256,
            "scope": self.scope,
            "switches": [switch.to_dict() for switch in self.switches],
        }

    def to_json(self):
        switches = [switch.to_json() for switch in self.switches]
        return {
            "id": self.id,
            "version_id": self.version_id,
            "architecture": self.architecture,
            "installer_type": self.installer_type,
            "file_name": self.file_name,
            "installer_sha256": self.installer_sha256,
            "scope": self.scope,
            "switches": switches,
        }


class NestedInstallerFile(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    installer_id = db.Column(db.Integer, db.ForeignKey("installer.id"))
    relative_file_path = db.Column(db.String(255))
    portable_command_alias = db.Column(db.String(100))

    def to_dict(self):
        return {
            "id": self.id,
            "installer_id": self.installer_id,
            "relative_file_path": self.relative_file_path,
            "portable_command_alias": self.portable_command_alias,
        }

    def to_json(self):
        return {
            "id": self.id,
            "installer_id": self.installer_id,
            "relative_file_path": self.relative_file_path,
            "portable_command_alias": self.portable_command_alias,
        }


class InstallerSwitch(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    installer_id = db.Column(db.Integer, db.ForeignKey("installer.id"))
    parameter = db.Column(db.String(50))
    value = db.Column(db.String(255))

    def to_dict(self):
        return {
            "id": self.id,
            "installer_id": self.installer_id,
            "parameter": self.parameter,
            "value": self.value,
        }

    def to_json(self):
        return {
            "id": self.id,
            "installer_id": self.installer_id,
            "parameter": self.parameter,
            "value": self.value,
        }


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(100), unique=True)
    email = db.Column(db.String(100), unique=True)
    role_id = db.Column(db.Integer, db.ForeignKey("role.id"))
    password = db.Column(db.String(100))
    role = db.relationship("Role", back_populates="users")

    def set_password(self, password):
        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")
        self.password = hashed_password

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role.name,
            "permissions": [permission.name for permission in self.role.permissions],
        }


roles_permissions = db.Table(
    "roles_permissions",
    db.Column("role_id", db.Integer, db.ForeignKey("role.id"), primary_key=True),
    db.Column(
        "permission_id", db.Integer, db.ForeignKey("permission.id"), primary_key=True
    ),
)


class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)

    # Relationship with Permission model
    permissions = db.relationship("Permission", secondary=roles_permissions)
    users = db.relationship("User", back_populates="role")

    def has_permission(self, name):
        # Check if the permission name is in there
        return name in [permission.name for permission in self.permissions]

    def user_count(self):
        return len(self.users)


class Permission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)


class Setting(db.Model):
    key = db.Column(db.String(50), unique=True, primary_key=True)
    name = db.Column(db.String(50), unique=True)
    description = db.Column(db.String(255))
    type = db.Column(db.Enum("string", "integer", "boolean", "float", "json"))
    value = db.Column(db.String(255))
    depends_on = db.Column(db.String(50), db.ForeignKey("setting.key"))
    dependent_setting = db.relationship(
        "Setting", remote_side=[key], backref="dependent_on"
    )

    def __repr__(self):
        return f"{self.name} : {self.value}"
    

    def set_value(self, value):
        # Check that the value is of the correct type
        if self.type == "integer":
            self.value = int(value)
        elif self.type == "boolean":
            self.value = "true" if value else "false"
        elif self.type == "float":
            self.value = float(value)
        elif self.type == "json":
            self.value = json.dumps(value)
        else:
            self.value = value

    def get_value(self):
        # Convert self.key to uppercase for case-insensitive comparison
        upper_key = self.key.upper()

        # First, check if the setting is defined in app.config in a case-insensitive manner
        if upper_key in (k.upper() for k in current_app.config):
            app_config_value = current_app.config[upper_key]
            # Return the app config value, converting it to the correct type
            if self.type == "integer":
                return int(app_config_value)
            elif self.type == "boolean":
                return app_config_value.lower() == "true" if isinstance(app_config_value, str) else bool(app_config_value)
            elif self.type == "float":
                return float(app_config_value)
            elif self.type == "json":
                return json.loads(app_config_value) if isinstance(app_config_value, str) else app_config_value
            else:
                return app_config_value
        else:
            # Otherwise, return the value from the database, as before
            if self.type == "integer":
                return int(self.value)
            elif self.type == "boolean":
                return self.value.lower() == "true"
            elif self.type == "float":
                return float(self.value)
            elif self.type == "json":
                return json.loads(self.value)
            else:
                return self.value

    def get(key):
        key = key.lower()
        return Setting.query.filter_by(key=key).first()

    def to_dict(self):
        upper_key = self.key.upper()
        return {
            "name": self.name,
            "description": self.description,
            "key": self.key,
            "type": self.type,
            "value": self.get_value(),
            "depends_on": self.depends_on,
            "is_env": upper_key in (k.upper() for k in current_app.config)
        }
