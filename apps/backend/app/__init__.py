from pathlib import Path

from flask import Flask, send_from_directory
from flask_cors import CORS

from .routes import api_bp
from .seed import init_and_seed


def create_app() -> Flask:
    root_dir = Path(__file__).resolve().parents[3]
    frontend_dir = root_dir / "apps" / "frontend"

    app = Flask(__name__, static_folder=str(frontend_dir), static_url_path="")
    app.config.from_object("app.config.Config")
    CORS(app)

    init_and_seed()

    app.register_blueprint(api_bp, url_prefix="/api")

    @app.route("/")
    def index():
        return send_from_directory(frontend_dir, "index.html")

    return app
