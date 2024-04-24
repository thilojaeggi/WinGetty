from datetime import datetime
from app import db

class PackageVersion(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    identifier = db.Column(db.String(50), db.ForeignKey("package.identifier"))
    version_code = db.Column(db.String(50))
    default_locale = db.Column(db.String(50))
    package_locale = db.Column(db.String(50))
    short_description = db.Column(db.String(50))
    date_added = db.Column(db.DateTime, default=datetime.now())
    installers = db.relationship("Installer", back_populates="package_version", cascade="all, delete-orphan")

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

