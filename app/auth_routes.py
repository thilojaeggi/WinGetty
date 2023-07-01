from flask import Blueprint, config, render_template, redirect, url_for, request, current_app, flash
from flask_login import login_required, login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_bcrypt import Bcrypt


from app.models import User
from app import db, bcrypt
auth = Blueprint('auth', __name__)

@auth.route('/login')
def login():
    # Get if at least one user exists, if no and registration is allowed, redirecto signup and flash message
    if not User.query.first() and current_app.config['ENABLE_REGISTRATION']:
        flash('No user exists yet, please create one.', 'warning')
        return redirect(url_for('auth.signup'))
    
    return render_template('login.j2')

@auth.route('/login', methods=['POST'])
def login_post():
    # login code goes here
    email = request.form.get('emailorusername').lower()
    password = request.form.get('password')
    remember = True if request.form.get('remember') else False

    user = User.query.filter_by(email=email).first()
    if not user:
        # Try to find user by username
        user = User.query.filter_by(username=email).first()

    # check if the user actually exists
    # take the user-supplied password, hash it, and compare it to the hashed password in the database
    if not user or not bcrypt.check_password_hash(user.password, password):
        flash('Please check your login details and try again.', 'error')
        return redirect(url_for('auth.login')) # if the user doesn't exist or password is wrong, reload the page

    login_user(user, remember=remember)
    flash('Logged in successfully.', 'success')
    return redirect(url_for('ui.index'))


@auth.route('/signup')
def signup():
    if not current_app.config['ENABLE_REGISTRATION']:
        flash('Registration is disabled.', 'error')
        return redirect(url_for('ui.index'))
    return render_template('signup.j2')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth.route('/signup', methods=['POST'])
def signup_post():
    # code to validate and add user to database goes here
    email = request.form.get('email').lower()
    username = request.form.get('username').lower()
    password = request.form.get('password')
    if not current_app.config['ENABLE_REGISTRATION']:
        flash('Registration is disabled.', 'error')
        return redirect(url_for('ui.index'))

    user = User.query.filter_by(email=email).first() # if this returns a user, then the email already exists in database
    if not user:
        user = User.query.filter_by(username=username).first()

    if user: # if a user is found, we want to redirect back to signup page so user can try again
        flash('Email address already in use.', 'error')
        return redirect(url_for('auth.signup'))

    # create a new user with the form data. Hash the password so the plaintext version isn't saved.

    new_user = User(email=email, username=username, password=bcrypt.generate_password_hash(password).decode('utf-8'))

    # add the new user to the database
    db.session.add(new_user)
    db.session.commit()

    # Sign in the new user
    login_user(new_user)


    flash('Account successfully created', 'success')

    return redirect(url_for('ui.index'))