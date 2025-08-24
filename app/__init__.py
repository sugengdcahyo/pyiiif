from flask import Flask
from flask_cors import CORS
from .config import get_config
from .errors import register_error_handlers
from .routes.iiif import bp as iiif_bp
from .routes.viewer import viewer_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(get_config())
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
