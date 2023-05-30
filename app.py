import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] =\
        'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class Package(db.Model):
    package_identifier = db.Column(db.String(255), unique=True, nullable=False, primary_key=True)
    package_name = db.Column(db.String(255), nullable=False)
    publisher = db.Column(db.String(255), nullable=False)
    versions = db.relationship('PackageVersion', backref='package', cascade='all, delete-orphan')

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
                    "InstallerUrl": installer.installer_url,
                    "InstallerSha256": installer.installer_sha256,
                    "Scope": installer.scope
                }
                version_data["Installers"].append(installer_data)

            output["Data"]["Versions"].append(version_data)

        return output


class PackageVersion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    package_identifier = db.Column(db.String(50), db.ForeignKey('package.package_identifier'))
    package_version = db.Column(db.String(50))
    default_locale = db.Column(db.String(50))
    package_locale = db.Column(db.String(50))
    short_description = db.Column(db.String(50))
    installers = db.relationship('Installer', backref='package_version', lazy=True)

class Installer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    package_version_id = db.Column(db.Integer, db.ForeignKey('package_version.id'))
    architecture = db.Column(db.String(50))
    installer_type = db.Column(db.String(50))
    installer_url = db.Column(db.String(100))
    installer_sha256 = db.Column(db.String(100))
    scope = db.Column(db.String(50))


@app.route('/')
def index():
    return redirect(url_for('packages'))

@app.route('/packages')
def packages():
    packages = Package.query.all()
    return render_template('packages.html', packages=packages)

@app.route('/package/<identifier>')
def package(identifier):
    package = Package.query.filter_by(package_identifier=identifier).first()
    return render_template('package.html', package=package)

@app.route('/add_package', methods=['POST'])
def add_package():
    name = request.form['name']
    identifier = request.form['identifier']
    publisher = request.form['publisher']

    package = Package(package_identifier=identifier, package_name=name, publisher=publisher)
    db.session.add(package)
    db.session.commit()
    return redirect(url_for('index'))
    



@app.route('/information')
def information():
    return jsonify({"Data": {"SourceIdentifier": "api.soos", "ServerSupportedVersions": ["1.4.0"]}})
    
@app.route('/packageManifests/<name>', methods=['GET'])
def get_package_manifest(name):
    package = Package.query.filter_by(package_identifier=name).first()
    if package is None:
        
        return jsonify({}), 204
    return jsonify(package.generate_output())



@app.route('/manifestSearch', methods=['POST'])
def manifestSearch():
    return jsonify({
    "Data": [
        {
            "PackageIdentifier": "Test",
            "PackageName": "test",
            "Publisher": "test",
            "Versions": [
                {
                    "PackageVersion": "1.0.0"
                }
            ]
        }
    ]
})

