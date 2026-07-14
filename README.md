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
SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
```

L'app usa il flusso **OAuth PKCE**, pensato per i client pubblici (CLI/desktop):
serve **solo il `client_id`**, nessun `client_secret` da custodire. Il Redirect URI
deve corrispondere esattamente a quello impostato nella Dashboard Spotify.

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

# anteprima del nuovo ordine, senza toccare la playlist
spotify-reorder -p 37i9dQ... -c popolarita --dry-run

# elenco dei criteri (numero + slug) senza autenticarsi
spotify-reorder --lista-criteri
```

| Flag | Descrizione |
|------|-------------|
| `-p`, `--playlist` | ID o URL di una playlist. Ripetibile. Se omesso → menu interattivo. |
| `-c`, `--criterio` | Numero (`1`–`5`) o slug del criterio. Default (con `-p`): il primo. |
| `-y`, `--yes` | Applica senza chiedere conferma. |
| `--dry-run` | Mostra l'anteprima del nuovo ordine senza applicare modifiche. |
| `--backup` | Salva l'ordine attuale della/e playlist in un file, senza riordinare. |
| `--restore FILE` | Ripristina l'ordine di una playlist da un file di backup. |
| `--backup-before` | Salva un backup prima di riordinare (rete di sicurezza). |
| `--no-browser` | Non aprire mai il browser per l'auth (per esecuzioni programmate). |
| `--analizza` | Mostra statistiche della/e playlist (sola lettura), senza riordinare. |
| `--lista-criteri` | Mostra i criteri disponibili ed esce. |

### Analisi (sola lettura)

Mostra gli **artisti più presenti** nella playlist, senza modificarla.

```bash
spotify-reorder -p 37i9dQ... --analizza
```

### Backup e ripristino

Prima di un riordino puoi salvare l'ordine corrente come rete di sicurezza, e
ripristinarlo in seguito. I backup sono file JSON nella cartella `backups/`.

```bash
# salva l'ordine attuale (nessuna modifica alla playlist)
spotify-reorder -p 37i9dQ... --backup

# ...più tardi, ripristina quell'ordine
spotify-reorder --restore backups/37i9dQ...-20260714-101500.json
```

Per prudenza il ripristino **si rifiuta se la playlist è cambiata** dal backup
(brani aggiunti o rimossi): l'insieme dei brani deve combaciare esattamente.

### Riordino automatico programmato (launchd)

Puoi far riordinare una playlist **da sola**, su un orario, tramite `launchd`
(lo scheduler nativo di macOS). Sfrutta la modalità non-interattiva:

```
spotify-reorder -p <URL> -c default --yes --no-browser --backup-before
```

- `--yes` non chiede conferma, `--no-browser` non apre mai il browser (se il
  token non è rinnovabile in silenzio fallisce pulito, lasciando traccia nel log),
  `--backup-before` salva l'ordine prima di riordinare, così puoi sempre fare
  `--restore`.
- **Prerequisito**: fai almeno un login interattivo (`spotify-reorder`) una volta,
  così esiste un token in cache che i run automatici rinnovano da soli.

Configurazione (esempio: il primo del mese alle 9:00):

```bash
# 1. Copia il template ed edita l'URL della playlist e (se vuoi) l'orario
cp examples/com.gigi.spotify-reorder.plist ~/Library/LaunchAgents/

# 2. Attivalo
launchctl load ~/Library/LaunchAgents/com.gigi.spotify-reorder.plist

# 3. Provalo subito (senza aspettare la data)
launchctl start com.gigi.spotify-reorder

# 4. Controlla com'è andata
cat ~/Library/Logs/spotify-reorder.log

# Per disattivarlo
launchctl unload ~/Library/LaunchAgents/com.gigi.spotify-reorder.plist
```

Il file [`examples/com.gigi.spotify-reorder.plist`](examples/com.gigi.spotify-reorder.plist)
contiene i dettagli. Nota: il Mac deve essere acceso all'orario previsto (se era
spento/dormiente, `launchd` recupera l'esecuzione al risveglio).

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

- **"Credenziali mancanti"** — controlla che `.env` esista e contenga `SPOTIPY_CLIENT_ID`.
- **Token non valido / errori di auth** — elimina `.spotify_token_cache` e riavvia.
- **"comando non trovato: spotify-reorder"** — attiva l'ambiente virtuale (`source spotify-env/bin/activate`).
- **Una playlist viene saltata (403)** — puoi riordinare solo playlist tue o collaborative; l'app te lo segnala prima di procedere.
