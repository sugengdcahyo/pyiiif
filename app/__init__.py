from app.logger import setup_logger
from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from .config import get_config, Config
from .errors import register_error_handlers
# from .routes.iiif import bp as iiif_bp
from .routes.iiif_ifds import iiif_bp
from .routes.viewer import viewer_bp
from .routes.metadata import bp as metadata_bp
import os

import logging
from logging.handlers import RotatingFileHandler


load_dotenv()


def create_app() -> Flask:
    app = Flask(__name__)

    # config loader
    app.config.from_object(Config)

    # setup logging
    setup_logger(app)

    # blueprint
    app.register_blueprint(metadata_bp, url_prefix="/metadata")
    app.register_blueprint(iiif_bp, url_prefix="/iiif")
    app.register_blueprint(viewer_bp, url_prefix="/")

    # error handler JSON
    register_error_handlers(app)

    app.logger.info("Flask IIIF app initialized")

    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    return app
