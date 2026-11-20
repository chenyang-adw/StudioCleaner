"""应用目录与常用路径。"""
import os
from pathlib import Path


def local_appdata() -> Path:
    return Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")


def roaming_appdata() -> Path:
    return Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")


APP_DIR = local_appdata() / "StudioCleaner"
DB_PATH = APP_DIR / "studio_cleaner.db"
LOG_PATH = APP_DIR / "studio_cleaner.log"
BACKUP_DIR = APP_DIR / "registry_backups"


def ensure_app_dirs() -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def windows_dir() -> Path:
    return Path(os.environ.get("SystemRoot", r"C:\Windows"))


def user_temp_dirs() -> list[Path]:
    out = []
    for key in ("TEMP", "TMP"):
        v = os.environ.get(key)
        if v:
            out.append(Path(v))
    la = os.environ.get("LOCALAPPDATA")
    if la:
        out.append(Path(la) / "Temp")
    return out
