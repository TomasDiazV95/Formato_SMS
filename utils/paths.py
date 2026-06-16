from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
STORAGE_DIR = PROJECT_ROOT / "storage"
ARCHIVE_DIR = PROJECT_ROOT / "archive"
FRONTEND_DIR = PROJECT_ROOT / "react-frontend"
FRONTEND_DIST = FRONTEND_DIR / "dist"
FRONTEND_PUBLIC = FRONTEND_DIR / "public"


def config_path(filename: str) -> Path:
    return CONFIG_DIR / filename


def data_path(filename: str) -> Path:
    return DATA_DIR / filename


def storage_path(*parts: str) -> Path:
    return STORAGE_DIR.joinpath(*parts)


def archive_path(*parts: str) -> Path:
    return ARCHIVE_DIR.joinpath(*parts)
