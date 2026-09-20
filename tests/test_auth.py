import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import MagicMock
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


class TestCreateClient:
    def test_inoltra_open_browser(self, monkeypatch):
        visto = {}

        def fake_build(open_browser=True):
            visto["open_browser"] = open_browser
            return MagicMock()

        monkeypatch.setattr(auth, "_build_oauth", fake_build)
        auth.create_client(open_browser=False)
        assert visto["open_browser"] is False


class TestSilentAuthentication:
    @pytest.fixture
    def manager(self, monkeypatch):
        monkeypatch.setattr(auth, "load_dotenv", lambda *a, **k: None)
        monkeypatch.setenv("SPOTIPY_CLIENT_ID", "cid123")
        manager = auth._build_oauth(open_browser=False)
        manager.cache_handler = MagicMock()
        manager.get_authorization_code = MagicMock(
            side_effect=AssertionError("Il login interattivo non deve iniziare")
        )
        return manager

    @pytest.mark.parametrize("cached", [
        None, {}, {"scope": "wrong"}, "invalid",
        {"scope": auth.SCOPE, "access_token": "cached"},
        {"scope": auth.SCOPE, "access_token": "old", "expires_at": 0},
        {"scope": auth.SCOPE, "access_token": "", "expires_at": 9999999999},
        {"scope": auth.SCOPE, "access_token": "cached", "expires_at": "invalid"},
    ])
    def test_cache_non_valida_fallisce_senza_login(self, manager, cached):
        manager.cache_handler.get_cached_token.return_value = cached
        with pytest.raises(RuntimeError, match="login"):
            manager.get_access_token()
        manager.get_authorization_code.assert_not_called()

    def test_token_valido_usato_senza_login(self, manager):
        manager.cache_handler.get_cached_token.return_value = {
            "access_token": "cached", "scope": auth.SCOPE, "expires_at": 9999999999,
        }
        assert manager.get_access_token() == "cached"
        manager.get_authorization_code.assert_not_called()

    def test_token_scaduto_rinnovato_in_silenzio(self, manager):
        manager.cache_handler.get_cached_token.return_value = {
            "access_token": "old", "refresh_token": "refresh",
            "scope": auth.SCOPE, "expires_at": 0,
        }
        manager.refresh_access_token = MagicMock(return_value={"access_token": "new", "expires_at": 9999999999})
        assert manager.get_access_token() == "new"
        manager.refresh_access_token.assert_called_once_with("refresh")
        manager.get_authorization_code.assert_not_called()

    def test_refresh_fallito_non_avvia_login(self, manager):
        manager.cache_handler.get_cached_token.return_value = {
            "access_token": "old", "refresh_token": "refresh",
            "scope": auth.SCOPE, "expires_at": 0,
        }
        manager.refresh_access_token = MagicMock(side_effect=RuntimeError("refresh failed"))
        with pytest.raises(RuntimeError, match="refresh failed"):
            manager.get_access_token()
        manager.get_authorization_code.assert_not_called()

    def test_interattivo_mantiene_pkce_standard(self, monkeypatch):
        monkeypatch.setattr(auth, "load_dotenv", lambda *a, **k: None)
        monkeypatch.setenv("SPOTIPY_CLIENT_ID", "cid123")
        assert type(auth._build_oauth(open_browser=True)) is SpotifyPKCE


def test_client_non_riprova_mutazioni_automaticamente(monkeypatch):
    monkeypatch.setattr(auth, "_build_oauth", lambda **kwargs: MagicMock())
    spotify = MagicMock()
    monkeypatch.setattr(auth, "Spotify", spotify)
    auth.create_client()
    assert spotify.call_args.kwargs["retries"] == 0
    assert spotify.call_args.kwargs["status_retries"] == 0
