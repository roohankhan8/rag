import os
from dotenv import load_dotenv

load_dotenv()

from flask import Flask
from flask_cors import CORS
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from .models import db
from .routes import api
from .storage import init_db


def ensure_postgres_database(database_url):
    url = make_url(database_url)
    if url.get_backend_name() != "postgresql":
        return
    database = url.database
    admin_url = os.environ.get("DATABASE_ADMIN_URL")
    if admin_url:
        maintenance_url = make_url(admin_url)
    else:
        maintenance_url = url.set(database="postgres")
    engine = create_engine(maintenance_url, isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as connection:
            exists = connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :database"),
                {"database": database},
            ).scalar()
            if not exists:
                connection.exec_driver_sql(
                    f'CREATE DATABASE "{database.replace(chr(34), chr(34) * 2)}"'
                )
    finally:
        engine.dispose()


def create_app(test_config=None):
    database_url = os.environ.get("DATABASE_URL", "sqlite:///rag.db")
    ensure_postgres_database(database_url)
    app = Flask(__name__)
    app.config.update(
        MAX_CONTENT_LENGTH=2 * 1024 * 1024,
        TESTING=False,
        SQLALCHEMY_DATABASE_URI=database_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
    )
    if test_config:
        app.config.update(test_config)
    CORS(app)
    db.init_app(app)
    with app.app_context():
        init_db()
    app.register_blueprint(api, url_prefix="/api")
    return app


app = create_app()
