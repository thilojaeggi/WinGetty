import logging
import os
import threading
import time
from wsgiref.simple_server import make_server
import pytest
from flask import request, url_for, session
import requests
from app import create_app, db
from app.models import User
from flask_migrate import downgrade, upgrade
from config import Config
from multiprocessing import Process

from tests.test_database import DATABASE_URIS
logging.basicConfig(level=logging.DEBUG)

@pytest.fixture(params=DATABASE_URIS)
def app(monkeypatch, request):
    monkeypatch.setenv('WINGETTY_SQLALCHEMY_DATABASE_URI', request.param)
    app = create_app()
    app.config.update(SERVER_NAME='localhost:5001', TESTING=True)
    with app.app_context():

        # Apply migrations to set up the databases
        os.chdir(os.path.dirname(os.path.dirname(__file__)))
        upgrade()
        os.chdir(os.path.dirname(__file__))
        # Create permissions and settings
        from app.permissions import create_all
        create_all()
        from app.settings import create_all
        create_all()

        yield app

        # Teardown: revert migrations and drop all tables
        os.chdir(os.path.dirname(os.path.dirname(__file__)))
        #downgrade()
        os.chdir(os.path.dirname(__file__))

        db.session.commit()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture(scope="session")
def run_server():
    os.environ['WINGETTY_SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
    # print environment variables
    os.environ['WINGETTY_OIDC_ENABLED'] = 'True'
    os.environ['WINGETTY_OIDC_CLIENT_ID'] = os.environ.get('OIDC_CLIENT_ID')
    os.environ['WINGETTY_OIDC_CLIENT_SECRET'] = os.environ.get('OIDC_CLIENT_SECRET')
    os.environ['WINGETTY_OIDC_SERVER_METADATA_URL'] = os.environ.get('OIDC_SERVER_METADATA_URL')
    os.environ['WINGETTY_OIDC_REDIRECT_URI'] = 'http://localhost:5001/authorize/oidc'

    app = create_app()
    app.config.update(
        SERVER_NAME='localhost:5001',
        TESTING=True,
        DEBUG=False,
        OIDC_ENABLED=True,
        OIDC_CLIENT_ID=os.environ.get('OIDC_CLIENT_ID'),
        OIDC_CLIENT_SECRET=os.environ.get('OIDC_CLIENT_SECRET'),
        OIDC_SERVER_METADATA_URL=os.environ.get('OIDC_SERVER_METADATA_URL'),
        OIDC_REDIRECT_URI='http://localhost:5001/authorize/oidc',
    )
    with app.app_context():
        # Apply migrations to set up the databases
        os.chdir(os.path.dirname(os.path.dirname(__file__)))
        upgrade()
        os.chdir(os.path.dirname(__file__))
        # Create permissions and settings
        from app.permissions import create_all
        create_all()
        from app.settings import create_all
        create_all()


    server = make_server('localhost', 5001, app)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    yield app
    server.shutdown()
    thread.join()



# Example test that uses these fixtures
@pytest.mark.usefixtures('run_server')
def test_server_response(client):
    logging.debug("Requesting the main index route")
    response = requests.get('http://localhost:5001/')
    logging.debug("Received response with status code: %s", response.status_code)
    print(response.text)
    assert response.status_code == 200

    


@pytest.mark.order(1)
@pytest.mark.parametrize("client", DATABASE_URIS, indirect=True)
def test_signup_get(client):
    signup_url = url_for('auth.signup', _external=True)
    response = client.get(signup_url, follow_redirects=True)
    assert response.status_code == 200
    assert b'Sign up' in response.data

@pytest.mark.order(2)
@pytest.mark.parametrize("client", DATABASE_URIS, indirect=True)
def test_signup_post(client):
    signup_url = url_for('auth.signup_post', _external=True)
    # Form data to be sent with the request
    user_data = {
        'email': 'test@test.com',
        'username': 'testuser',
        'password': 'testpass'
    }
    # Send a POST request with the form data
    response = client.post(signup_url, data=user_data, follow_redirects=True)
    # output the response data
    # Get user data from the database
    from app.models import User
    user = User.query.filter_by(email=user_data['email']).first()
    # Check if the user was created successfully
    assert user is not None
    assert user.email == user_data['email']

# Check that a second user cannot be created
@pytest.mark.order(3)
@pytest.mark.parametrize("client", DATABASE_URIS, indirect=True)
def test_signup_post_duplicate(client):
    signup_url = url_for('auth.signup_post', _external=True)
    # Form data to be sent with the request
    user_data = {
        'email': 'secondtest@test.com',
        'username': 'seconduser',
        'password': 'testpass'
    }
    # Send a POST request with the form data
    response = client.post(signup_url, data=user_data)
    # Should be redirected to the login page as registration is disabled
    assert response.status_code == 302
    # Check that the user was not created
    from app.models import User
    user = User.query.filter_by(email=user_data['email']).first()
    # Check that one user exists (the first user created in the previous test)
    count = User.query.count()
    assert count == 1

    assert user is None
    


@pytest.mark.order(3)
@pytest.mark.parametrize("client", DATABASE_URIS, indirect=True)
def test_login_get(client):
    """Test that the login page can be accessed."""
    # Use url_for to generate the URL for the login route
    login_url = url_for('auth.login', _external=True, follow_redirects=True)
    response = client.get(login_url)
    assert response.status_code == 200
    assert b'Log in' in response.data  # Assuming 'Login' is part of the response content

@pytest.mark.order(4)
def test_login_with_requests(run_server, app):
    with app.app_context():
        login_url = url_for('auth.oidc_login', _external=True)
    
    """Test that a user can log in with a POST request."""
    response = requests.get(login_url, allow_redirects=True)
    # Pytest log output
    logging.debug("Received response with status code: %s", response.status_code)
    logging.debug("Response text: %s", response.text)
    print(response.text)
    
    assert response.status_code == 200
