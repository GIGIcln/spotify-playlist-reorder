import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import MagicMock, patch
from cli import _parse_selezione, _totale_brani, risolvi_criterio, _parse_args, main
from playlist import CRITERI_ORDINAMENTO

N = 10


class TestTotaleBrani:
    def test_schema_classico_tracks(self):
        assert _totale_brani({"tracks": {"total": 42}}) == 42

    def test_schema_nuovo_items(self):
        # Spotify può restituire tracks=None e il totale sotto 'items'
        assert _totale_brani({"tracks": None, "items": {"href": "x", "total": 5}}) == 5

    def test_entrambi_assenti(self):
        assert _totale_brani({"tracks": None, "items": None}) == 0

    def test_chiavi_mancanti(self):
        assert _totale_brani({}) == 0


class TestParseSelezione:
    def test_singolo(self):
        assert _parse_selezione("3", N) == [2]

    def test_lista(self):
        assert _parse_selezione("1,3,5", N) == [0, 2, 4]

    def test_range(self):
        assert _parse_selezione("2-4", N) == [1, 2, 3]

    def test_misto(self):
        assert _parse_selezione("1,3-5,7", N) == [0, 2, 3, 4, 6]

    def test_duplicati_rimossi(self):
        assert _parse_selezione("2,2,3", N) == [1, 2]

    def test_fuori_range_alto(self):
        assert _parse_selezione("11", N) is None

    def test_fuori_range_basso(self):
        assert _parse_selezione("0", N) is None

    def test_range_invertito(self):
        assert _parse_selezione("5-2", N) is None

    def test_stringa_non_numerica(self):
        assert _parse_selezione("abc", N) is None

    def test_stringa_vuota(self):
        assert _parse_selezione("", N) is None

    def test_spazi_attorno(self):
        assert _parse_selezione(" 1 , 3 ", N) == [0, 2]

    def test_range_limite_massimo(self):
        assert _parse_selezione(f"1-{N}", N) == list(range(N))


class TestRisolviCriterio:
    def test_numero_valido(self):
        assert risolvi_criterio("2") is CRITERI_ORDINAMENTO[1]

    def test_slug_valido(self):
        assert risolvi_criterio("data-asc") is CRITERI_ORDINAMENTO[1]

    def test_slug_case_insensitive_con_spazi(self):
        assert risolvi_criterio("  Data-Asc ") is CRITERI_ORDINAMENTO[1]

    def test_numero_fuori_range(self):
        assert risolvi_criterio("99") is None
        assert risolvi_criterio("0") is None

    def test_slug_inesistente(self):
        assert risolvi_criterio("bpm") is None

    def test_stringa_vuota(self):
        assert risolvi_criterio("") is None


class TestParseArgs:
    def test_default(self):
        a = _parse_args([])
        assert a.playlist is None
        assert a.criterio is None
        assert a.yes is False
        assert a.lista_criteri is False

    def test_playlist_ripetibile(self):
        a = _parse_args(["-p", "A", "-p", "B"])
        assert a.playlist == ["A", "B"]

    def test_criterio_e_yes(self):
        a = _parse_args(["-c", "data-asc", "-y"])
        assert a.criterio == "data-asc"
        assert a.yes is True

    def test_lista_criteri(self):
        assert _parse_args(["--lista-criteri"]).lista_criteri is True

    def test_dry_run(self):
        assert _parse_args([]).dry_run is False
        assert _parse_args(["--dry-run"]).dry_run is True


class TestMain:
    def _run_main(self, argv):
        sp = MagicMock()
        sp.current_user.return_value = {"id": "me"}
        with patch("cli.create_client", return_value=sp) as m_client, \
             patch("cli.riordina_playlist") as m_rp, \
             patch("cli.scegli_playlist", return_value=["INT1"]) as m_sp, \
             patch("cli.scegli_criterio", return_value=CRITERI_ORDINAMENTO[0]) as m_sc:
            main(argv)
        return {"client": m_client, "rp": m_rp, "sp": m_sp, "sc": m_sc}

    def test_lista_criteri_non_autentica(self):
        with patch("cli.create_client") as m_client:
            main(["--lista-criteri"])
        m_client.assert_not_called()

    def test_criterio_invalido_esce_prima_di_auth(self):
        with patch("cli.create_client") as m_client, pytest.raises(SystemExit):
            main(["-p", "abc", "-c", "inesistente"])
        m_client.assert_not_called()

    def test_non_interattivo_slug_e_yes(self):
        m = self._run_main(["-p", "PL1", "-c", "data-asc", "--yes"])
        m["sp"].assert_not_called()   # niente menu playlist
        m["sc"].assert_not_called()   # niente menu criterio
        m["rp"].assert_called_once()
        args, kwargs = m["rp"].call_args
        assert args[1] == "https://open.spotify.com/playlist/PL1"
        assert args[2] is CRITERI_ORDINAMENTO[1]  # data-asc
        assert kwargs["me_id"] == "me"
        assert kwargs["chiedi_conferma"] is False

    def test_non_interattivo_criterio_default_e_conferma(self):
        m = self._run_main(["-p", "PL1"])
        m["sc"].assert_not_called()
        args, kwargs = m["rp"].call_args
        assert args[2] is CRITERI_ORDINAMENTO[0]   # default: primo criterio
        assert kwargs["chiedi_conferma"] is True    # senza --yes

    def test_interattivo_usa_i_menu(self):
        m = self._run_main([])
        m["sp"].assert_called_once()
        m["sc"].assert_called_once()
        m["rp"].assert_called_once()

    def test_url_normalizzato_in_id(self):
        m = self._run_main(["-p", "https://open.spotify.com/playlist/XYZ?si=1", "-c", "1", "-y"])
        args, _ = m["rp"].call_args
        assert args[1] == "https://open.spotify.com/playlist/XYZ"

    def test_piu_playlist(self):
        m = self._run_main(["-p", "A", "-p", "B", "-y"])
        assert m["rp"].call_count == 2

    def test_dry_run_propagato(self):
        m = self._run_main(["-p", "PL1", "--dry-run", "-y"])
        _, kwargs = m["rp"].call_args
        assert kwargs["dry_run"] is True

    def test_dry_run_default_false(self):
        m = self._run_main(["-p", "PL1", "-y"])
        _, kwargs = m["rp"].call_args
        assert kwargs["dry_run"] is False

    def test_keyboardinterrupt_uscita_pulita(self):
        with patch("cli._esegui", side_effect=KeyboardInterrupt), \
             pytest.raises(SystemExit) as exc:
            main([])
        assert exc.value.code == 130

    def test_eoferror_uscita_pulita(self):
        with patch("cli._esegui", side_effect=EOFError), \
             pytest.raises(SystemExit) as exc:
            main([])
        assert exc.value.code == 130
