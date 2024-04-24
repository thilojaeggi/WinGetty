from app import db

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
