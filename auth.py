import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

SCOPE = (
    "playlist-read-private "
    "playlist-read-collaborative "
    "playlist-modify-public "
    "playlist-modify-private"
)


def _get_app_dir() -> str:
    """Return the directory where .env and token cache live.

    - Bundled on Windows/Linux: directory containing the executable.
    - Bundled on macOS: directory containing the .app bundle.
    - Running from source: directory containing this file.
    """
    if hasattr(sys, "frozen"):
        exe = Path(sys.executable)
        if sys.platform == "darwin":
            # Walk up until we find the .app bundle, then return its parent.
            p = exe
            while p.suffix != ".app" and p.parent != p:
                p = p.parent
            return str(p.parent if p.suffix == ".app" else exe.parent)
        return str(exe.parent)
    return os.path.dirname(os.path.abspath(__file__))


CACHE_PATH = os.path.join(_get_app_dir(), ".spotify_token_cache")


def _build_oauth(open_browser: bool = False, show_dialog: bool = False) -> SpotifyOAuth:
    load_dotenv(dotenv_path=os.path.join(_get_app_dir(), ".env"), override=False)
    client_id = os.getenv("SPOTIPY_CLIENT_ID")
    client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
    redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI", "http://127.0.0.1:8888/callback")

    if not client_id or not client_secret:
        raise ValueError("Credenziali mancanti. Verifica il file .env")

    return SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=SCOPE,
        cache_path=CACHE_PATH,
        open_browser=open_browser,
        show_dialog=show_dialog,
    )


def create_client() -> Spotify:
    return Spotify(auth_manager=_build_oauth(open_browser=True))


def create_oauth(show_dialog: bool = False) -> SpotifyOAuth:
    """Return an OAuth manager without triggering auth or opening a browser."""
    return _build_oauth(open_browser=False, show_dialog=show_dialog)


def wait_for_oauth_callback(port: int = 8888) -> str:
    """Start a local HTTP server, wait for the OAuth redirect, return the auth code."""
    auth_code: list[str | None] = [None]

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            params = parse_qs(urlparse(self.path).query)
            auth_code[0] = params.get("code", [None])[0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(
                b"<html><body><h1>Autenticato! Puoi chiudere questa scheda.</h1></body></html>"
            )

        def log_message(self, *_):
            pass

    server = HTTPServer(("127.0.0.1", port), _Handler)
    server.handle_request()
    server.server_close()

    if not auth_code[0]:
        raise ValueError("Nessun codice di autenticazione ricevuto")
    return auth_code[0]
