from flask import Blueprint

viewer_bp = Blueprint(
    "viewer", __name__,
    static_folder="../../public",
    static_url_path="",
    template_folder="../../public"
)


@viewer_bp.route("/", defaults={"path": ""})
def show_viewer(path):
    return viewer_bp.send_static_file("viewer.html")
