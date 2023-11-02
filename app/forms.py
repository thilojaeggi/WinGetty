from flask import current_app
from flask_wtf import FlaskForm
from wtforms import (StringField, TextAreaField, IntegerField, BooleanField,
                     RadioField, FileField, SelectField)
from wtforms.validators import InputRequired, Length, Optional    
from flask_wtf.file import FileField, FileAllowed, FileRequired
import wtforms
from wtforms import Form, StringField, SelectField, validators, ValidationError

class RequiredIf(object):

    def __init__(self, **kwargs):
        self.conditions = kwargs

    def __call__(self, form, field):
        # NOTE! you can create here any custom processing
        current_value = form.data.get(field.name)
        if current_value == 'None':
            for condition_field, reserved_value in self.conditions.items():
                dependent_value = form.data.get(condition_field)
                if condition_field not in form.data:
                    continue
                elif dependent_value == reserved_value:
                    # just an example of error
                    raise Exception(
                        'Invalid value of field "%s". Field is required when %s==%s' % (
                            field.name,
                            condition_field,
                            dependent_value
                        ))

class RequiredIfFile(object):
    def __init__(self, field):
        self.field = field

    def __call__(self, form, field):
        if isinstance(form._fields.get(self.field), FileField):
            if field.data is None:
                raise ValidationError('This field is required.')


class FileOrURLRequired:
    def __init__(self, url_field, file_required=True):
        self.url_field = url_field
        self.file_required = file_required

    def __call__(self, form, field):
        if self.file_required and not field.data and not form[self.url_field].data:
            raise ValidationError('Either file must be uploaded or URL must be provided.')


class RequiredIfFileOrURL:
    def __init__(self, file_field, url_field):
        self.file_field = file_field
        self.url_field = url_field

    def __call__(self, form, field):
        if (not form[self.file_field].data and not form[self.url_field].data):
            return  # If neither file nor url is provided, make the field optional
        elif (form[self.file_field].data or form[self.url_field].data) and not field.data:
            raise ValidationError('This field is required if either file is uploaded or URL is provided.')



# this is type of form to just to escape csrf protection
class AddInstallerFormFields(FlaskForm):
    class Meta:
        csrf = False


    def __init__(self, file_required=True, *args, **kwargs):
        super(AddInstallerFormFields, self).__init__(*args, **kwargs)
        if file_required:
            self.file.validators.append(FileOrURLRequired(url_field="url", file_required=True))
            self.url.validators.append(Optional())  # Setting the URL field to optional when file is required
        else:
            self.file.validators.append(Optional())
            self.url.validators.append(Optional())  # Both fields are optional when file_required is False

        if current_app.config['USE_S3'] and file_required:
            self.is_aws.validators.append(InputRequired())




    file = FileField('File', validators=[FileAllowed(['exe', 'zip', 'msi', 'msix', 'appx'])])


    url = StringField('URL', validators=[Optional()])

    is_aws = BooleanField('Is AWS', validators=[Optional()])

    version = StringField('Version',validators=[RequiredIfFileOrURL('file', 'url')])
    

    architecture = SelectField('Architecture', choices=[('x86', 'x86'), ('x64', 'x64'), ('arm', 'arm'), ('arm64', 'arm64')],validators=[RequiredIfFileOrURL('file', 'url')])
    
    installer_type = SelectField('Type', choices=[('exe', 'exe'), ('msi', 'msi'), ('msix', 'msix'), ('appx', 'appx'), ('zip', 'zip'), ('inno', 'inno'), ('nullsoft', 'nullsoft'), ('wix', 'wix'), ('burn', 'burn'), ('pwa', 'pwa'), ('msstore', 'msstore')],validators=[RequiredIfFileOrURL('file', 'url')])
    
    installer_scope = SelectField('Scope', choices=[('user', 'user'), ('machine', 'machine'), ('both', 'both')],validators=[RequiredIfFileOrURL('file', 'url')])
    
    nestedinstallertype = SelectField('Nested Installer Type', choices=[('msi', 'msi'), ('msix', 'msix'), ('appx', 'appx'), ('exe', 'exe'), ('inno', 'inno'),('nullsoft', 'nullsoft'), ('wix', 'wix'), ('burn', 'burn'), ('portable','portable')], validators=[
        RequiredIf(installer_type='zip')
        ])
    
    nestedinstallerpath = StringField('Nested Installer Path', validators=[
        RequiredIf(installer_type='zip')
        ])
    
class AddInstallerFormFieldsWithoutFile(AddInstallerFormFields):
    def __init__(self, *args, **kwargs):
        super(AddInstallerFormFieldsWithoutFile, self).__init__(*args, **kwargs, file_required=False)

class AddPackageForm(FlaskForm):
    name = StringField('Name', validators=[
    InputRequired(),
    Length(min=1, max=50)
    ])

    publisher = StringField('Publisher', validators=[
    InputRequired(),
    Length(min=1, max=50)
    ])

    identifier = StringField('Identifier', validators=[
    InputRequired(),
    Length(min=1, max=101)
    ])

    # Include the AddInstallerFormFields without csrf protection
    installer = wtforms.FormField(AddInstallerFormFieldsWithoutFile)


class AddInstallerForm(FlaskForm):
    # Include the AddInstallerFormFields without csrf protection
    installer = wtforms.FormField(AddInstallerFormFields)

class AddVersionForm(FlaskForm):


    installer = wtforms.FormField(AddInstallerFormFieldsWithoutFile)





