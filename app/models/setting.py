from flask import current_app
from app import db
import json

class Setting(db.Model):
    key = db.Column(db.String(50), unique=True, primary_key=True)
    name = db.Column(db.String(50), unique=True)
    description = db.Column(db.String(255))
    type = db.Column(db.Enum("string", "integer", "boolean", "float", "json", name="setting_type_enum"))
    value = db.Column(db.String(255))
    position = db.Column(db.Integer)
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
