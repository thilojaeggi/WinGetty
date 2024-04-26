
from flask import url_for
from looseversion import LooseVersion
from app import db, bcrypt
from semver import VersionInfo, parse_version_info

from packaging.version import parse as parse_version

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
            "download_count": self.download_count,
            "versions": sorted(
                [version.to_dict() for version in self.versions],
                key=lambda x: LooseVersion(x["version_code"]),
                reverse=True,
            ),
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

