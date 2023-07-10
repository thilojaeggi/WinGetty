from datetime import datetime
from app import db, bcrypt
from flask import url_for, current_app
import os
from flask_login import UserMixin

class Package(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    identifier = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    publisher = db.Column(db.String(255), nullable=False)
    versions = db.relationship('PackageVersion', backref='package', cascade='all, delete-orphan')
    download_count = db.Column(db.Integer, default=0)

    def generate_output(self):
            output = {
                "Data": {
                    "PackageIdentifier": self.identifier,
                    "Versions": self._get_version_data()
                }
            }
            return output

    def _get_version_data(self):
        version_data = []
        for version in self.versions:
            data = {
                "PackageVersion": version.version_code,
                "DefaultLocale": self._get_default_locale(version),
                "Installers": self._get_installer_data(version)
            }
            # Only append version if there's at least one installer
            if data["Installers"]:
                version_data.append(data)
        return version_data

    def _get_default_locale(self, version):
        return {
            "PackageLocale": version.package_locale,
            "Publisher": self.publisher,
            "PackageName": self.name,
            "ShortDescription": version.short_description
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
                            "InstallerUrl": url_for('api.download', identifier=self.identifier, version=version.version_code, architecture=installer.architecture, scope=installer.scope, _external=True, _scheme="https"),
                            "InstallerSha256": installer.installer_sha256,
                            "Scope": scope,
                            "InstallerSwitches": self._get_installer_switches(installer)
                        }
                        installer_data.append(data)
                else:
                    data = {
                        "Architecture": installer.architecture,
                        "InstallerType": installer.installer_type,
                        "InstallerUrl": url_for('api.download', identifier=self.identifier, version=version.version_code, architecture=installer.architecture, scope=installer.scope,  _external=True, _scheme="https"),
                        "InstallerSha256": installer.installer_sha256,
                        "Scope": installer.scope,
                        "InstallerSwitches": self._get_installer_switches(installer)
                    }
                    installer_data.append(data)
            return installer_data
    
    def _get_installer_switches(self, installer):
        switches = {}
        for switch in installer.switches:
            switches[switch.parameter] = switch.value
        return switches

    def generate_output_manifest_search(self):
        output = {
                    "PackageIdentifier": self.identifier,
                    "PackageName": self.name,
                    "Publisher": self.publisher,
                    "Versions": []
                }
            
        for version in self.versions:
            version_data = {
                "PackageVersion": version.version_code
            }
            # Only append version if there's at least one installer
            if version.installers:
                output["Versions"].append(version_data)

        return output


class PackageVersion(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    identifier = db.Column(db.String(50), db.ForeignKey('package.identifier'))
    version_code = db.Column(db.String(50))
    default_locale = db.Column(db.String(50))
    package_locale = db.Column(db.String(50))
    short_description = db.Column(db.String(50))
    date_added = db.Column(db.DateTime, default=datetime.now())
    installers = db.relationship('Installer', backref='package_version', lazy=True)

class Installer(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    version_id = db.Column(db.Integer, db.ForeignKey('package_version.id'))
    architecture = db.Column(db.String(50))
    installer_type = db.Column(db.String(50))
    file_name = db.Column(db.String(100))
    installer_sha256 = db.Column(db.String(100))
    scope = db.Column(db.String(50))
    switches = db.relationship('InstallerSwitch', backref='installer', lazy=True)

    def to_json(self):
        switches = [switch.to_json() for switch in self.switches]
        return {
            'id': self.id,
            'version_id': self.version_id,
            'architecture': self.architecture,
            'installer_type': self.installer_type,
            'file_name': self.file_name,
            'installer_sha256': self.installer_sha256,
            'scope': self.scope,
            'switches': switches
        }

        

class InstallerSwitch(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    installer_id = db.Column(db.Integer, db.ForeignKey('installer.id'))
    parameter = db.Column(db.String(50))
    value = db.Column(db.String(255))

    def to_json(self):
        return {
            'id': self.id,
            'installer_id': self.installer_id,
            'parameter': self.parameter,
            'value': self.value
        }
    
roles_permissions = db.Table(
    'roles_permissions',
    db.Column('role_id', db.Integer, db.ForeignKey('role.id'), primary_key=True),
    db.Column('permission_id', db.Integer, db.ForeignKey('permission.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(100), unique=True)
    email = db.Column(db.String(100), unique=True)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'))
    password = db.Column(db.String(100))
    role = db.relationship('Role')

    def set_password(self, password):
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        self.password = hashed_password
        

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)

    # Relationship with Permission model
    permissions = db.relationship('Permission', secondary=roles_permissions)

    def has_permission(self, name):
        # Check if the permission name is in there
        return name in [permission.name for permission in self.permissions]
        


class Permission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)