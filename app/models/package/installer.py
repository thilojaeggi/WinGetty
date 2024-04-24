from flask import url_for
from app import db

class Installer(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    version_id = db.Column(db.Integer, db.ForeignKey("package_version.id"))
    package_version = db.relationship("PackageVersion", back_populates="installers")
    downloads = db.relationship("DownloadLog", backref="installer", lazy=True, cascade="all, delete-orphan")
    architecture = db.Column(db.String(50))
    installer_type = db.Column(db.String(50))
    file_name = db.Column(db.String(100), nullable=True)
    external_url = db.Column(db.String(255), nullable=True)
    installer_sha256 = db.Column(db.String(100))
    scope = db.Column(db.String(50))
    switches = db.relationship("InstallerSwitch", backref="installer", lazy=True)
    nested_installer_type = db.Column(db.String(50), nullable=True)
    nested_installer_files = db.relationship(
        "NestedInstallerFile", backref="installer", lazy=True, cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "version_id": self.version_id,
            "architecture": self.architecture,
            "installer_type": self.installer_type,
            "nested_installer_type": self.nested_installer_type,
            "nested_installer_files": [ nested_installer_file.to_dict() for nested_installer_file in self.nested_installer_files],
            "file_name": self.file_name,
            "external_url": self.external_url,
            "installer_sha256": self.installer_sha256,
            "scope": self.scope,
            "switches": [switch.to_dict() for switch in self.switches],
            "installer_url": url_for('api.download', identifier=self.package_version.package.identifier, version=self.package_version.version_code, architecture=self.architecture, scope=self.scope, _external=True, _scheme='https')
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
