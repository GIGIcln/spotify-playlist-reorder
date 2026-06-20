import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cli import _parse_selezione

N = 10


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
