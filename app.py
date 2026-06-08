import tkinter as tk
from tkinter import messagebox, ttk
import json
import os
import re
import time
import spotipy
from spotipy.oauth2 import SpotifyOAuth

SETTINGS_FILE = "settings.json"

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_settings(client_id, client_secret):
    settings = {"client_id": client_id, "client_secret": client_secret}
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f)

def get_playlist_id(url):
    match = re.search(r"playlist/([a-zA-Z0-9]+)", url)
    return match.group(1) if match else None

def normalizza_data(data_str):
    if not data_str:
        return "9999-99-99"
    parti = data_str.split("-")
    anno = parti[0]
    mese = parti[1].zfill(2) if len(parti) > 1 else "01"
    giorno = parti[2].zfill(2) if len(parti) > 2 else "01"
    return f"{anno}-{mese}-{giorno}"

def riordina():
    client_id = entry_id.get().strip()
    client_secret = entry_secret.get().strip()
    playlist_url = entry_url.get().strip()

    if not client_id or not client_secret or not playlist_url:
        messagebox.showerror("Errore", "Compila tutti i campi!")
        return

    save_settings(client_id, client_secret)

    playlist_id = get_playlist_id(playlist_url)
    if not playlist_id:
        messagebox.showerror("Errore", "Link playlist non valido!")
        return

    scope = "playlist-modify-public playlist-modify-private playlist-read-private"
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri="http://127.0.0.1:8888/callback",
        scope=scope
    ))

    try:
        # FASE 1: Download di tutti i brani con paginazione
        label_status.config(text=" Download brani in corso...")
        progress_bar['value'] = 0
        root.update()

        tracks_data = []
        offset = 0
        limit = 100
        
        # Prima chiamata per ottenere il totale
        results = sp.playlist_items(playlist_id, offset=offset, limit=limit)
        
        if not results or 'items' not in results:
            raise Exception("Impossibile leggere la playlist. Verifica che sia pubblica o che tu abbia i permessi.")
        
        total_tracks = results.get('total', 0)
        print(f" Playlist con {total_tracks} elementi totali")
        
        while results:
            for entry in results['items']:
                content = entry.get('item') or entry.get('track')
                
                if content is None:
                    continue
                
                if content.get('type') != 'track':
                    continue
                
                if content.get('is_local', False):
                    continue
                
                if not content.get('uri'):
                    continue

                try:
                    tracks_data.append({
                        'uri': content['uri'],
                        'artista': content['artists'][0]['name'].strip().lower() if content.get('artists') else "zzz_unknown",
                        'data_uscita': normalizza_data(content['album']['release_date']) if content.get('album') else "9999-99-99",
                        'posizione_album': content.get('track_number', 0)
                    })
                except Exception as e:
                    print(f"⚠️ Traccia ignorata: {e}")
                    continue

            # Aggiorna progress bar
            offset += limit
            progress = min((offset / total_tracks) * 50, 50)  # 50% per il download
            progress_bar['value'] = progress
            label_status.config(text=f"⏳ Download: {offset}/{total_tracks} brani...")
            root.update()

            # Prossima pagina
            if results.get('next'):
                results = sp.next(results)
            else:
                break

        print(f"🎵 Trovati {len(tracks_data)} brani validi su {total_tracks} totali")

        if not tracks_data:
            raise Exception("Nessun brano valido trovato. La playlist potrebbe contenere solo podcast o file locali.")

        # FASE 2: Ordinamento
        label_status.config(text="🔄 Ordinamento in corso...")
        progress_bar['value'] = 50
        root.update()

        tracks_data.sort(key=lambda t: (
            t['artista'],
            t['data_uscita'],
            t['posizione_album']
        ))

        nuovo_ordine = [t['uri'] for t in tracks_data]
        print(f"✅ Ordinamento completato: {len(nuovo_ordine)} brani")

        # FASE 3: Upload su Spotify con gestione playlist grandi
        label_status.config(text="💾 Salvataggio su Spotify...")
        progress_bar['value'] = 50
        root.update()

        if len(nuovo_ordine) > 100:
            # Per playlist grandi (>100 brani): svuota e riaggiungi a blocchi
            print(f" Playlist grande: {len(nuovo_ordine)} brani. Procedura in 2 step...")
            
            # Step 1: Svuota la playlist
            label_status.config(text="🗑️ Svuotamento playlist...")
            root.update()
            sp.playlist_replace_items(playlist_id, [])
            time.sleep(1)  # Pausa per evitare rate limiting
            
            # Step 2: Aggiungi a blocchi di 100
            total_batches = (len(nuovo_ordine) + 99) // 100
            print(f"📤 Invio in {total_batches} batch da 100 brani...")
            
            for i in range(0, len(nuovo_ordine), 100):
                batch_num = (i // 100) + 1
                batch = nuovo_ordine[i:i+100]
                
                print(f"   Batch {batch_num}/{total_batches}: brani {i+1}-{min(i+100, len(nuovo_ordine))}")
                
                label_status.config(text=f" Batch {batch_num}/{total_batches}...")
                
                # Retry logic per ogni batch
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        sp.playlist_add_items(playlist_id, batch)
                        break  # Successo, esci dal retry
                    except Exception as e:
                        if attempt < max_retries - 1:
                            print(f"   ⚠️ Tentativo {attempt+1} fallito, retry in 2 secondi...")
                            time.sleep(2)
                        else:
                            raise Exception(f"Errore nel batch {batch_num}: {e}")
                
                # Aggiorna progress bar (50-100% per l'upload)
                progress = 50 + (batch_num / total_batches) * 50
                progress_bar['value'] = progress
                root.update()
                
                # Pausa tra i batch per evitare rate limiting
                if batch_num < total_batches:
                    time.sleep(0.5)
        else:
            # Per playlist piccole (<=100 brani): sostituzione diretta
            print(f"📦 Playlist piccola: {len(nuovo_ordine)} brani. Sostituzione diretta...")
            sp.playlist_replace_items(playlist_id, nuovo_ordine)
            progress_bar['value'] = 100
            root.update()

        label_status.config(text="✅ Playlist riordinata con successo!")
        progress_bar['value'] = 100
        root.update()
        
        messagebox.showinfo("Successo", 
            f"Playlist riordinata con successo!\n\n"
            f"🎵 Brani ordinati: {len(nuovo_ordine)}\n"
            f"📊 Brani totali nella playlist: {total_tracks}\n"
            f"⏭️ Brani ignorati: {total_tracks - len(nuovo_ordine)}\n\n"
            f"Criterio di ordinamento:\n"
            f"1. Artista (A-Z)\n"
            f"2. Data di uscita (dal più vecchio al più recente)\n"
            f"3. Posizione nell'album originale")

    except spotipy.exceptions.SpotifyException as e:
        label_status.config(text="❌ Errore API Spotify")
        progress_bar['value'] = 0
        messagebox.showerror("Errore Spotify", 
            f"Codice HTTP: {e.http_status}\n"
            f"Errore: {e.msg}\n\n"
            f"Se l'errore è 429 (Too Many Requests), riprova tra qualche minuto.")
    except Exception as e:
        label_status.config(text="❌ Errore durante il riordino")
        progress_bar['value'] = 0
        messagebox.showerror("Errore", str(e))

# --- Interfaccia Grafica ---
root = tk.Tk()
root.title("Spotify Playlist Reorderer")
root.geometry("500x420")
root.resizable(False, False)
root.configure(padx=20, pady=20)

settings = load_settings()

tk.Label(root, text="Client ID:", font=("Arial", 10, "bold")).pack(anchor="w")
entry_id = tk.Entry(root, width=55)
entry_id.insert(0, settings.get("client_id", ""))
entry_id.pack(pady=(0, 10))

tk.Label(root, text="Client Secret:", font=("Arial", 10, "bold")).pack(anchor="w")
entry_secret = tk.Entry(root, width=55, show="*")
entry_secret.insert(0, settings.get("client_secret", ""))
entry_secret.pack(pady=(0, 10))

tk.Label(root, text="Link Playlist Spotify:", font=("Arial", 10, "bold")).pack(anchor="w")
entry_url = tk.Entry(root, width=55)
entry_url.pack(pady=(0, 15))

btn = tk.Button(root, text="🎵 Riordina Playlist", command=riordina, 
                bg="#1DB954", fg="white", font=("Arial", 12, "bold"), width=25, height=2)
btn.pack(pady=10)

# Progress bar
progress_bar = ttk.Progressbar(root, orient='horizontal', length=400, mode='determinate')
progress_bar.pack(pady=10)

label_status = tk.Label(root, text="In attesa... Inserisci i dati e clicca Riordina", 
                        fg="gray", font=("Arial", 9))
label_status.pack(pady=5)

# Info
info_text = tk.Label(root, 
                     text="💡 Supporta playlist fino a 500+ brani\n"
                          "📋 Ordina per: Artista → Data → Posizione album\n"
                          "🔒 Le credenziali vengono salvate localmente",
                     fg="blue", font=("Arial", 8), justify="left")
info_text.pack(pady=10)

root.mainloop()