import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import auth
from spotipy.oauth2 import SpotifyPKCE


class TestBuildOauth:
    def test_usa_pkce_senza_secret(self, monkeypatch):
        # load_dotenv disattivato per non leggere il .env reale.
        monkeypatch.setattr(auth, "load_dotenv", lambda *a, **k: None)
        monkeypatch.setenv("SPOTIPY_CLIENT_ID", "cid123")
        monkeypatch.delenv("SPOTIPY_CLIENT_SECRET", raising=False)

        mgr = auth._build_oauth()

        assert isinstance(mgr, SpotifyPKCE)
        assert mgr.client_id == "cid123"

    def test_manca_client_id_errore(self, monkeypatch):
        monkeypatch.setattr(auth, "load_dotenv", lambda *a, **k: None)
        monkeypatch.delenv("SPOTIPY_CLIENT_ID", raising=False)

        with pytest.raises(ValueError):
            auth._build_oauth()

    def test_client_secret_ignorato(self, monkeypatch):
        # Anche se presente in ambiente, il secret non deve essere richiesto né usato.
        monkeypatch.setattr(auth, "load_dotenv", lambda *a, **k: None)
        monkeypatch.setenv("SPOTIPY_CLIENT_ID", "cid123")
        monkeypatch.setenv("SPOTIPY_CLIENT_SECRET", "irrilevante")

        mgr = auth._build_oauth()

        assert isinstance(mgr, SpotifyPKCE)
        assert not hasattr(mgr, "client_secret") or not mgr.client_secret
