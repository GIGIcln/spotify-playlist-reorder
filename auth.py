import os
import sys
from pathlib import Path

from spotipy import Spotify
from spotipy.oauth2 import SpotifyPKCE
from spotipy.cache_handler import CacheFileHandler
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


class _SilentSpotifyPKCE(SpotifyPKCE):
    """Use cached credentials and refresh only, with no interactive fallback."""

    def get_access_token(self, code=None, check_cache=True):
        login_error = (
            "Token Spotify assente o non valido. Esegui un login "
            "senza --no-browser prima di riprovare."
        )
        try:
            cached = self.cache_handler.get_cached_token()
            token = self.validate_token(cached) if isinstance(cached, dict) else None
            access_token = token.get("access_token") if token else None
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise RuntimeError(login_error) from exc
        if not isinstance(access_token, str) or not access_token:
            raise RuntimeError(login_error)
        return access_token


def _build_oauth(open_browser: bool = False) -> SpotifyPKCE:
    """Costruisce l'auth manager PKCE.

    PKCE è pensato per i client pubblici (CLI, desktop) che non possono
    custodire un secret: serve solo il client_id, nessun client_secret.
    """
    load_dotenv(dotenv_path=os.path.join(_get_app_dir(), ".env"), override=False)
    client_id = os.getenv("SPOTIPY_CLIENT_ID")
    redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI", "http://127.0.0.1:8888/callback")

    if not client_id:
        raise ValueError("Credenziali mancanti. Verifica SPOTIPY_CLIENT_ID nel file .env")

    oauth_class = SpotifyPKCE if open_browser else _SilentSpotifyPKCE
    return oauth_class(
        client_id=client_id,
        redirect_uri=redirect_uri,
        scope=SCOPE,
        cache_handler=CacheFileHandler(cache_path=CACHE_PATH),
        open_browser=open_browser,
    )


def create_client(open_browser: bool = True) -> Spotify:
    """Crea il client Spotify.

    Con open_browser=False (es. esecuzioni programmate) l'app non apre mai il
    browser: se il token in cache non è rinnovabile in silenzio, l'auth fallisce
    invece di restare in attesa di un login manuale.
    """
    # Repeating a PUT after an ambiguous failure can move a different block.
    # Let the application decide whether an operation can safely be retried.
    return Spotify(
        auth_manager=_build_oauth(open_browser=open_browser),
        retries=0,
        status_retries=0,
    )
