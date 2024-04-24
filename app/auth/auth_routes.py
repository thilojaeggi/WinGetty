import os
from urllib.parse import urlencode
from flask import Blueprint, config, render_template, redirect, session, url_for, request, current_app, flash
from flask_login import login_required, login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_bcrypt import Bcrypt

from app.models import Role, Setting, User
from app import db, bcrypt, permissions
from app import oauth



auth = Blueprint('auth', __name__, template_folder='templates')

import requests


@auth.route('/login/oidc')
def oidc_login():
    if not Setting.get("OIDC_ENABLED").get_value():
        flash('OIDC login is not enabled.', 'error')
        return redirect(url_for('auth.login'))
    oidc_provider = current_app.oidc_provider
    # Generate a nonce and store it in the session
    nonce = os.urandom(16).hex()
    session['oidc_nonce'] = nonce
    # if testing use http, else use https
    # if flask is running in testing mode, use http
    if current_app.debug:
        redirect_uri = url_for('auth.oidc_authorize', _external=True)
    else:
        redirect_uri = url_for('auth.oidc_authorize', _external=True, _scheme='https')
    # Pass the nonce in the authorization request
    return oidc_provider.authorize_redirect(redirect_uri, nonce=nonce)

@auth.route('/authorize/oidc')
def oidc_authorize():
    if not Setting.get("OIDC_ENABLED").get_value():
        flash('OIDC login is not enabled.', 'error')
        return redirect(url_for('auth.login'))
    
    oidc_provider = current_app.oidc_provider
    token = oidc_provider.authorize_access_token()
    # Retrieve the nonce from the session
    nonce = session.pop('oidc_nonce', None)
    try:
        # Use the nonce to validate the ID token
        user_info = oidc_provider.parse_id_token(token, nonce)

        email = user_info.get('email')
        username = user_info.get('preferred_username')

        # Check that email is verified
        if not user_info.get('email_verified'):
            flash('Email address not verified.', 'error')
            return redirect(url_for('auth.login'))
        

        if not email:
            flash('No email address found in SSO response.', 'error')
            return redirect(url_for('auth.login'))
        if not username:
            username = email.split('@')[0]

        flash('Logged in successfully via SSO.', 'success')
        user = User.query.filter_by(email=email).first()
        if not user:
            password = os.urandom(16).hex()
            user = User(email=email, username=username, role=Role.query.filter_by(name='viewer').first())
            user.set_password(password)
            session.pop('_flashes', None)
            flash('User created from SSO login.', 'info')
            db.session.add(user)
            db.session.commit()
        login_user(user)
        session['id_token'] = token.get('id_token')
        session['IS_OIDC_LOGIN'] = True
        return redirect(url_for('ui.packages'))
    except Exception as e:
        flash('Failed to validate SSO login.', 'error')
        return redirect(url_for('auth.login'))

@auth.route('/login')
def login():
    # Get if at least one user exists, if no and registration is allowed, redirecto signup and flash message
    if not User.query.first():
        flash('No user exists yet, please create one.', 'warning')
        return redirect(url_for('auth.signup'))
    return render_template('auth/login.j2')

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
    return redirect(url_for('ui.packages'))


@auth.route('/signup')
def signup():
    # Check if any user exists in the database.
    user_exists = User.query.first() is not None
    
    # If users already exist and registration is disabled, redirect to login with a flash message.
    if user_exists and not Setting.get("ENABLE_REGISTRATION").get_value():
        flash('Registration is disabled.', 'error')
        return redirect(url_for('auth.login'))
    
    # If no users exist or registration is enabled, render the signup template.
    return render_template('auth/signup.j2')



@auth.route('/logout')
@login_required
def logout():
    print(session.get('IS_OIDC_LOGIN'))
    if Setting.get("OIDC_ENABLED").get_value() and session.get('IS_OIDC_LOGIN'):
        id_token = session.pop('id_token', None)
        if not id_token:
            flash("Missing ID token, unable to securely logout.", "error")
            return redirect(url_for('auth.login'))
        try:
            oidc_metadata_url = Setting.get("OIDC_SERVER_METADATA_URL").get_value()
            response = requests.get(oidc_metadata_url)
            if response.ok:
                print(response.json())
                oidc_config = response.json()
                end_session_endpoint = oidc_config.get('end_session_endpoint')
                if end_session_endpoint:
                    if current_app.debug:
                        redirect_uri = url_for('ui.index', _external=True, _scheme='http')
                    else:
                        redirect_uri = url_for('ui.index', _external=True, _scheme='https')
                    
                    print(redirect_uri)
                    
                    params = {
                        'id_token_hint': id_token,
                        'post_logout_redirect_uri': redirect_uri
                    }
                    full_logout_url = f"{end_session_endpoint}?{urlencode(params)}"
                    logout_user()
                    flash('Logged out successfully using SSO.', 'success')
                    return redirect(full_logout_url)
                else:
                    flash("SSO logout endpoint not found.", "error")
            else:
                flash("Failed to fetch SSO configuration.", "error")
        except Exception as e:
            flash(f"Error during SSO logout: {str(e)}", "error")
    logout_user()
    flash('Logged out successfully.', 'success')
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
    return redirect(url_for('ui.packages'))


    