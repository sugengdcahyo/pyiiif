from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from .config import get_config
from .errors import register_error_handlers
from .routes.iiif import bp as iiif_bp
from .routes.viewer import viewer_bp
import os


load_dotenv()


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(get_config())
    app.config["AWS_ACCESS_KEY_ID"] = os.getenv("AWS_ACCESS_KEY_ID", "")
    app.config["AWS_SECRET_ACCESS_KEY"] = os.getenv(
        "AWS_SECRET_ACCESS_KEY", "")
    app.config["AWS_REGION"] = os.getenv("AWS_REGION", "")
    app.config["IIIF_BACKEND"] = os.getenv("IIIF_BACKEND", "openslide").lower()
    app.config["S3_BUCKET"] = os.getenv("S3_BUCKET", "")
    app.config["S3_REGION"] = os.getenv("S3_REGION_NAME", "")
    app.config["S3_PREFIX"] = os.getenv("S3_SLIDE_PREFIX", "")
    app.config["VALID_EXTENSIONS"] = tuple(
        ext.strip().lower() for ext in os.getenv(
            "VALID_EXTENSIONS", ".svs,.tif,.tiff,.ndpi,.vms,.vmu,.scn,.mrxs,.bif,.tiff"
        ).split(",") if ext.strip()
    )

    CORS(app, origins=app.config["CORS_ORIGINS"])

    # blueprint
    app.register_blueprint(iiif_bp, url_prefix="/iiif")
    app.register_blueprint(viewer_bp, url_prefix="/")

    # error handler JSON
    register_error_handlers(app)

    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    return app
