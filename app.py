# app.py
import os
from flask import Flask, abort, send_from_directory
from flask_cors import CORS

from modules import (
    backoffice_bp,
    bit_bp,
    crm_bp,
    gm_bp,
    ivr_bp,
    mail_bp,
    reports_bp,
    resultantes_bp,
    sant_hipotecario_bp,
    santander_consumer_bp,
    sms_bp,
    tanner_bp,
)
from frontend import FRONTEND_DIST, serve_react_app, ensure_frontend_build

#caca
def _register_frontend_routes(app: Flask) -> None:
    spa_paths = [
        "/",
        "/procesos",
        "/procesos/sms",
        "/procesos/ivr",
        "/procesos/mail",
        "/procesos/crm",
        "/procesos/santander-consumer",
        "/cargas",
        "/cargas/gm",
        "/cargas/bit",
        "/cargas/tanner",
        "/cargas/santander",
        "/cargas/porsche",
        "/reportes",
        "/backoffice/catalogos",
    ]

    for path in spa_paths:
        endpoint_name = path.strip("/").replace("/", "_") or "root"
        app.add_url_rule(path, f"spa_{endpoint_name}", serve_react_app)

    @app.route("/assets/<path:filename>")
    def serve_frontend_assets(filename: str):
        assets_dir = FRONTEND_DIST / "assets"
        if not assets_dir.exists():
            abort(404)
        return send_from_directory(assets_dir, filename)

    @app.route("/favicon.svg")
    def serve_frontend_favicon():
        return send_from_directory(FRONTEND_DIST, "favicon.svg")

    @app.route("/icons.svg")
    def serve_frontend_icons():
        return send_from_directory(FRONTEND_DIST, "icons.svg")


def create_app():
    app = Flask(__name__)
    app.secret_key = "123456"

    CORS(
        app,
        resources={r"/*": {"origins": "*"}},
        supports_credentials=False,
        expose_headers=["Content-Disposition"],
    )

    app.register_blueprint(sms_bp)
    app.register_blueprint(ivr_bp)
    app.register_blueprint(gm_bp)
    app.register_blueprint(bit_bp)
    app.register_blueprint(tanner_bp)
    app.register_blueprint(sant_hipotecario_bp)
    app.register_blueprint(santander_consumer_bp)
    app.register_blueprint(mail_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(resultantes_bp)
    app.register_blueprint(crm_bp)
    app.register_blueprint(backoffice_bp)

    _register_frontend_routes(app)

    if os.getenv("AUTO_BUILD_FRONTEND", "0").lower() in {"1", "true", "yes"}:
        ensure_frontend_build(force=True)

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5013)
