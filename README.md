# Spotify Playlist Reorderer

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()

Un'applicazione desktop per riordinare automaticamente le tue playlist Spotify in base a criteri personalizzati: Artista, Data di uscita e Posizione nell'album. Disponibile sia come script Python che come applicazione .exe per Windows.

## Indice

- [Caratteristiche](#caratteristiche)
- [Nota Importante sulle Credenziali](#nota-importante-sulle-credenziali)
- [Requisiti](#requisiti)
- [Installazione](#installazione)
- [Utilizzo](#utilizzo)
- [Configurazione Spotify](#configurazione-spotify)
- [Creare file EXE](#creare-file-exe-windows)
- [Come Funziona](#come-funziona)
- [Struttura del Progetto](#struttura-del-progetto)
- [Risoluzione Problemi](#risoluzione-problemi)
- [Licenza](#licenza)

## Caratteristiche

### Funzionalita Principali

- **Interfaccia Grafica Intuitiva**: GUI moderna basata su Tkinter
- **Ordinamento Intelligente**:
  1. Ordine alfabetico dell'artista (A-Z)
  2. Data di uscita del brano (dal piu vecchio al piu recente)
  3. Posizione nell'album originale
- **Gestione Credenziali**: Salvataggio sicuro di Client ID e Secret
- **Supporto Playlist Grandi**: Gestione ottimizzata fino a 500+ brani
- **Elaborazione Batch**: Upload a blocchi da 100 brani
- **Retry Automatico**: Gestione intelligente degli errori
- **Progress Bar Visiva**: Monitoraggio in tempo reale
- **Filtri Automatici**: Esclusione di podcast e file locali
- **File Executable**: Disponibile versione .exe per Windows
- **Versione Flet**: Interfaccia moderna con supporto mobile e web

### Sicurezza

- Le credenziali vengono salvate localmente in settings.json
- Utilizzo del protocollo OAuth 2.0 di Spotify
- Nessuna raccolta di dati personali

## Nota Importante sulle Credenziali

**Ogni utente deve creare la propria app Spotify Developer!**

Questo e un progetto open source che puoi usare liberamente, ma:

- NON usare le credenziali di qualcun altro
- Crea la TUA app su Spotify Developer (e gratuito)
- Usa le TUE credenziali personali

### Perche?

1. **Limiti API**: Spotify impone limiti di richieste per app. Condividere le credenziali significa condividere i limiti e rischiare il blocco.
2. **Sicurezza**: Le credenziali sono personali e collegate al tuo account Spotify.
3. **Termini di Servizio**: E richiesto da Spotify che ogni sviluppatore usi le proprie credenziali.

### E difficile?

No! Creare un'app Spotify Developer:
- E **gratuito**
- Richiede **2 minuti**
- Serve solo un **account Spotify** (anche gratuito)
- Segui la sezione Configurazione Spotify sotto

### Posso distribuire l'app agli amici?

Si! Puoi:
- Condividere il link a questa repository
- Condividere il file .exe che hai creato
- Insegnare loro a configurare le proprie credenziali

Ma **ogni utente deve configurare le proprie credenziali** al primo avvio.

## Requisiti

### Software Richiesto

- **Python 3.8** o superiore (per versione script)
- **Account Spotify** (gratuito o premium)
- **Connessione Internet** per l'autorizzazione API

### Per creare l'EXE (Windows)

- Sistema operativo Windows 10/11
- PyInstaller (si installa automaticamente)

## Installazione

### Opzione 1: Utilizzo come Script Python

1. **Clona la repository**: `git clone https://github.com/GIGIcln/spotify-playlist-reorder.git`

2. **Entra nella cartella**: `cd spotify-playlist-reorder`

3. **Crea un ambiente virtuale** (consigliato):

   Windows: `python -m venv spotify-env` poi `.\spotify-env\Scripts\Activate.ps1`

   macOS/Linux: `python3 -m venv spotify-env` poi `source spotify-env/bin/activate`

4. **Installa le dipendenze**: `pip install -r requirements.txt`

5. **Avvia l'applicazione**: `python app.py`

### Opzione 2: Scaricare l'EXE (Windows)

Puoi scaricare direttamente il file .exe dalla sezione Releases o crearlo tu stesso seguendo le istruzioni nella sezione "Creare file EXE".

### Opzione 3: Versione Flet 

La versione Flet offre un'interfaccia moderna e può essere esportata per Android, iOS e Web.

1. **Installa Flet**: `pip install flet`

2. **Avvia l'app Flet**: `flet run app_flet.py`

3. **Vantaggi rispetto alla versione Tkinter**:
   - Interfaccia Material Design moderna
   - Tema scuro automatico
   - Progress bar visiva
   - Log in tempo reale
   - Esportabile per Android/iOS/Web

## Utilizzo

### Primo Avvio

1. Configura la TUA App Spotify Developer (vedi sezione Configurazione Spotify)

2. Avvia l'applicazione: `python app.py` (oppure doppio clic su SpotifyReorderer.exe)

3. Inserisci le TUE credenziali:
   - **Client ID**: Copiato dalla tua dashboard Spotify Developer
   - **Client Secret**: Copiato dalla tua dashboard Spotify Developer
   - **Link Playlist**: URL della playlist da riordinare

4. Clicca su "Riordina Playlist"

5. Autorizza l'app nel browser che si aprira automaticamente

6. Attendi il completamento: La progress bar mostrera l'avanzamento

### Esempio di Output

Playlist con 247 elementi totali - Trovati 245 brani validi su 247 totali - Ordinamento completato: 245 brani - Invio in 3 batch da 100 brani - Batch 1/3: brani 1-100 - Batch 2/3: brani 101-200 - Batch 3/3: brani 201-245 - Playlist riordinata con successo!

## Configurazione Spotify

### Creare la tua App Spotify Developer (Obbligatorio per ogni utente)

1. **Accedi a Spotify Developer Dashboard**: Vai su https://developer.spotify.com/dashboard e accedi con il tuo account Spotify

2. **Crea una nuova app**: Clicca su "Create app", compila i campi:
   - **App name**: Spotify Playlist Reorderer (o nome a piacere)
   - **App description**: Tool per riordinare playlist automaticamente
   - **Redirect URI**: http://127.0.0.1:8888/callback
   - Accetta i termini e clicca "Save"

3. **Ottieni le tue credenziali**: Clicca sulla tua app, vai su "Settings", copia **Client ID** e **Client Secret**

4. **Configura Redirect URI**: Assicurati che sia impostato: http://127.0.0.1:8888/callback - Clicca "Add" e poi "Save"

### Note Importanti

- Non condividere mai il tuo Client Secret con nessuno
- Il Redirect URI deve corrispondere esattamente a quello nel codice
- L'app e per uso personale
- Ogni utente deve creare la propria app, non usare quella di altri

## Creare file EXE (Windows)

Se vuoi trasformare l'applicazione in un file eseguibile .exe che puoi avviare con un doppio clic:

### Passaggi:

1. **Attiva l'ambiente virtuale**: `.\spotify-env\Scripts\Activate.ps1`

2. **Installa PyInstaller**: `pip install pyinstaller`

3. **Crea l'exe**: `pyinstaller --noconfirm --onefile --windowed --name "SpotifyReorderer" app.py`

4. **Trova il file**: L'exe sara nella cartella `dist/SpotifyReorderer.exe`

### Note importanti:

- **Dimensione**: L'exe pesera circa 15-25 MB (include Python e le librerie)
- **Primo avvio**: Windows potrebbe mostrare un avviso di sicurezza. Clicca su "Altre informazioni" e poi "Esegui comunque"
- **Settings.json**: Le credenziali verranno salvate nella stessa cartella dell'exe
- **Consiglio**: Crea una cartella dedicata per l'exe (es. C:\Apps\SpotifyReorderer\)

## Come Funziona

### Algoritmo di Ordinamento

L'applicazione utilizza un algoritmo di ordinamento a tre livelli:
1. Nome artista (A-Z)
2. Data di uscita (YYYY-MM-DD)
3. Numero traccia nell'album

### Gestione Playlist Grandi

Per playlist con piu di 100 brani:
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
- app.py (Applicazione GUI principale)
- reorder_playlist.py (Versione CLI terminale)
- requirements.txt (Dipendenze Python)
- settings.json (Credenziali salvate - auto-generato, NON committare)
- .gitignore (File ignorati da Git)
- LICENSE (Licenza MIT)
- README.md (Documentazione)
- dist/ (Cartella contenente l'exe dopo la compilazione)
- build/ (Cartella temporanea di PyInstaller)

## Risoluzione Problemi

### Errori Comuni

**"Invalid client"** - Causa: Client ID o Secret errati - Soluzione: Verifica di aver copiato correttamente le credenziali dalla TUA dashboard Spotify Developer

**"Redirect URI mismatch"** - Causa: Il Redirect URI non corrisponde - Soluzione: Assicurati che sia http://127.0.0.1:8888/callback

**"HTTP Error 429: Too Many Requests"** - Causa: Troppe richieste in poco tempo - Soluzione: Attendi qualche minuto, l'app gestisce automaticamente i retry

**"Nessun brano valido trovato"** - Causa: Playlist vuota o contenente solo podcast/file locali - Soluzione: Verifica che la playlist contenga brani musicali

**"ModuleNotFoundError: No module named 'spotipy'"** - Causa: Dipendenze non installate - Soluzione: pip install -r requirements.txt

**"Windows ha protetto il tuo PC"** (solo exe) - Causa: L'exe non ha firma digitale - Soluzione: Clicca "Altre informazioni" e poi "Esegui comunque"

## Licenza

Distribuito sotto licenza MIT. Vedi LICENSE per maggiori informazioni.

Copyright (c) 2026 GIGIcln

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

---

**Se ti piace questo progetto, lascia una stella sulla repository!**
