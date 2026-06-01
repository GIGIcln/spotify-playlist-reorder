# 🎵 Spotify Playlist Reorderer

Uno script Python semplice e automatizzato per riordinare le tue playlist di Spotify secondo criteri personalizzati.

## ✨ Caratteristiche
- 📊 **Ordinamento intelligente**: 1. Artista (A-Z) → 2. Data di uscita → 3. Numero traccia (stesso album)
- 🔒 **Sicuro**: Usa variabili d'ambiente (`.env`) per proteggere le tue credenziali
- 🌐 **Compatibile**: Gestisce il formato API aggiornato di Spotify (`item` / `track`)
- ⚡ **Ottimizzato**: Riempie automaticamente playlist >100 brani rispettando i limiti API
- 🚫 **Filtro automatico**: Salta podcast, episodi, brani non disponibili e file locali

## 📋 Requisiti
- Python 3.8 o superiore
- Un account Spotify personale
- Un account GitHub (opzionale, per pubblicare il progetto)

## 🛠️ Installazione e Configurazione

### 1. Installa le dipendenze
Apri il terminale nella cartella del progetto ed esegui:
```bash
pip install spotipy python-dotenv
```
### 2. Configura spotify for developers
1. Vai su developer.spotify.com/dashboard e accedi
2. Clicca su *create app* -> inserisci nome e descrizione -> clicca *create*
3. Clicca *Edit Settings* -> in *Redirect URls* aggiungi: 
```bash
http://127.0.0.1:8080/callback
```
Clicca *Add* -> *Save*
4. Copia *Client ID* e *Client Secret* (clicca "View client secret" se richiesto)

### 3. Crea file .env 
Nella cartella del progetto, crea un file chiamato .env (nota il punto iniziale) e incolla:
```bash
SPOTIPY_CLIENT_ID=il_tuo_client_id_qui
SPOTIPY_CLIENT_SECRET=il_tuo_client_secret_qui
SPOTIPY_REDIRECT_URI=http://127.0.0.1:8080/callback
```
⚠️ **Importante**: Il file .env è già escluso da .gitignore. Non verrà mai caricato su GitHub.

## 🚀 Come usarlo

1. Apri il terminale nella cartella del progetto
2. Esegui:
```bash
python3 reorder_playlist.py
```
3. Incolla il link della playlist (deve essere una playlist tua)
4. Autorizza l'app nel browser che si aprirà
5. Attendi il messaggio: ✅ Playlist riordinata con successo!

## 💡 Come funziona l'ordinamento
Lo script segue questa priorità esatta:
1. ##Artista##: Ordine alfabetico (A-Z, senza distinzione tra maiuscole/minuscole)
2. ##Data di uscita##: Dal più vecchio al più recente
3. ##Track Number##: Se due brani hanno stesso artista e stessa data (es. stesso album/EP), mantiene l'ordine originale della tracklist

## 📦 Struttura del progetto
```
spotify-reorder/
├── reorder_playlist.py      # Script principale
├── .env                     # Credenziali (NON committare su GitHub)
├── .gitignore               # File ignorati da Git
└── README.md                # Questa guida
```

## 🔧 Risoluzione problemi comuni

| Problema | Soluzione |
|----------|-----------|
| `redirect_uri mismatch` o `Not secure` | Verifica che l'URI nel file `.env` sia **identico** a quello salvato nella dashboard Spotify |
| `❌ Nessun brano valido trovato` | La playlist potrebbe contenere solo podcast, brani non disponibili nel tuo paese (grigi) o file locali. Prova con una playlist tua contenente canzoni standard |
| `ModuleNotFoundError: No module named 'spotipy'` | Esegui `pip install spotipy python-dotenv` |
| `zsh: no matches found: .cache-*` | Usa le virgolette: `rm -f ".cache-*"` (necessario su macOS) |
| Lo script chiede l'autorizzazione ogni volta | Cancella i file di cache vecchi: `rm -f ".cache-*"` e riprova |