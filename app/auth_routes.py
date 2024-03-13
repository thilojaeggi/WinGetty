from flask import Blueprint, config, render_template, redirect, url_for, request, current_app, flash
from flask_login import login_required, login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_bcrypt import Bcrypt

from app.models import Role, Setting, User
from app import db, bcrypt, permissions
auth = Blueprint('auth', __name__)

@auth.route('/login')
def login():
    # Get if at least one user exists, if no and registration is allowed, redirecto signup and flash message
    if not User.query.first():
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
    # Check if any user exists in the database.
    user_exists = User.query.first() is not None
    
    # If users already exist and registration is disabled, redirect to login with a flash message.
    if user_exists and not Setting.get("ENABLE_REGISTRATION").get_value():
        flash('Registration is not allowed. Please contact your administrator.', 'warning')
        return redirect(url_for('auth.login'))
    
    # If no users exist or registration is enabled, render the signup template.
    return render_template('signup.j2')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth.route('/signup', methods=['POST'])
def signup_post():
    # Before processing the form, check if registration is enabled and users exist
    if User.query.first() and not Setting.get("ENABLE_REGISTRATION").get_value():
        flash('Registration is disabled.', 'error')
        return redirect(url_for('auth.login'))

    # Proceed with form processing
    email = request.form.get('email').lower()
    username = request.form.get('username').lower()
    password = request.form.get('password')

    # Check if the email is already in use
    if User.query.filter_by(email=email).first():
        flash('Email address already in use.', 'error')
        return redirect(url_for('auth.signup'))

    # Check if the username is already in use
    if User.query.filter_by(username=username).first():
        flash('Username already in use.', 'error')
        return redirect(url_for('auth.signup'))

    # Assign role based on whether it's the first user
    if not User.query.first():
        role = Role.query.filter_by(name='admin').first()
    else:
        role = Role.query.filter_by(name='user').first()

    # Create a new User instance
    new_user = User(email=email, username=username, role=role)
    new_user.set_password(password)

    # Add the new user to the database
    db.session.add(new_user)
    db.session.commit()

    # Automatically log in the new user
    login_user(new_user)

    flash('Account successfully created', 'success')
    return redirect(url_for('ui.index'))