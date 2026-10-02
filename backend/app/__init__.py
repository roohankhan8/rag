from dotenv import load_dotenv

load_dotenv()

from flask import Flask
from flask_cors import CORS
from .routes import api

def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(
        MAX_CONTENT_LENGTH=2 * 1024 * 1024,
        TESTING=False,
    )

    if test_config:
        app.config.update(test_config)

    CORS(app)
    app.register_blueprint(api, url_prefix="/api")
    return app


app = create_app()
