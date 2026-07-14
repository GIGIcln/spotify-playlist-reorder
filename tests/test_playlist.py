import sys
import os
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import MagicMock, patch
from playlist import (
    estrai_playlist_id,
    normalizza_data,
    calcola_ordine_target,
    applica_riordinamento,
    fetch_tracks,
    riordina_playlist,
    esporta_backup,
    ripristina_backup,
    analizza_playlist,
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


class TestFetchTracks:
    def _sp(self, contents):
        sp = MagicMock()
        sp.playlist_items.return_value = {
            "items": [{"track": c} for c in contents],
            "next": None,
        }
        sp.next.return_value = None
        return sp

    def _track(self, **overrides):
        base = {
            "type": "track",
            "uri": "spotify:track:aaa",
            "name": "X",
            "artists": [{"name": "Artist"}],
            "album": {"release_date": "2020-05-10"},
        }
        base.update(overrides)
        return base

    def test_traccia_normale(self):
        tracks = fetch_tracks(self._sp([self._track()]), "pid")
        assert len(tracks) == 1
        assert tracks[0]["artista"] == "artist"
        assert tracks[0]["data_uscita"] == "2020-05-10"

    def test_album_senza_release_date_non_scartata(self):
        # Prima causava KeyError -> traccia persa; ora viene tenuta con data ignota.
        tracks = fetch_tracks(self._sp([self._track(album={})]), "pid")
        assert len(tracks) == 1
        assert tracks[0]["data_uscita"] == "9999-99-99"

    def test_album_none_non_scartata(self):
        tracks = fetch_tracks(self._sp([self._track(album=None)]), "pid")
        assert len(tracks) == 1
        assert tracks[0]["data_uscita"] == "9999-99-99"

    def test_senza_artisti_usa_placeholder(self):
        tracks = fetch_tracks(self._sp([self._track(artists=[])]), "pid")
        assert tracks[0]["artista"] == "zzz_unknown"

    def test_salta_locali_e_non_tracce(self):
        contents = [
            self._track(is_local=True),
            self._track(type="episode"),
            self._track(uri=""),
            self._track(uri="spotify:track:ok"),
        ]
        tracks = fetch_tracks(self._sp(contents), "pid")
        assert [t["uri"] for t in tracks] == ["spotify:track:ok"]


class TestRiordinaPlaylistDryRun:
    def _sp_con_due_tracce(self):
        # Due tracce in ordine artista "b","a": il criterio default le inverte,
        # quindi target_order != identità e si arriva al ramo dry-run.
        def _track(artista):
            return {
                "type": "track",
                "uri": f"spotify:track:{artista}",
                "name": artista.upper(),
                "artists": [{"name": artista}],
                "album": {"release_date": "2020-01-01"},
            }
        sp = MagicMock()
        sp.playlist.return_value = {"name": "P", "owner": {"id": "me"}, "collaborative": False}
        sp.playlist_items.return_value = {
            "items": [{"track": _track("b")}, {"track": _track("a")}],
            "next": None,
        }
        sp.next.return_value = None
        return sp

    def test_dry_run_non_scrive(self, capsys):
        sp = self._sp_con_due_tracce()
        riordina_playlist(sp, "https://open.spotify.com/playlist/pid",
                          me_id="me", chiedi_conferma=True, dry_run=True)
        sp.playlist_reorder_items.assert_not_called()
        out = capsys.readouterr().out
        assert "Dry-run" in out
        assert "Anteprima" in out  # l'anteprima viene comunque mostrata


def _sp_con_tracce(uris, owner="me"):
    """Spotify finto: playlist di proprietà `owner` con i brani dati (per uri)."""
    def _content(uri):
        return {
            "type": "track", "uri": uri, "name": uri.split(":")[-1],
            "artists": [{"name": "A"}], "album": {"release_date": "2020-01-01"},
        }
    sp = MagicMock()
    sp.playlist.return_value = {"name": "P", "owner": {"id": owner}, "collaborative": False}
    sp.playlist_items.return_value = {"items": [{"track": _content(u)} for u in uris], "next": None}
    sp.next.return_value = None
    sp.playlist_reorder_items.return_value = {"snapshot_id": "s"}
    return sp


class TestEsportaBackup:
    def test_scrive_file_con_ordine(self, tmp_path):
        sp = _sp_con_tracce(["spotify:track:a", "spotify:track:b"])
        path = esporta_backup(sp, "pid", str(tmp_path))
        assert os.path.isfile(path)
        data = json.load(open(path, encoding="utf-8"))
        assert data["playlist_id"] == "pid"
        assert [t["uri"] for t in data["tracks"]] == ["spotify:track:a", "spotify:track:b"]


class TestRipristinaBackup:
    def _scrivi_backup(self, tmp_path, uris, playlist_id="pid"):
        path = tmp_path / "bk.json"
        path.write_text(json.dumps({
            "playlist_id": playlist_id,
            "playlist_name": "P",
            "created_at": "2026-07-14T10:00:00",
            "tracks": [{"uri": u, "nome": u} for u in uris],
        }), encoding="utf-8")
        return str(path)

    def test_ripristina_ordine_se_combacia(self, tmp_path):
        # Backup [b, a]; attuale [a, b] -> riordina.
        bk = self._scrivi_backup(tmp_path, ["spotify:track:b", "spotify:track:a"])
        sp = _sp_con_tracce(["spotify:track:a", "spotify:track:b"])
        ripristina_backup(sp, bk, me_id="me")
        sp.playlist_reorder_items.assert_called()

    def test_rifiuta_se_playlist_cambiata(self, tmp_path, capsys):
        # Backup [a, b]; attuale [a, c] -> insiemi diversi -> annulla, nessuna scrittura.
        bk = self._scrivi_backup(tmp_path, ["spotify:track:a", "spotify:track:b"])
        sp = _sp_con_tracce(["spotify:track:a", "spotify:track:c"])
        ripristina_backup(sp, bk, me_id="me")
        sp.playlist_reorder_items.assert_not_called()
        assert "annullato" in capsys.readouterr().out

    def test_gia_nell_ordine_del_backup(self, tmp_path, capsys):
        bk = self._scrivi_backup(tmp_path, ["spotify:track:a", "spotify:track:b"])
        sp = _sp_con_tracce(["spotify:track:a", "spotify:track:b"])
        ripristina_backup(sp, bk, me_id="me")
        sp.playlist_reorder_items.assert_not_called()
        assert "già nell'ordine" in capsys.readouterr().out

    def test_dry_run_non_scrive(self, tmp_path, capsys):
        bk = self._scrivi_backup(tmp_path, ["spotify:track:b", "spotify:track:a"])
        sp = _sp_con_tracce(["spotify:track:a", "spotify:track:b"])
        ripristina_backup(sp, bk, me_id="me", dry_run=True)
        sp.playlist_reorder_items.assert_not_called()
        assert "Dry-run" in capsys.readouterr().out

    def test_salta_se_non_proprietario(self, tmp_path, capsys):
        bk = self._scrivi_backup(tmp_path, ["spotify:track:b", "spotify:track:a"])
        sp = _sp_con_tracce(["spotify:track:a", "spotify:track:b"], owner="altro")
        ripristina_backup(sp, bk, me_id="me")
        sp.playlist_reorder_items.assert_not_called()
        assert "Salto" in capsys.readouterr().out


class TestAnalizzaPlaylist:
    def _sp(self, tracce):
        # tracce: lista di (uri, artista, popularity)
        def _c(uri, art, pop):
            return {"type": "track", "uri": uri, "name": uri, "artists": [{"name": art}],
                    "album": {"release_date": "2020-01-01"}, "popularity": pop}
        sp = MagicMock()
        sp.playlist.return_value = {"name": "P"}
        sp.playlist_items.return_value = {"items": [{"track": _c(*t)} for t in tracce], "next": None}
        sp.next.return_value = None
        return sp

    def test_top_artisti(self, capsys):
        sp = self._sp([
            ("spotify:track:1", "Rossi", 50),
            ("spotify:track:2", "Rossi", 95),
            ("spotify:track:3", "Bianchi", 70),
        ])
        analizza_playlist(sp, "pid")
        out = capsys.readouterr().out
        assert "Artisti più presenti" in out
        # Rossi (2 brani) prima di Bianchi (1) nella classifica artisti
        assert out.index("Rossi") < out.index("Bianchi")
        assert "2 brani" in out and "1 brano" in out

    def test_playlist_vuota(self, capsys):
        sp = MagicMock()
        sp.playlist.return_value = {"name": "P"}
        sp.playlist_items.return_value = {"items": [], "next": None}
        sp.next.return_value = None
        analizza_playlist(sp, "pid")
        assert "Nessun brano" in capsys.readouterr().out

    def test_non_scrive_mai(self, capsys):
        sp = self._sp([("spotify:track:1", "Rossi", 50)])
        analizza_playlist(sp, "pid")
        sp.playlist_reorder_items.assert_not_called()


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


class _FakeSpotify:
    """Spotify finto che applica la vera semantica di playlist_reorder_items.

    Parte con la playlist in ordine originale [0, 1, ..., n-1]; dopo le chiamate
    emesse da applica_riordinamento, `order` deve combaciare con target_order.
    """

    def __init__(self, n: int):
        self.order = list(range(n))
        self.calls = []
        self.received_snapshots = []

    def playlist_reorder_items(self, playlist_id, range_start, insert_before,
                               range_length, snapshot_id=None):
        self.calls.append((range_start, insert_before, range_length))
        self.received_snapshots.append(snapshot_id)
        block = self.order[range_start:range_start + range_length]
        rest = self.order[:range_start] + self.order[range_start + range_length:]
        ib = insert_before - range_length if insert_before > range_start else insert_before
        self.order = rest[:ib] + block + rest[ib:]
        return {"snapshot_id": f"s{len(self.calls)}"}


class TestApplicaRiordinamento:
    def _run(self, target_order):
        sp = _FakeSpotify(len(target_order))
        moves = applica_riordinamento(sp, "pid", target_order)
        return sp, moves

    def test_realizza_ordine_target(self):
        sp, _ = self._run([2, 0, 1, 3])
        assert sp.order == [2, 0, 1, 3]

    def test_gia_ordinata_nessuna_chiamata(self):
        sp, moves = self._run([0, 1, 2, 3])
        assert sp.order == [0, 1, 2, 3]
        assert moves == 0
        assert sp.calls == []

    def test_blocco_contiguo_una_sola_chiamata(self):
        sp, moves = self._run([1, 2, 3, 0])
        assert sp.order == [1, 2, 3, 0]
        assert moves == 1
        assert sp.calls == [(1, 0, 3)]  # sposta il blocco [1,2,3] in testa

    def test_batching_riduce_le_chiamate(self):
        # Due metà scambiate: un solo spostamento a blocco invece di ~5.
        target = [5, 6, 7, 8, 9, 0, 1, 2, 3, 4]
        sp, moves = self._run(target)
        assert sp.order == target
        assert moves == 1

    def test_snapshot_id_concatenato(self):
        sp, _ = self._run([3, 0, 1, 2, 5, 4])
        # La prima chiamata parte senza snapshot, le successive usano quello precedente.
        assert sp.received_snapshots[0] is None
        assert sp.received_snapshots[1:] == [f"s{i}" for i in range(1, len(sp.calls))]

    def test_progress_callback(self):
        progress = []
        sp = _FakeSpotify(4)
        applica_riordinamento(sp, "pid", [3, 0, 1, 2], on_progress=lambda d, t: progress.append((d, t)))
        assert progress[-1] == (4, 4)  # arriva sempre al totale

    def test_correttezza_su_molte_permutazioni(self):
        import random
        rng = random.Random(1234)
        for _ in range(300):
            n = rng.randint(1, 15)
            target = list(range(n))
            rng.shuffle(target)
            sp, moves = self._run(target)
            assert sp.order == target
            assert moves <= n  # mai peggio di uno spostamento per brano


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
