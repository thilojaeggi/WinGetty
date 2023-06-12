from app import db
from flask import url_for, current_app

class Package(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    package_identifier = db.Column(db.String(255), unique=True, nullable=False)
    package_name = db.Column(db.String(255), nullable=False)
    publisher = db.Column(db.String(255), nullable=False)
    versions = db.relationship('PackageVersion', backref='package', cascade='all, delete-orphan')
    download_count = db.Column(db.Integer, default=0)

    def generate_output(self):
        output = {
            "Data": {
                "PackageIdentifier": self.package_identifier,
                "Versions": []
            }
        }

        for version in self.versions:
            version_data = {
                "PackageVersion": version.package_version,
                "DefaultLocale": {
                    "PackageLocale": version.package_locale,
                    "Publisher": self.publisher,
                    "PackageName": self.package_name,
                    "ShortDescription": version.short_description
                },
                "Installers": []
            }

            for installer in version.installers:
                installer_data = {
                    "Architecture": installer.architecture,
                    "InstallerType": installer.installer_type,
                    "InstallerUrl": url_for('api.download', identifier=self.package_identifier, version=version.package_version, architecture=installer.architecture, _external=True).replace("http://localhost", "https://thilojaeggi-psychic-tribble-jrg579jpj935p64-5000.preview.app.github.dev"),
                    "InstallerSha256": installer.installer_sha256,
                    "Scope": installer.scope
                }
                version_data["Installers"].append(installer_data)
            # Only append version if there's at least one installer
            if version_data["Installers"]:
                output["Data"]["Versions"].append(version_data)

        return output


    def generate_output_manifest_search(self):
        output = {
                    "PackageIdentifier": self.package_identifier,
                    "PackageName": self.package_name,
                    "Publisher": self.publisher,
                    "Versions": []
                }
            
        for version in self.versions:
            version_data = {
                "PackageVersion": version.package_version
            }
            # Only append version if there's at least one installer
            if version.installers:
                output["Versions"].append(version_data)

        return output


class PackageVersion(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    package_identifier = db.Column(db.String(50), db.ForeignKey('package.package_identifier'))
    package_version = db.Column(db.String(50))
    default_locale = db.Column(db.String(50))
    package_locale = db.Column(db.String(50))
    short_description = db.Column(db.String(50))
    date_added = db.Column(db.DateTime, default=db.func.current_timestamp())
    installers = db.relationship('Installer', backref='package_version', lazy=True)

class Installer(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    package_version_id = db.Column(db.Integer, db.ForeignKey('package_version.id'))
    architecture = db.Column(db.String(50))
    installer_type = db.Column(db.String(50))
    
    file_name = db.Column(db.String(100))
    installer_sha256 = db.Column(db.String(100))
    scope = db.Column(db.String(50))