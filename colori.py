"""Colori ANSI minimali per l'output da terminale.

I colori vengono disattivati automaticamente se l'output non è un terminale
interattivo (es. redirect su file o pipe) o se è impostata la variabile
d'ambiente NO_COLOR, così l'output resta pulito.
"""
import os
import sys

USA_COLORE = sys.stdout.isatty() and "NO_COLOR" not in os.environ


def _stile(codice: str):
    def applica(testo) -> str:
        if not USA_COLORE:
            return str(testo)
        return f"\033[{codice}m{testo}\033[0m"
    return applica


bold = _stile("1")
dim = _stile("2")
cyan = _stile("36")
blu = _stile("34")
verde = _stile("32")
giallo = _stile("33")
