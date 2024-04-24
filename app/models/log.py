from app import db
from datetime import datetime

class Log(db.Model):
    __tablename__ = "log"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    type = db.Column(db.String(50), nullable=False)
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(255))
    date = db.Column(db.DateTime, default=datetime.now())
    __mapper_args__ = {"polymorphic_on": type, "polymorphic_identity": "log"}

    def to_dict(self):
        return {
            "id": self.id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "date": self.date,
        }

class DownloadLog(Log):
    __tablename__ = "download_log"
    id = db.Column(db.Integer, db.ForeignKey('log.id'), primary_key=True)
    installer_id = db.Column(db.Integer, db.ForeignKey("installer.id"))
    __mapper_args__ = {"polymorphic_identity": "download_log"}


    def to_dict(self):
        data = super().to_dict()
        data.update(
            {
                "installer_id": self.installer_id,
                "installer": self.installer.to_dict(),
            }
        )
        return data
    
class AccessLog(Log):
    __tablename__ = "access_log"
    id = db.Column(db.Integer, db.ForeignKey('log.id'), primary_key=True)  # Ensures shared primary key
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref="access_logs")
    action = db.Column(db.String(255))
    __mapper_args__ = {"polymorphic_identity": "access_log"}


    def to_dict(self):
        data = super().to_dict()
        data.update(
            {
                "user_id": self.user_id,
                "user": self.user.username,
                "action": self.action,
            }
        )
        return data
