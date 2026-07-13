import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import MagicMock, patch
from playlist import (
    estrai_playlist_id,
    normalizza_data,
    calcola_ordine_target,
    enrich_with_audio_features,
    _reorder_with_retry,
    verifica_proprietario,
    _mostra_anteprima,
    CRITERI_ORDINAMENTO,
)

DEFAULT = CRITERI_ORDINAMENTO[0]
PER_DATA_ASC = CRITERI_ORDINAMENTO[1]
PER_DATA_DESC = CRITERI_ORDINAMENTO[2]
PER_ARTISTA = CRITERI_ORDINAMENTO[3]
PER_POPOLARITA = CRITERI_ORDINAMENTO[4]
BPM_SLOW = CRITERI_ORDINAMENTO[5]
BPM_FAST = CRITERI_ORDINAMENTO[6]
ENERGIA = CRITERI_ORDINAMENTO[7]
DANCE = CRITERI_ORDINAMENTO[8]
VALENCE = CRITERI_ORDINAMENTO[9]


class TestEstraiPlaylistId:
    def test_url_standard(self):
        assert estrai_playlist_id("https://open.spotify.com/playlist/abc123") == "abc123"

    def test_url_con_query_string(self):
        assert estrai_playlist_id("https://open.spotify.com/playlist/abc123?si=xyz") == "abc123"

    def test_solo_id(self):
        assert estrai_playlist_id("abc123") == "abc123"


class TestNormalizzaData:
    def test_data_completa(self):
        assert normalizza_data("2021-3-5") == "2021-03-05"

    def test_solo_anno(self):
        assert normalizza_data("2021") == "2021-01-01"

    def test_anno_e_mese(self):
        assert normalizza_data("2021-7") == "2021-07-01"

    def test_stringa_vuota(self):
        assert normalizza_data("") == "9999-99-99"

    def test_none(self):
        assert normalizza_data(None) == "9999-99-99"

    def test_gia_zero_padded(self):
        assert normalizza_data("2000-01-01") == "2000-01-01"


class TestCalcolaOrdineTarget:
    def _make_track(self, artista, data, posizione, popularity=50):
        return {
            "uri": f"spotify:track:{artista}",
            "artista": artista,
            "data_uscita": data,
            "posizione_album": posizione,
            "popularity": popularity,
        }

    # --- criterio default (artista → data → posizione) ---

    def test_gia_ordinata(self):
        tracks = [
            self._make_track("alpha", "2020-01-01", 1),
            self._make_track("beta", "2020-01-01", 1),
        ]
        assert calcola_ordine_target(tracks) == [0, 1]

    def test_ordine_invertito(self):
        tracks = [
            self._make_track("zeta", "2020-01-01", 1),
            self._make_track("alpha", "2020-01-01", 1),
        ]
        assert calcola_ordine_target(tracks) == [1, 0]

    def test_stesso_artista_per_data(self):
        tracks = [
            self._make_track("alpha", "2022-01-01", 1),
            self._make_track("alpha", "2019-01-01", 1),
        ]
        assert calcola_ordine_target(tracks) == [1, 0]

    def test_stesso_artista_stessa_data_per_posizione(self):
        tracks = [
            self._make_track("alpha", "2020-01-01", 3),
            self._make_track("alpha", "2020-01-01", 1),
            self._make_track("alpha", "2020-01-01", 2),
        ]
        assert calcola_ordine_target(tracks) == [1, 2, 0]

    def test_lista_vuota(self):
        assert calcola_ordine_target([]) == []

    def test_singolo_elemento(self):
        tracks = [self._make_track("alpha", "2020-01-01", 1)]
        assert calcola_ordine_target(tracks) == [0]

    def test_nessun_criterio_usa_default(self):
        tracks = [
            self._make_track("zeta", "2020-01-01", 1),
            self._make_track("alpha", "2020-01-01", 1),
        ]
        assert calcola_ordine_target(tracks, None) == calcola_ordine_target(tracks, DEFAULT)

    # --- per data ascendente ---

    def test_per_data_asc(self):
        tracks = [
            self._make_track("z", "2022-01-01", 1),
            self._make_track("a", "2019-01-01", 1),
            self._make_track("m", "2021-01-01", 1),
        ]
        assert calcola_ordine_target(tracks, PER_DATA_ASC) == [1, 2, 0]

    # --- per data discendente ---

    def test_per_data_desc(self):
        tracks = [
            self._make_track("z", "2022-01-01", 1),
            self._make_track("a", "2019-01-01", 1),
            self._make_track("m", "2021-01-01", 1),
        ]
        assert calcola_ordine_target(tracks, PER_DATA_DESC) == [0, 2, 1]

    # --- per artista ---

    def test_per_artista(self):
        tracks = [
            self._make_track("zeta", "2020-01-01", 1),
            self._make_track("alpha", "2020-01-01", 1),
            self._make_track("miro", "2020-01-01", 1),
        ]
        assert calcola_ordine_target(tracks, PER_ARTISTA) == [1, 2, 0]

    # --- per popolarità ---

    def test_per_popolarita(self):
        tracks = [
            self._make_track("a", "2020-01-01", 1, popularity=30),
            self._make_track("b", "2020-01-01", 1, popularity=90),
            self._make_track("c", "2020-01-01", 1, popularity=60),
        ]
        assert calcola_ordine_target(tracks, PER_POPOLARITA) == [1, 2, 0]


