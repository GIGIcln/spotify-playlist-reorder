import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth


# 1. CREDENZIALI (inserite direttamente, senza variabili d'ambiente)
CLIENT_ID = "43cb1c95f8134343926d894ec86c651b"
CLIENT_SECRET = "e9c2e0e14a00442399d05b3c0eb9d975"
REDIRECT_URI = "http://127.0.0.1:8888/callback"

# 2. PERMESSI
SCOPE = "playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private"

# 3. CACHE
CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".spotify_token_cache")
if os.path.exists(CACHE_PATH):
    os.remove(CACHE_PATH)

print("⏳ Avvio procedura di autenticazione Spotify...")
print("🌐 Il browser dovrebbe aprirsi automaticamente a breve.\n")

# 4. AUTENTICAZIONE
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SCOPE,
    cache_path=CACHE_PATH,
    open_browser=True
))

print("✅ Autenticazione completata con successo!\n")

# DEBUG: Verifica gli scope del token
print("🔍 DEBUG: Verifica permessi del token...")
try:
    token_info = sp.auth_manager.get_cached_token()
    if token_info:
        scopes = token_info.get('scope', 'Nessuno scope trovato')
        print(f"✅ Scope del token: {scopes}")
    else:
        print("⚠️ Nessun token trovato nella cache.")
except Exception as e:
    print(f"❌ Errore nel verificare gli scope: {e}")

print("\n" + "="*80 + "\n")

# DEBUG: Chi sono io e chi è il proprietario della playlist?
print("🔍 DEBUG: Verifica account...")
try:
    me = sp.current_user()
    print(f"✅ IO SONO: {me['id']} ({me['display_name']})")
except Exception as e:
    print(f"❌ Errore nel recuperare l'utente: {e}")
    exit(1)

# Prova a ottenere la playlist per vedere chi è il proprietario
playlist_id_debug = "0EWJQ38fuPDwGpGifCqmpn"
try:
    playlist_info = sp.playlist(playlist_id_debug)
    owner = playlist_info['owner']['id']
    is_public = playlist_info['public']
    print(f"✅ LA PLAYLIST È DI: {owner}")
    print(f"✅ LA PLAYLIST È PUBBLICA: {is_public}")
    
    if me['id'] != owner:
        print(f"\n⚠️ ATTENZIONE: L'account autenticato ({me['id']}) NON è il proprietario della playlist ({owner})!")
        print("Questo è il motivo dell'errore 403 Forbidden.")
        print("Devi autorizzare l'app con l'account che possiede la playlist.")
except Exception as e:
    print(f"❌ Errore nel recuperare la playlist: {e}")
    print("La playlist potrebbe essere privata e tu non hai i permessi per vederla.")

print("\n" + "="*80 + "\n")

# --- DA QUI IN POI IL TUO CODICE ORIGINALE PROSEGUE ---
# def riordina_playlist(link):
#     ...
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
    results = sp.playlist_items(playlist_id, additional_types=['track'])
    
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