import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from playlist import estrai_playlist_id, normalizza_data, calcola_ordine_target, CRITERI_ORDINAMENTO

DEFAULT = CRITERI_ORDINAMENTO[0]
PER_DATA_ASC = CRITERI_ORDINAMENTO[1]
PER_DATA_DESC = CRITERI_ORDINAMENTO[2]
PER_ARTISTA = CRITERI_ORDINAMENTO[3]
PER_POPOLARITA = CRITERI_ORDINAMENTO[4]


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
