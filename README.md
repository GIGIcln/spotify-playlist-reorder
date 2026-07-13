# Spotify Playlist Reorder

App da **terminale** per riordinare le tue playlist Spotify secondo vari criteri
(artista, data di uscita, popolarità, BPM, energia, danceability, valence) **senza
alterare la data di aggiunta** dei brani.

## Caratteristiche

- **10 criteri di ordinamento**, da classici (artista → album → traccia) a basati sulle audio-feature (BPM, energia, ecc.)
- **Batch**: seleziona e riordina più playlist in una volta
- **Anteprima + conferma** prima di applicare le modifiche
- **Controllo proprietario**: salta con un messaggio chiaro le playlist che non puoi modificare (niente errore 403 grezzo)
- **Preserva la data di aggiunta**: sposta i brani uno a uno invece di riscrivere la playlist
- **Chiamate resilienti**: backoff esponenziale su errori 429 / 5xx
- **Barra di avanzamento** (`tqdm`)

## Prerequisiti

- Python 3.10 o superiore
- Un account Spotify
- Un'app registrata sulla [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) (per le credenziali API)

## Installazione

```bash
git clone https://github.com/GIGIcln/spotify-playlist-reorder.git
cd spotify-playlist-reorder

python3 -m venv spotify-env
source spotify-env/bin/activate      # Windows: spotify-env\Scripts\activate

pip install -e .
```

`pip install -e .` installa le dipendenze **e** registra il comando `spotify-reorder`.

## Configurazione

Crea un file `.env` nella cartella del progetto (non va committato):

```dotenv
SPOTIPY_CLIENT_ID=il_tuo_client_id
SPOTIPY_CLIENT_SECRET=il_tuo_client_secret
SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
```

Il Redirect URI deve corrispondere esattamente a quello impostato nella Dashboard Spotify.

## Utilizzo

Con l'ambiente virtuale attivo, da qualsiasi cartella:

```bash
spotify-reorder
```

(in alternativa: `python reorder_playlist.py` dalla cartella del progetto)

Flusso interattivo:

1. Al primo avvio si apre il browser per autorizzare l'app; il token viene salvato in `.spotify_token_cache` e riusato agli avvii successivi.
2. Viene mostrata la lista numerata delle tue playlist.
3. Scegli una o più playlist: `3`, oppure `1,4,7`, oppure un range `2-5` (anche misto: `1,3-5,7`).
4. Scegli il criterio di ordinamento.
5. Vedi l'**anteprima** dei primi brani nel nuovo ordine e **confermi** (`s/N`) prima di applicare.

## Criteri di ordinamento

| # | Criterio | Audio-feature |
|---|----------|:---:|
| 1 | Artista → Data → Posizione *(default)* | No |
| 2 | Data di uscita — dal più vecchio | No |
| 3 | Data di uscita — dal più recente | No |
| 4 | Artista (A→Z) | No |
| 5 | Popolarità — dal più popolare | No |
| 6 | BPM — dal più lento | Sì |
| 7 | BPM — dal più veloce | Sì |
| 8 | Energia — dalla più alta | Sì |
| 9 | Danceability — dalla più alta | Sì |
| 10 | Valence / positività — dalla più alta | Sì |

## Come funziona il riordino

Invece di svuotare e riscrivere la playlist (che azzererebbe la "data di aggiunta"),
l'app emette singole chiamate `playlist_reorder_items` — una per ogni brano fuori
posto — tracciando lo `snapshot_id`. Una playlist già ordinata non genera nessuna
chiamata.

## Struttura del progetto

```
spotify-playlist-reorder/
├── reorder_playlist.py   # Entry point (python reorder_playlist.py)
├── cli.py                # Interfaccia da terminale
├── playlist.py           # Logica: fetch, sort, riordino, audio-feature
├── auth.py               # OAuth Spotify (legge le credenziali da .env)
├── pyproject.toml        # Metadati + comando `spotify-reorder`
├── requirements.txt
└── tests/                # Test (pytest)
```

## Test

```bash
pip install pytest
pytest tests/
```

## Risoluzione problemi

- **"Credenziali mancanti"** — controlla che `.env` esista e contenga `SPOTIPY_CLIENT_ID` / `SPOTIPY_CLIENT_SECRET`.
- **Token non valido / errori di auth** — elimina `.spotify_token_cache` e riavvia.
- **"comando non trovato: spotify-reorder"** — attiva l'ambiente virtuale (`source spotify-env/bin/activate`).
- **Una playlist viene saltata (403)** — puoi riordinare solo playlist tue o collaborative; l'app te lo segnala prima di procedere.
