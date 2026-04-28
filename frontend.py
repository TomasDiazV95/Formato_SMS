from __future__ import annotations

import os
import subprocess
from pathlib import Path

from flask import Response, abort, send_from_directory


FRONTEND_DIR = Path(__file__).resolve().parent / "react-frontend"
FRONTEND_DIST = FRONTEND_DIR / "dist"
FRONTEND_PUBLIC = FRONTEND_DIR / "public"

_BUILD_HINT = "React build no encontrado. Ejecuta `npm install && npm run build` en react-frontend/."
_AUTO_BUILD = os.getenv("AUTO_BUILD_FRONTEND", "0").lower() in {"1", "true", "yes"}
_AUTO_BUILT = False


def _find_latest_bundle(assets_dir: Path, pattern: str) -> Path | None:
    candidates = sorted(
        assets_dir.glob(pattern),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def _render_runtime_index() -> str | None:
    assets_dir = FRONTEND_DIST / "assets"
    if not assets_dir.exists():
        return None

    js_bundle = _find_latest_bundle(assets_dir, "index-*.js")
    if js_bundle is None:
        return None

    css_bundle = _find_latest_bundle(assets_dir, "index-*.css")
    css_tag = ""
    if css_bundle is not None:
        css_tag = f'    <link rel="stylesheet" href="/assets/{css_bundle.name}" />\n'

    return (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "  <head>\n"
        '    <meta charset="UTF-8" />\n'
        '    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />\n'
        '    <meta name="viewport" content="width=device-width, initial-scale=1.0" />\n'
        "    <title>Formato SMS</title>\n"
        f"{css_tag}"
        "  </head>\n"
        "  <body>\n"
        '    <div id="root"></div>\n'
        f'    <script type="module" src="/assets/{js_bundle.name}"></script>\n'
        "  </body>\n"
        "</html>\n"
    )


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
    target = FRONTEND_DIST / file_name
    if not target.exists():
        abort(404, description=_BUILD_HINT)


def serve_react_app():
    """Devuelve el index.html compilado del frontend."""
    global _AUTO_BUILT
    if _AUTO_BUILD and not _AUTO_BUILT:
        ensure_frontend_build(force=True)
        _AUTO_BUILT = True

    dist_index = FRONTEND_DIST / "index.html"
    if dist_index.exists():
        return send_from_directory(FRONTEND_DIST, "index.html")

    runtime_index = _render_runtime_index()
    if runtime_index is not None:
        return Response(runtime_index, mimetype="text/html")

    _require_build("index.html")
    return send_from_directory(FRONTEND_DIST, "index.html")


__all__ = ["FRONTEND_DIST", "FRONTEND_PUBLIC", "serve_react_app", "ensure_frontend_build"]
