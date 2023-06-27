from flask import Blueprint, config, render_template, redirect, url_for, request, current_app
from flask_login import login_required, login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash


from app.models import User
from app import db
auth = Blueprint('auth', __name__)

@auth.route('/login')
def login():
    # Get if at least one user exists, if no and registration is allowed, redirecto signup and flash message
    if not User.query.first() and not current_app.config['DISABLE_REGISTRATION']:
        return redirect(url_for('auth.signup'))
    
    return render_template('login.j2')

@auth.route('/login', methods=['POST'])
def login_post():
    # login code goes here
    email = request.form.get('email')
    password = request.form.get('password')
    remember = True if request.form.get('remember') else False

    user = User.query.filter_by(email=email).first()

    # check if the user actually exists
    # take the user-supplied password, hash it, and compare it to the hashed password in the database
    if not user or not check_password_hash(user.password, password):
        return redirect(url_for('auth.login')) # if the user doesn't exist or password is wrong, reload the page

    login_user(user, remember=remember)
    return redirect(url_for('ui.index'))


@auth.route('/signup')
def signup():
    if current_app.config['DISABLE_REGISTRATION']:
        return redirect(url_for('ui.index'))
    return render_template('register.j2')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth.route('/signup', methods=['POST'])
def signup_post():
    # code to validate and add user to database goes here
    email = request.form.get('email')
    name = request.form.get('name')
    password = request.form.get('password')
    if current_app.config['DISABLE_REGISTRATION']:
        return redirect(url_for('ui.index'))

    user = User.query.filter_by(email=email).first() # if this returns a user, then the email already exists in database

    if user: # if a user is found, we want to redirect back to signup page so user can try again
        return redirect(url_for('auth.signup'))

    # create a new user with the form data. Hash the password so the plaintext version isn't saved.
    new_user = User(email=email, name=name, password=generate_password_hash(password, method='sha256'))

    # add the new user to the database
    db.session.add(new_user)
    db.session.commit()

    return redirect(url_for('auth.login'))