from __future__ import annotations

import os
import subprocess
from pathlib import Path

from flask import abort, send_from_directory


FRONTEND_DIR = Path(__file__).resolve().parent / "react-frontend"
FRONTEND_DIST = FRONTEND_DIR / "dist"

_BUILD_HINT = "React build no encontrado. Ejecuta `npm install && npm run build` en react-frontend/."
_AUTO_BUILD = os.getenv("AUTO_BUILD_FRONTEND", "0").lower() in {"1", "true", "yes"}
_AUTO_BUILT = False


def ensure_frontend_build(force: bool = False) -> None:
    dist_index = FRONTEND_DIST / "index.html"
    if not force and dist_index.exists():
        return

    npm_bin = os.environ.get("NPM_BIN", "npm")
    try:
        if not (FRONTEND_DIR / "node_modules").exists():
            subprocess.run([npm_bin, "install"], cwd=FRONTEND_DIR, check=True)
        subprocess.run([npm_bin, "run", "build"], cwd=FRONTEND_DIR, check=True)
    except FileNotFoundError as exc:
        raise RuntimeError("npm no está disponible en el PATH del servidor.") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("Falló la compilación del frontend React.") from exc


def _require_build(file_name: str) -> None:
    ensure_frontend_build()
    target = FRONTEND_DIST / file_name
    if not target.exists():
        abort(404, description=_BUILD_HINT)


def serve_react_app():
    """Devuelve el index.html compilado del frontend."""
    global _AUTO_BUILT
    if _AUTO_BUILD and not _AUTO_BUILT:
        ensure_frontend_build(force=True)
        _AUTO_BUILT = True
    _require_build("index.html")
    return send_from_directory(FRONTEND_DIST, "index.html")


__all__ = ["FRONTEND_DIST", "serve_react_app", "ensure_frontend_build"]
