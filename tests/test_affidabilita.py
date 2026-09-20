import copy
import json
from unittest.mock import patch

import pytest
import playlist
import cli


class SpotifyFinto:
    def __init__(self):
        self.items = [self.entry('b'), self.entry('a')]
        self.version = 0
        self.calls = []
        self.bad_write = False

    @staticmethod
    def entry(name, local=False):
        return {'added_at': '2026-01-01T00:00:00Z', 'track': {
            'uri': 'spotify:track:' + name, 'type': 'track', 'name': name,
            'is_local': local, 'artists': [{'name': name}],
            'album': {'release_date': '2020'},
        }}

    def playlist(self, *args, **kwargs):
        return {'snapshot_id': str(self.version), 'name': 'P',
                'owner': {'id': 'me'}, 'collaborative': False}

    def playlist_items(self, *args, **kwargs):
        return {'items': copy.deepcopy(self.items), 'next': None}

    def playlist_reorder_items(self, pid, range_start, insert_before, range_length, snapshot_id):
        assert snapshot_id == str(self.version)
        self.calls.append((range_start, insert_before, range_length))
        if not self.bad_write:
            block = self.items[range_start:range_start + range_length]
            del self.items[range_start:range_start + range_length]
            self.items[insert_before:insert_before] = block
        self.version += 1
        return {'snapshot_id': str(self.version)}


def test_riordino_verificato():
    sp = SpotifyFinto()
    assert playlist.riordina_playlist(sp, 'pid', me_id='me') == 'riordinata'
    assert sp.items[0]['track']['name'] == 'a'


def test_modifica_durante_anteprima_blocca_scrittura():
    sp = SpotifyFinto()
    def confirm(*args):
        sp.version += 1
        return True
    with patch('playlist._conferma_interattiva', side_effect=confirm):
        with pytest.raises(RuntimeError, match='cambiata'):
            playlist.riordina_playlist(sp, 'pid', chiedi_conferma=True)
    assert not sp.calls


def test_risposta_successo_ma_ordine_errato_non_e_successo():
    sp = SpotifyFinto()
    sp.bad_write = True
    with pytest.raises(RuntimeError, match='verifica'):
        playlist.riordina_playlist(sp, 'pid')


def test_backup_include_locali_e_non_sovrascrive(tmp_path):
    sp = SpotifyFinto()
    sp.items.insert(1, sp.entry('local', local=True))
    first = playlist.esporta_backup(sp, 'pid', str(tmp_path))
    second = playlist.esporta_backup(sp, 'pid', str(tmp_path))
    assert first != second
    data = json.loads(open(first).read())
    assert data['version'] == 2
    assert len(data['items']) == 3


def test_restore_rifiuta_locale_aggiunto(tmp_path):
    sp = SpotifyFinto()
    backup = playlist.esporta_backup(sp, 'pid', str(tmp_path))
    sp.items.append(sp.entry('local', local=True))
    sp.version += 1
    with pytest.raises(ValueError, match='cambiata'):
        playlist.ripristina_backup(sp, backup)
    assert not sp.calls


def test_restore_file_invalido_prima_di_auth(tmp_path):
    path = tmp_path / 'bad.json'
    path.write_text('{}')
    with patch('cli.create_client') as client, pytest.raises(SystemExit) as exc:
        cli.main(['--restore', str(path), '-y'])
    assert exc.value.code == 1
    client.assert_not_called()


def test_batch_continua_ma_esce_con_errore():
    with patch('cli.create_client') as client, patch('cli.riordina_playlist', side_effect=[RuntimeError('errore'), 'riordinata']) as reorder:
        client.return_value.current_user.return_value = {'id': 'me'}
        with pytest.raises(SystemExit) as exc:
            cli.main(['-p', 'a', '-p', 'b', '-y'])
    assert exc.value.code == 1
    assert reorder.call_count == 2


def test_piu_spostamenti_non_si_bloccano_a_meta():
    # Lo snapshot_id restituito da playlist_reorder_items non coincide con quello
    # di GET /playlists/{id}: se lo si riconfronta a ogni giro il riordino si
    # interrompe dopo il primo spostamento.
    sp = SpotifyFinto()
    sp.items = [sp.entry(n) for n in 'cadb']
    assert playlist.riordina_playlist(sp, 'pid', me_id='me') == 'riordinata'
    assert [i['track']['name'] for i in sp.items] == list('abcd')
    assert len(sp.calls) > 1
