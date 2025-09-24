from flask import Blueprint
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
PUBLIC_DIR = BASE_DIR / "public"


viewer_bp = Blueprint(
    "viewer", __name__,
    static_folder=PUBLIC_DIR,
    static_url_path=""
)


@viewer_bp.route("/", defaults={"path": ""})
def show_viewer(path):
    return viewer_bp.send_static_file("viewer.html")
