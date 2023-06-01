import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import hashlib

app = Flask(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] =\
        'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

with app.app_context():
    db.create_all()

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
            output["Versions"].append(version_data)

        return output


class PackageVersion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    package_identifier = db.Column(db.String(50), db.ForeignKey('package.package_identifier'))
    package_version = db.Column(db.String(50))
    default_locale = db.Column(db.String(50))
    package_locale = db.Column(db.String(50))
    short_description = db.Column(db.String(50))
    date_added = db.Column(db.DateTime, default=db.func.current_timestamp())
    installers = db.relationship('Installer', backref='package_version', lazy=True)

class Installer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    package_version_id = db.Column(db.Integer, db.ForeignKey('package_version.id'))
    architecture = db.Column(db.String(50))
    installer_type = db.Column(db.String(50))
    installer_url = db.Column(db.String(100))
    installer_sha256 = db.Column(db.String(100))
    scope = db.Column(db.String(50))


@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}


@app.route('/')
def index():
    return redirect(url_for('packages'))

@app.route('/packages')
def packages():
    packages = Package.query.all()
    return render_template('packages.j2', packages=packages)

@app.route('/package/<identifier>')
def package(identifier):
    package = Package.query.filter_by(package_identifier=identifier).first()
    return render_template('package.j2', package=package)

@app.route('/add_package', methods=['POST'])
def add_package():
    name = request.form['name']
    identifier = request.form['identifier']
    publisher = request.form['publisher']
    # Get file
    file = request.files['file']
    version = request.form['version']


    package = Package(package_identifier=identifier, package_name=name, publisher=publisher)
    if file and version:
        print("File and version found")
        file.save(os.path.join(basedir, 'static', 'packages', file.filename))
        # Get file hash
        hash = calculate_sha256(os.path.join(basedir, 'static', 'packages', file.filename))
        package_version = PackageVersion(package_version=version, package_locale="en-US", short_description=name,package_identifier=identifier)
        installer = Installer(architecture="x64", installer_type="msi", installer_url='https://thilojaeggi-psychic-tribble-jrg579jpj935p64-5000.preview.app.github.dev/static/packages/' + file.filename, installer_sha256=hash, scope="user")        
        package_version.installers.append(installer)
        package.versions.append(package_version)
    db.session.add(package)
    db.session.commit()
    return redirect(url_for('index'))
    
@app.route('/add_package_version', methods=['POST'])
def add_package_version():
    package_identifier = request.form['package_identifier']
    package_version = request.form['package_version']
    package_locale = request.form['package_locale']
    short_description = request.form['short_description']

    package = Package.query.filter_by(package_identifier=package_identifier).first()
    if package is None:
        return redirect(request.referrer)

    
    package_version = PackageVersion(package_version=package_version, package_locale=package_locale, short_description=short_description)
    package.versions.append(package_version)
    db.session.commit()
    return redirect(request.referrer)



@app.route('/add_installer', methods=['POST'])
def add_installer():
    package_identifier = request.form['package_identifier']
    package_version = request.form['package_version']
    architecture = request.form['architecture']
    installer_type = request.form['installer_type']
    file = request.files['file']
    scope = request.form['scope']

    package = Package.query.filter_by(package_identifier=package_identifier).first()
    if package is None:
        return redirect(request.referrer)
    
    package_version = PackageVersion.query.filter_by(package_version=package_version).first()
    if package_version is None:
        return redirect(request.referrer)
    
    if file:
        file.save(os.path.join(basedir, 'static', 'packages', file.filename))
        # Get file hash
        hash = calculate_sha256(os.path.join(basedir, 'static', 'packages', file.filename))
        installer = Installer(architecture=architecture, installer_type=installer_type, installer_url='https://thilojaeggi-psychic-tribble-jrg579jpj935p64-5000.preview.app.github.dev/static/packages/' + file.filename, installer_sha256=hash, scope=scope)
        package_version.installers.append(installer)
        db.session.commit()

    
    return redirect(request.referrer)
    



@app.route('/information')
def information():
    return jsonify({"Data": {"SourceIdentifier": "api.wingetty", "ServerSupportedVersions": ["1.4.0"]}})
    
@app.route('/packageManifests/<name>', methods=['GET'])
def get_package_manifest(name):
    package = Package.query.filter_by(package_identifier=name).first()
    if package is None:
        
        return jsonify({}), 204
    return jsonify(package.generate_output())



@app.route('/manifestSearch', methods=['POST'])
def manifestSearch():
    # Output all post request data
    request_data = request.get_json()
    print(request_data)

    maximum_results = request_data.get('MaximumResults')
    fetch_all_manifests = request_data.get('FetchAllManifests')
        
    query = request_data.get('Query')
    if query is not None:
        keyword = query.get('KeyWord')
        match_type = query.get('MatchType')

    inclusions = request_data.get('Inclusions')
    if inclusions is not None:
        package_match_field = inclusions[0].get('PackageMatchField')
        request_match = inclusions[0].get('RequestMatch')
        if query is None:
            keyword = request_match.get('KeyWord')
            match_type = request_match.get('MatchType')

    filters = request_data.get('Filters')
    if filters is not None:
        package_match_field_filter = filters[0].get('PackageMatchField')
        request_match_filter = filters[0].get('RequestMatch')
        keyword_filter = request_match_filter.get('KeyWord')
        match_type_filter = request_match_filter.get('MatchType')

    # Get packages by keyword and match type (exact or partial)
    packages = []
    if keyword is not None and match_type is not None:
        if match_type == "Exact":
            packages_query = Package.query.filter_by(package_identifier=keyword)
        elif match_type == "Partial" or match_type == "Substring":
            packages_query = Package.query.filter(Package.package_name.contains(keyword))
        else:
            return jsonify({}), 204

        if maximum_results is not None:
            packages_query = packages_query.limit(maximum_results)
        
        packages = packages_query.all()

    if not packages:
        return jsonify({}), 204


    output_data = []
    for package in packages:
        # If a package is added to the output without any version associated with it WinGet will error out
        if len(package.versions) > 0:
            output_data.append(package.generate_output_manifest_search())
    
    output = {"Data": output_data}
    print(output)
    return jsonify(output)

def calculate_sha256(filename):
    sha256_hash = hashlib.sha256()

    with open(filename, 'rb') as file:
        # Read the file in chunks to efficiently handle large files
        for chunk in iter(lambda: file.read(4096), b''):
            sha256_hash.update(chunk)

    return sha256_hash.hexdigest()