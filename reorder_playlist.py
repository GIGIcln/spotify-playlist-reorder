import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

load_dotenv()

SCOPE = "playlist-modify-public playlist-modify-private playlist-read-private"

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=os.getenv("SPOTIPY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
    redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
    scope=SCOPE
))

def estrai_playlist_id(url):
    return url.split("/")[-1].split("?")[0]

def normalizza_data(data_str):
    if not data_str:
        return "9999-99-99" 
    parti = data_str.split("-")
    anno = parti[0]
    mese = parti[1].zfill(2) if len(parti) > 1 else "01"
    giorno = parti[2].zfill(2) if len(parti) > 2 else "01"
    return f"{anno}-{mese}-{giorno}"

def riordina_playlist(playlist_url):
    playlist_id = estrai_playlist_id(playlist_url)
    print("⏳ Download dei brani e metadati in corso...")

    tracks_data = []
    
    # Scarica tutti i dati della playlist
    results = sp.playlist_items(playlist_id)
    
    while results:
        for entry in results['items']:
            # 🔧 CORREZIONE: Spotify ora usa 'item' invece di 'track'
            # Controlla entrambi i formati per compatibilità
            content = entry.get('item') or entry.get('track')
            
            if content is None:
                continue  # Salta elementi vuoti
            
            # Accetta solo brani musicali, non podcast/episodi
            if content.get('type') != 'track':
                continue
                
            # Salta tracce locali (file sul tuo PC non accessibili via API)
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

        results = sp.next(results) if results.get('next') else None

    if not tracks_data:
        print("❌ Nessun brano valido trovato.")
        print("💡 Controlla che la playlist contenga canzoni (non podcast) e che non siano file locali.")
        return

    print(f"🎵 Trovati {len(tracks_data)} brani. Ordinamento in corso...")

    # 🔄 LOGICA DI RIORDINAMENTO (i tuoi 3 criteri)
    tracks_data.sort(key=lambda t: (
        t['artista'],           # 1️⃣ Ordine alfabetico artista
        t['data_uscita'],       # 2️⃣ Data di uscita
        t['posizione_album']    # 3️⃣ Ordine nell'album originale
    ))

    nuovo_ordine = [t['uri'] for t in tracks_data]

    print("💾 Salvataggio su Spotify...")
    try:
        if len(nuovo_ordine) > 100:
            # Gestione playlist lunghe (>100 brani)
            sp.playlist_replace_items(playlist_id, [])
            for i in range(0, len(nuovo_ordine), 100):
                sp.playlist_add_items(playlist_id, nuovo_ordine[i:i+100])
        else:
            sp.playlist_replace_items(playlist_id, nuovo_ordine)
        print("✅ Playlist riordinata con successo!")
    except Exception as e:
        print(f"❌ Errore: {e}")

if __name__ == "__main__":
    link = input("🔗 Incolla il link della playlist Spotify: ")
    riordina_playlist(link)