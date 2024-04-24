import os
from flask import current_app
import pytest
from app import create_app, db
from flask_migrate import upgrade, downgrade
from sqlalchemy import create_engine, inspect, text

from config import Config
# Define database URIs for different databases
DATABASE_URIS = [
    'sqlite:///test.db',
    'mysql+pymysql://root:password@localhost:3307/testdb',
    'postgresql://user:password@localhost:5433/testdb'
]

@pytest.mark.parametrize("db_uri", DATABASE_URIS)
def test_database_migrations(monkeypatch, db_uri):
    monkeypatch.setenv('WINGETTY_SQLALCHEMY_DATABASE_URI', db_uri)
    app = create_app()
    with app.app_context():
        db.reflect()
        db.drop_all()
        # Apply migrations to set up the databases
        os.chdir(os.path.dirname(os.path.dirname(__file__)))
        upgrade()

        print('Current database URI:', db.engine.url)

        engine = db.engine
        inspector = inspect(engine)
        assert 'user' in inspector.get_table_names()

        # Teardown: revert migrations and drop all tables
        downgrade()
        # Go back to the original directory
        os.chdir(os.path.dirname(__file__))
        db.reflect()
        db.drop_all()



        # Recreate inspector to refresh the schema information
        inspector = inspect(engine)
        assert 'user' not in inspector.get_table_names()
