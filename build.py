#!/usr/bin/env python3
"""Cross-platform build script — produces a standalone executable via flet pack.

Windows : dist/SpotifyPlaylistReorder.exe
macOS   : dist/SpotifyPlaylistReorder.app
"""

import subprocess
import sys
from pathlib import Path

APP_NAME = "SpotifyPlaylistReorder"
APP_DISPLAY = "Spotify Playlist Reorder"
APP_VERSION = "1.0.0"


def _find_flet(root: Path) -> str:
    """Return the flet CLI executable, preferring the project venv.

    Checks common venv locations relative to the project root, then
    falls back to whatever 'flet' is on PATH.
    """
    venv_names = ["spotify-env", "venv", ".venv"]
    scripts_subdir = "Scripts" if sys.platform == "win32" else "bin"
    flet_name = "flet.exe" if sys.platform == "win32" else "flet"

    for venv in venv_names:
        candidate = root / venv / scripts_subdir / flet_name
        if candidate.exists():
            return str(candidate)

    return flet_name  # fall back to PATH


def main() -> None:
    root = Path(__file__).parent
    flet = _find_flet(root)

    cmd = [
        flet, "pack", "gui.py",
        "--name", APP_NAME,
        "--product-name", APP_DISPLAY,
        "--product-version", APP_VERSION,
        "--hidden-import", "spotipy.oauth2",
    ]

    if sys.platform == "win32" and (root / "icon.ico").exists():
        cmd += ["--icon", "icon.ico"]
    elif sys.platform == "darwin":
        for candidate in ("icon.icns", "icon.png"):
            if (root / candidate).exists():
                cmd += ["--icon", candidate]
                break

    print("Building:", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=root)

    dist = root / "dist"
    print("\nBuild completata!")

    if sys.platform == "win32":
        out = dist / f"{APP_NAME}.exe"
        print(f"   Eseguibile: {out}")
        print("\nNOTA: copia il file .env nella stessa cartella dell'eseguibile prima di avviarlo.")
    elif sys.platform == "darwin":
        out = dist / f"{APP_NAME}.app"
        print(f"   Bundle: {out}")
        print("\nNOTA: copia il file .env nella stessa cartella del bundle .app prima di avviarlo.")
    else:
        print(f"   Output: {dist}")
        print("\nNOTA: copia il file .env nella stessa cartella dell'eseguibile prima di avviarlo.")


if __name__ == "__main__":
    main()
