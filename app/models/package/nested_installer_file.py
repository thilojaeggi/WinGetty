from app import db

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
