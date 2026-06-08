# Spotify Playlist Reorderer

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Un'applicazione desktop per riordinare automaticamente le tue playlist Spotify in base a criteri personalizzati: Artista, Data di uscita e Posizione nell'album.

## Indice

- [Caratteristiche](#caratteristiche)
- [Requisiti](#requisiti)
- [Installazione](#installazione)
- [Utilizzo](#utilizzo)
- [Configurazione Spotify](#configurazione-spotify)
- [Come Funziona](#come-funziona)
- [Struttura del Progetto](#struttura-del-progetto)
- [Risoluzione Problemi](#risoluzione-problemi)
- [Licenza](#licenza)

## Caratteristiche

### Funzionalità Principali

- **Interfaccia Grafica Intuitiva**: GUI moderna basata su Tkinter
- **Ordinamento Intelligente**: 
  1. Ordine alfabetico dell'artista (A-Z)
  2. Data di uscita del brano (dal più vecchio al più recente)
  3. Posizione nell'album originale
- **Gestione Credenziali**: Salvataggio sicuro di Client ID e Secret
- **Supporto Playlist Grandi**: Gestione ottimizzata fino a 500+ brani
- **Elaborazione Batch**: Upload a blocchi da 100 brani
- **Retry Automatico**: Gestione intelligente degli errori
- **Progress Bar Visiva**: Monitoraggio in tempo reale
- **Filtri Automatici**: Esclusione di podcast e file locali

### Sicurezza

- Le credenziali vengono salvate localmente in settings.json
- Utilizzo del protocollo OAuth 2.0 di Spotify
- Nessuna raccolta di dati personali

## Requisiti

### Software Richiesto

- **Python 3.8** o superiore
- **Account Spotify** (gratuito o premium)
- **Connessione Internet** per l'autorizzazione API

### Dipendenze Python

Il progetto utilizza le seguenti librerie:
- spotipy>=2.23.0
- python-dotenv>=1.0.0 (solo per versione CLI)

## Installazione

### Metodo 1: Clonazione da GitHub (Consigliato)

1. **Clona la repository**: `git clone https://github.com/GIGIcln/spotify-playlist-reorder.git`

2. **Entra nella cartella**: `cd spotify-playlist-reorder`

3. **Crea un ambiente virtuale** (consigliato):
   
   Windows: `python -m venv spotify-env` poi `.\spotify-env\Scripts\Activate.ps1`
   
   macOS/Linux: `python3 -m venv spotify-env` poi `source spotify-env/bin/activate`

4. **Installa le dipendenze**: `pip install -r requirements.txt`

5. **Avvia l'applicazione**: `python app.py`

## Utilizzo

### Primo Avvio

1. Configura l'App Spotify Developer (vedi sezione Configurazione)

2. Avvia l'applicazione: `python app.py`

3. Inserisci le credenziali:
   - **Client ID**: Copiato dalla dashboard Spotify
   - **Client Secret**: Copiato dalla dashboard Spotify
   - **Link Playlist**: URL della playlist da riordinare

4. Clicca su "🎵 Riordina Playlist"

5. Autorizza l'app nel browser che si aprirà automaticamente

6. Attendi il completamento: La progress bar mostrerà l'avanzamento

### Esempio di Output

Playlist con 247 elementi totali - Trovati 245 brani validi su 247 totali - Ordinamento completato: 245 brani - Invio in 3 batch da 100 brani - Batch 1/3: brani 1-100 - Batch 2/3: brani 101-200 - Batch 3/3: brani 201-245 - Playlist riordinata con successo!

## Configurazione Spotify

### Creare un'App Spotify Developer

1. **Accedi a Spotify Developer Dashboard**: Vai su https://developer.spotify.com/dashboard e accedi con il tuo account Spotify

2. **Crea una nuova app**: Clicca su "Create app", compila i campi:
   - **App name**: Spotify Playlist Reorderer (o nome a piacere)
   - **App description**: Tool per riordinare playlist automaticamente
   - **Redirect URI**: http://127.0.0.1:8888/callback
   - Accetta i termini e clicca "Save"

3. **Ottieni le credenziali**: Clicca sulla tua app, vai su "Settings", copia **Client ID** e **Client Secret**

4. **Configura Redirect URI**: Assicurati che sia impostato: http://127.0.0.1:8888/callback - Clicca "Add" e poi "Save"

### Note Importanti

- Non condividere mai il tuo Client Secret
- Il Redirect URI deve corrispondere esattamente a quello nel codice
- L'app è per uso personale

## Come Funziona

### Algoritmo di Ordinamento

L'applicazione utilizza un algoritmo di ordinamento a tre livelli:
1. Nome artista (A-Z)
2. Data di uscita (YYYY-MM-DD)
3. Numero traccia nell'album

### Gestione Playlist Grandi

Per playlist con più di 100 brani:
1. **Svuotamento**: Rimuove tutti i brani dalla playlist
2. **Aggiunta Batch**: Re-inserisce i brani ordinati a blocchi di 100
   - Ogni batch attende 0.5 secondi per evitare rate limiting
   - Retry automatico (fino a 3 tentativi) in caso di errore

### Filtri Applicati

Vengono automaticamente esclusi:
- File locali (non disponibili su Spotify)
- Podcast ed episodi
- Brani senza URI valido
- Brani con metadati incompleti

## Struttura del Progetto

spotify-playlist-reorder/
├── app.py (Applicazione GUI principale)
├── reorder_playlist.py (Versione CLI terminale)
├── requirements.txt (Dipendenze Python)
├── settings.json (Credenziali salvate - auto-generato)
├── .gitignore (File ignorati da Git)
├── LICENSE (Licenza MIT)
└── README.md (Documentazione)

## Risoluzione Problemi

### Errori Comuni

**"Invalid client"** - Causa: Client ID o Secret errati - Soluzione: Verifica di aver copiato correttamente le credenziali

**"Redirect URI mismatch"** - Causa: Il Redirect URI non corrisponde - Soluzione: Assicurati che sia http://127.0.0.1:8888/callback

**"HTTP Error 429: Too Many Requests"** - Causa: Troppe richieste in poco tempo - Soluzione: Attendi qualche minuto, l'app gestisce automaticamente i retry

**"Nessun brano valido trovato"** - Causa: Playlist vuota o contenente solo podcast/file locali - Soluzione: Verifica che la playlist contenga brani musicali

**"ModuleNotFoundError: No module named 'spotipy'"** - Causa: Dipendenze non installate - Soluzione: pip install -r requirements.txt

## Licenza

Distribuito sotto licenza MIT. Vedi LICENSE per maggiori informazioni.

Copyright (c) 2026 GIGIcln

---
