from flask import Flask, jsonify


def register_error_handlers(app: Flask):
    @app.errorhandler(400)
    @app.errorhandler(404)
    @app.errorhandler(500)
    def json_error(e):
        code = getattr(e, "code", 500)
        return jsonify({
            "error": getattr(e, "description", str(e)),
            "status": code
        }), code
