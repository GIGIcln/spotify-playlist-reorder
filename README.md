# Spotify Playlist Reorder

App da **terminale** per riordinare le tue playlist Spotify secondo vari criteri
(artista, data di uscita, popolarità) **senza alterare la data di aggiunta** dei brani.

## Caratteristiche

- **5 criteri di ordinamento** (artista → album → traccia, data di uscita, popolarità)
- **Batch**: seleziona e riordina più playlist in una volta
- **Interattivo o da script**: menu guidato, oppure argomenti da riga di comando (`--playlist`, `--criterio`, `--yes`) per automazioni
- **Anteprima + conferma** prima di applicare le modifiche
- **Controllo proprietario**: salta con un messaggio chiaro le playlist che non puoi modificare (niente errore 403 grezzo)
- **Preserva la data di aggiunta**: sposta i brani senza riscrivere la playlist
- **Chiamate resilienti**: backoff esponenziale su errori 429 / 5xx, spostamento a blocchi per ridurre le richieste
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

> **Suggerimento (modalità compat).** Con l'install editable "classico", se
> in futuro aggiungi un nuovo modulo `.py` al progetto potresti ottenere un
> `ModuleNotFoundError` finché non reinstalli. Per evitarlo, installa una volta
> in modalità compat — mette l'intera cartella del progetto sul path, così i
> nuovi moduli funzionano senza reinstallare:
>
> ```bash
> pip install -e . --config-settings editable_mode=compat
> ```

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

### Modalità non-interattiva (script / automazioni)

Passando `--playlist` salti i menu: la playlist è quella indicata e il criterio,
se non specificato con `--criterio`, è il primo (default). La conferma resta
richiesta a meno che tu non aggiunga `--yes`.

```bash
# playlist esplicita, criterio default, chiede conferma
spotify-reorder --playlist 37i9dQ...

# criterio esplicito (per numero o slug) e nessuna conferma
spotify-reorder -p 37i9dQ... -c data-asc --yes

# più playlist in una volta
spotify-reorder -p <id1> -p <id2> -y

# accetta anche URL completi
spotify-reorder -p "https://open.spotify.com/playlist/37i9dQ...?si=abc" -y

# elenco dei criteri (numero + slug) senza autenticarsi
spotify-reorder --lista-criteri
```

| Flag | Descrizione |
|------|-------------|
| `-p`, `--playlist` | ID o URL di una playlist. Ripetibile. Se omesso → menu interattivo. |
| `-c`, `--criterio` | Numero (`1`–`5`) o slug del criterio. Default (con `-p`): il primo. |
| `-y`, `--yes` | Applica senza chiedere conferma. |
| `--lista-criteri` | Mostra i criteri disponibili ed esce. |

### Comando globale (senza attivare il venv)

Il comando `spotify-reorder` installato nel venv ha uno shebang che punta al
Python del venv, quindi funziona anche senza attivarlo. Basta renderlo
raggiungibile dal `PATH`.

**Opzione A — symlink** (macOS / Linux; `~/.local/bin` di solito è già nel `PATH`):

```bash
ln -sf "$(pwd)/spotify-env/bin/spotify-reorder" ~/.local/bin/spotify-reorder
```

**Opzione B — alias** (aggiungi a `~/.zshrc` o `~/.bashrc`):

```bash
alias spotify-reorder="/percorso/assoluto/spotify-playlist-reorder/spotify-env/bin/spotify-reorder"
```

Dopo l'una o l'altra, puoi digitare `spotify-reorder` da qualsiasi cartella,
in un terminale nuovo, senza `source spotify-env/bin/activate`. Il file `.env`
viene comunque cercato nella cartella del progetto. Se ricrei il venv o sposti
la cartella, rifai il symlink/alias.

## Criteri di ordinamento

| # | Slug | Criterio |
|---|------|----------|
| 1 | `default` | Artista → Data → Posizione *(default)* |
| 2 | `data-asc` | Data di uscita — dal più vecchio |
| 3 | `data-desc` | Data di uscita — dal più recente |
| 4 | `artista` | Artista (A→Z) |
| 5 | `popolarita` | Popolarità — dal più popolare |

## Come funziona il riordino

Invece di svuotare e riscrivere la playlist (che azzererebbe la "data di aggiunta"),
l'app emette chiamate `playlist_reorder_items` tracciando lo `snapshot_id`. I brani
già contigui che finiscono nella stessa posizione target vengono spostati in blocco
con un'unica chiamata (`range_length > 1`), riducendo il numero di richieste. Una
playlist già ordinata non genera nessuna chiamata.

## Struttura del progetto

```
spotify-playlist-reorder/
├── reorder_playlist.py   # Entry point (python reorder_playlist.py)
├── cli.py                # Interfaccia da terminale
├── playlist.py           # Logica: fetch, sort, riordino
├── auth.py               # OAuth Spotify (legge le credenziali da .env)
├── pyproject.toml        # Metadati + comando `spotify-reorder`
├── requirements.txt
└── tests/                # Test (pytest)
```

## Test

```bash
pip install -e ".[dev]"   # installa anche pytest
pytest
```

## Risoluzione problemi

- **"Credenziali mancanti"** — controlla che `.env` esista e contenga `SPOTIPY_CLIENT_ID` / `SPOTIPY_CLIENT_SECRET`.
- **Token non valido / errori di auth** — elimina `.spotify_token_cache` e riavvia.
- **"comando non trovato: spotify-reorder"** — attiva l'ambiente virtuale (`source spotify-env/bin/activate`).
- **Una playlist viene saltata (403)** — puoi riordinare solo playlist tue o collaborative; l'app te lo segnala prima di procedere.