class TestEnrichWithAudioFeatures:
    def _make_track(self, uri):
        return {
            "uri": uri,
            "artista": "x",
            "data_uscita": "2020-01-01",
            "posizione_album": 1,
            "popularity": 50,
        }

    def test_enrich_adds_all_fields(self):
        sp = MagicMock()
        sp.audio_features.return_value = [
            {"tempo": 120.0, "energy": 0.8, "danceability": 0.7, "valence": 0.6},
            {"tempo": 90.0, "energy": 0.4, "danceability": 0.5, "valence": 0.3},
        ]
        tracks = [
            self._make_track("spotify:track:aaa"),
            self._make_track("spotify:track:bbb"),
        ]
        result = enrich_with_audio_features(sp, tracks)
        assert result[0]["bpm"] == 120.0
        assert result[0]["energy"] == 0.8
        assert result[0]["danceability"] == 0.7
        assert result[0]["valence"] == 0.6
        assert result[1]["bpm"] == 90.0

    def test_enrich_skips_none_features(self):
        sp = MagicMock()
        sp.audio_features.return_value = [
            None,
            {"tempo": 100.0, "energy": 0.5, "danceability": 0.5, "valence": 0.5},
        ]
        tracks = [
            self._make_track("spotify:track:aaa"),
            self._make_track("spotify:track:bbb"),
        ]
        result = enrich_with_audio_features(sp, tracks)
        assert "bpm" not in result[0]
        assert result[1]["bpm"] == 100.0

    def test_enrich_handles_api_error_gracefully(self):
        sp = MagicMock()
        sp.audio_features.side_effect = Exception("rate limited")
        tracks = [self._make_track("spotify:track:aaa")]
        result = enrich_with_audio_features(sp, tracks)
        assert "bpm" not in result[0]

    def test_enrich_batches_over_100(self):
        feat = {"tempo": 100.0, "energy": 0.5, "danceability": 0.5, "valence": 0.5}
        sp = MagicMock()
        sp.audio_features.side_effect = [[feat] * 100, [feat] * 1]
        tracks = [self._make_track(f"spotify:track:t{i}") for i in range(101)]
        enrich_with_audio_features(sp, tracks)
        assert sp.audio_features.call_count == 2


class TestAudioCriteria:
    def _make_audio_track(self, bpm, energy, danceability, valence):
        return {
            "uri": f"spotify:track:{bpm}-{energy}",
            "artista": "x",
            "data_uscita": "2020-01-01",
            "posizione_album": 1,
            "popularity": 50,
            "bpm": float(bpm),
            "energy": float(energy),
            "danceability": float(danceability),
            "valence": float(valence),
        }

    def test_bpm_slow_to_fast(self):
        tracks = [
            self._make_audio_track(140, 0.8, 0.7, 0.6),
            self._make_audio_track(80, 0.4, 0.5, 0.3),
            self._make_audio_track(110, 0.6, 0.6, 0.5),
        ]
        assert calcola_ordine_target(tracks, BPM_SLOW) == [1, 2, 0]

    def test_bpm_fast_to_slow(self):
        tracks = [
            self._make_audio_track(140, 0.8, 0.7, 0.6),
            self._make_audio_track(80, 0.4, 0.5, 0.3),
            self._make_audio_track(110, 0.6, 0.6, 0.5),
        ]
        assert calcola_ordine_target(tracks, BPM_FAST) == [0, 2, 1]

    def test_energia(self):
        tracks = [
            self._make_audio_track(100, 0.3, 0.5, 0.5),
            self._make_audio_track(100, 0.9, 0.5, 0.5),
            self._make_audio_track(100, 0.6, 0.5, 0.5),
        ]
        assert calcola_ordine_target(tracks, ENERGIA) == [1, 2, 0]

    def test_danceability(self):
        tracks = [
            self._make_audio_track(100, 0.5, 0.2, 0.5),
            self._make_audio_track(100, 0.5, 0.9, 0.5),
            self._make_audio_track(100, 0.5, 0.6, 0.5),
        ]
        assert calcola_ordine_target(tracks, DANCE) == [1, 2, 0]

    def test_valence(self):
        tracks = [
            self._make_audio_track(100, 0.5, 0.5, 0.1),
            self._make_audio_track(100, 0.5, 0.5, 0.8),
            self._make_audio_track(100, 0.5, 0.5, 0.5),
        ]
        assert calcola_ordine_target(tracks, VALENCE) == [1, 2, 0]

    def test_missing_audio_field_defaults_to_zero(self):
        tracks = [
            {"uri": "a", "artista": "x", "data_uscita": "2020", "posizione_album": 1, "popularity": 50},
            {"uri": "b", "artista": "x", "data_uscita": "2020", "posizione_album": 1, "popularity": 50, "bpm": 120.0},
        ]
        result = calcola_ordine_target(tracks, BPM_SLOW)
        assert result == [0, 1]


