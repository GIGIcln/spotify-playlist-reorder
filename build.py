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


def main() -> None:
    root = Path(__file__).parent

    cmd = [
        sys.executable, "-m", "flet", "pack", "gui.py",
        "--name", APP_NAME,
        "--product-name", APP_DISPLAY,
        "--product-version", APP_VERSION,
        "--hidden-import", "spotipy.oauth2",
    ]

    if sys.platform == "win32" and (root / "icon.ico").exists():
        cmd += ["--icon", "icon.ico"]
    elif sys.platform == "darwin" and (root / "icon.icns").exists():
        cmd += ["--icon", "icon.icns"]

    print("Building:", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=root)

    dist = root / "dist"
    print("\n✅ Build completata!")

    if sys.platform == "win32":
        out = dist / f"{APP_NAME}.exe"
        print(f"   Eseguibile: {out}")
        print("\n📋 Copia il file .env nella stessa cartella dell'eseguibile prima di avviarlo.")
    elif sys.platform == "darwin":
        out = dist / f"{APP_NAME}.app"
        print(f"   Bundle: {out}")
        print("\n📋 Copia il file .env nella stessa cartella del bundle .app prima di avviarlo.")
    else:
        print(f"   Output: {dist}")
        print("\n📋 Copia il file .env nella stessa cartella dell'eseguibile prima di avviarlo.")


if __name__ == "__main__":
    main()
