# Spotify Playlist Reorder

Script Python per riordinare automaticamente le playlist di Spotify in base a criteri personalizzati.

## Prerequisiti

- Python 3.10 o superiore installato
- Un account Spotify (Premium consigliato per funzionalità complete)
- Connessione a Internet

## 1. Ottenere le credenziali Spotify Developer

Prima di iniziare, devi creare un'app sulla piattaforma Spotify Developer per ottenere le chiavi di accesso:

1. Vai su https://developer.spotify.com/dashboard
2. Accedi con il tuo account Spotify
3. Clicca su "Create App" (o "Crea app")
4. Compila i campi:
   - App name: un nome a piacere (es. "My Playlist Reorderer")
   - App description: una breve descrizione
   - Redirect URI: http://localhost:8888/callback (deve essere ESATTAMENTE questo)
   - Which API/SDKs: spunta "Web API"
5. Accetta i termini e clicca "Save"
6. Dalla pagina dell'app, copia il "Client ID" e il "Client Secret" (clicca "Show client secret" per vederlo)

## 2. Installazione

### 2.1 Clonare la repository

Apri il terminale e clona il progetto:

    git clone https://github.com/GIGIcln/spotify-playlist-reorder.git
    cd spotify-playlist-reorder

### 2.2 Creare l'ambiente virtuale

Un ambiente virtuale isola le dipendenze del progetto dal resto del sistema.

Su macOS / Linux:

    python3 -m venv spotify-env
    source spotify-env/bin/activate

Su Windows (CMD):

    python -m venv spotify-env
    spotify-env\Scripts\activate

Su Windows (PowerShell) - se il comando sopra dà errore di permessi:

    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
    .\spotify-env\Scripts\activate

Dopo l'attivazione, vedrai "(spotify-env)" all'inizio della riga di comando.

### 2.3 Installare le dipendenze

Con l'ambiente virtuale attivo, installa le librerie necessarie:

    pip install -r requirements.txt

## 3. Configurazione

### 3.1 Creare il file .env

Nella cartella principale del progetto, crea un file chiamato `.env` (con il punto davanti) e incolla questo contenuto, sostituendo i valori con le tue credenziali:

    SPOTIPY_CLIENT_ID=il_tuo_client_id_qui
    SPOTIPY_CLIENT_SECRET=il_tuo_client_secret_qui
    SPOTIPY_REDIRECT_URI=http://localhost:8888/callback

Importante:
- Non rimuovere mai il punto davanti al nome del file (.env)
- Non committare questo file su GitHub (contiene dati sensibili)
- Il Redirect URI deve corrispondere esattamente a quello impostato nella Dashboard Spotify

### 3.2 Verificare la configurazione

Assicurati che il file `.gitignore` contenga queste righe (dovrebbe già esserci):

    .env
    .cache
    .spotify_token_cache
    spotify-env/
    build/
    dist/
    *.spec
    .DS_Store

## 4. Utilizzo

Con l'ambiente virtuale attivo, esegui lo script:

    python reorder_playlist.py

### Primo avvio

Al primo avvio:
1. Si aprirà automaticamente il browser per chiederti di autorizzare l'app
2. Accetta le autorizzazioni richieste
3. Verrai reindirizzato a http://localhost:8888/callback (la pagina potrebbe sembrare vuota, è normale)
4. Il token di accesso verrà salvato automaticamente nel file `.spotify_token_cache`

### Avvi successivi

Le volte successive, lo script userà il token salvato e non richiederà nuovamente l'autorizzazione (fino alla scadenza del token).

## 5. Struttura del progetto

    spotify-playlist-reorder/
    ├── reorder_playlist.py      # Script principale
    ├── requirements.txt         # Lista delle dipendenze Python
    ├── README.md                # Questa documentazione
    ├── .gitignore               # File da ignorare in Git
    ├── .env                     # Credenziali (DA CREARE, non committare)
    ├── .spotify_token_cache     # Token di accesso (generato automaticamente)
    └── spotify-env/             # Ambiente virtuale (non committare)

## 6. Risoluzione problemi comuni

### Errore: "Nessun token trovato nella cache"
Elimina il file `.spotify_token_cache` e riesegui lo script per rifare l'autenticazione:

    rm .spotify_token_cache
    python reorder_playlist.py

### Errore: "server_error" dall'auth server
Verifica che il Redirect URI nella Dashboard Spotify sia esattamente `http://localhost:8888/callback` (senza slash finale, con http e non https).

### Errore di permessi su Windows nell'attivare l'ambiente virtuale
Esegui PowerShell come amministratore oppure:

    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

### Errore: "ModuleNotFoundError: No module named 'spotipy'"
Assicurati di aver attivato l'ambiente virtuale e di aver eseguito `pip install -r requirements.txt`.

### Il browser non si apre automaticamente
Copia manualmente l'URL che appare nel terminale e incollalo nel browser.

## 7. Sicurezza

- Il file `.env` contiene le tue chiavi segrete: non condividerlo mai
- Il file `.spotify_token_cache` contiene il token di accesso: non condividerlo
- Il `.gitignore` è già configurato per escludere automaticamente questi file
- Se le tue credenziali finiscono online per errore, rigenerale immediatamente dalla Dashboard Spotify

## 8. Aggiornare le dipendenze

Se il progetto viene aggiornato con nuove dipendenze, esegui:

    pip install -r requirements.txt --upgrade