class TestReorderWithRetry:
    def _make_error(self, http_status: int, retry_after: int = 0):
        err = Exception(f"HTTP {http_status}")
        err.http_status = http_status
        err.headers = {"Retry-After": str(retry_after)}
        return err

    def test_success_on_first_call(self):
        sp = MagicMock()
        sp.playlist_reorder_items.return_value = {"snapshot_id": "s1"}
        result = _reorder_with_retry(sp, "pid", range_start=0, insert_before=1, range_length=1)
        assert result == {"snapshot_id": "s1"}
        sp.playlist_reorder_items.assert_called_once()

    def test_retries_on_429(self):
        sp = MagicMock()
        sp.playlist_reorder_items.side_effect = [
            self._make_error(429, retry_after=0),
            {"snapshot_id": "s1"},
        ]
        with patch("playlist.time.sleep") as mock_sleep:
            result = _reorder_with_retry(sp, "pid", range_start=0, insert_before=1, range_length=1)
        assert result == {"snapshot_id": "s1"}
        assert sp.playlist_reorder_items.call_count == 2
        mock_sleep.assert_called_once()

    def test_retries_on_503(self):
        sp = MagicMock()
        sp.playlist_reorder_items.side_effect = [
            self._make_error(503),
            self._make_error(503),
            {"snapshot_id": "s1"},
        ]
        with patch("playlist.time.sleep"):
            result = _reorder_with_retry(sp, "pid", range_start=0, insert_before=1, range_length=1)
        assert result == {"snapshot_id": "s1"}
        assert sp.playlist_reorder_items.call_count == 3

    def test_raises_after_max_retries(self):
        sp = MagicMock()
        sp.playlist_reorder_items.side_effect = self._make_error(503)
        with patch("playlist.time.sleep"), pytest.raises(Exception):
            _reorder_with_retry(sp, "pid", range_start=0, insert_before=1, range_length=1, max_retries=2)
        assert sp.playlist_reorder_items.call_count == 2

    def test_does_not_retry_on_400(self):
        sp = MagicMock()
        sp.playlist_reorder_items.side_effect = self._make_error(400)
        with patch("playlist.time.sleep"), pytest.raises(Exception):
            _reorder_with_retry(sp, "pid", range_start=0, insert_before=1, range_length=1)
        sp.playlist_reorder_items.assert_called_once()

    def test_respects_retry_after_header(self):
        sp = MagicMock()
        sp.playlist_reorder_items.side_effect = [
            self._make_error(429, retry_after=5),
            {"snapshot_id": "s1"},
        ]
        with patch("playlist.time.sleep") as mock_sleep:
            _reorder_with_retry(sp, "pid", range_start=0, insert_before=1, range_length=1)
        mock_sleep.assert_called_once_with(5)


class TestVerificaProprietario:
    def test_playlist_di_proprieta(self):
        sp = MagicMock()
        sp.playlist.return_value = {"name": "Mia", "owner": {"id": "me"}, "collaborative": False}
        ok, dettaglio = verifica_proprietario(sp, "pid", "me")
        assert ok is True
        assert dettaglio == "Mia"

    def test_playlist_di_altri_non_modificabile(self):
        sp = MagicMock()
        sp.playlist.return_value = {"name": "Altrui", "owner": {"id": "spotify"}, "collaborative": False}
        ok, dettaglio = verifica_proprietario(sp, "pid", "me")
        assert ok is False
        assert "non tua" in dettaglio

    def test_playlist_collaborativa_modificabile(self):
        sp = MagicMock()
        sp.playlist.return_value = {"name": "Team", "owner": {"id": "altro"}, "collaborative": True}
        ok, _ = verifica_proprietario(sp, "pid", "me")
        assert ok is True

    def test_errore_api_non_modificabile(self):
        sp = MagicMock()
        sp.playlist.side_effect = Exception("boom")
        ok, dettaglio = verifica_proprietario(sp, "pid", "me")
        assert ok is False
        assert "impossibile leggere" in dettaglio


class TestMostraAnteprima:
    def test_anteprima_usa_ordine_target(self, capsys):
        tracks = [
            {"artista": "zeta", "nome": "Z", "data_uscita": "2020-01-01"},
            {"artista": "alpha", "nome": "A", "data_uscita": "2019-06-01"},
        ]
        _mostra_anteprima(tracks, [1, 0])
        out = capsys.readouterr().out
        # il primo brano mostrato deve essere quello in testa a target_order (alpha)
        assert out.index("alpha") < out.index("zeta")
        assert "(2019)" in out
