import os
from dotenv import load_dotenv

load_dotenv()

from flask import Flask
from flask_cors import CORS
from .models import db
from .routes import api
from .storage import init_db


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(
        MAX_CONTENT_LENGTH=2 * 1024 * 1024,
        TESTING=False,
        SQLALCHEMY_DATABASE_URI="sqlite:///rag.db",
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
