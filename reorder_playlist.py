import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI", "http://127.0.0.1:8888/callback")

if not CLIENT_ID or not CLIENT_SECRET:
    print("❌ Credenziali mancanti. Verifica il file .env")
    exit(1)

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

    results = sp.playlist_items(playlist_id, additional_types=['track'])

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

        results = sp.next(results) if results.get('next') else None

    if not tracks_data:
        print("❌ Nessun brano valido trovato.")
        print("💡 Controlla che la playlist contenga canzoni (non podcast) e che non siano file locali.")
        return

    print(f"🎵 Trovati {len(tracks_data)} brani. Calcolo dell'ordine in corso...")

    # Ordina mantenendo l'indice originale per gestire i duplicati
    indexed = list(enumerate(tracks_data))
    indexed_sorted = sorted(indexed, key=lambda x: (
        x[1]['artista'],
        x[1]['data_uscita'],
        x[1]['posizione_album']
    ))

    target_order = [orig_idx for orig_idx, _ in indexed_sorted]
    current_order = list(range(len(tracks_data)))

    if target_order == current_order:
        print("✅ La playlist è già nell'ordine corretto. Nessuna modifica necessaria.")
        return

    print("💾 Riordinamento su Spotify in corso (date di aggiunta preservate)...")

    snapshot_id = None
    moves = 0

    for i, orig_idx in enumerate(target_order):
        current_pos = current_order.index(orig_idx)
        if current_pos == i:
            continue

        # Se sposto indietro: insert_before=i; se sposto avanti: insert_before=i+1
        insert_before = i if current_pos > i else i + 1

        try:
            result = sp.playlist_reorder_items(
                playlist_id,
                range_start=current_pos,
                insert_before=insert_before,
                range_length=1,
                snapshot_id=snapshot_id
            )
            snapshot_id = result.get('snapshot_id')
            moves += 1
            item = current_order.pop(current_pos)
            current_order.insert(i, item)
        except Exception as e:
            print(f"❌ Errore durante il riordinamento alla posizione {i}: {e}")
            return

    print(f"✅ Playlist riordinata con successo! ({moves} spostamenti effettuati)")

def scegli_playlist():
    print("📋 Caricamento delle tue playlist...")
    playlists = []
    results = sp.current_user_playlists()
    while results:
        for item in results['items']:
            if item:
                playlists.append({'name': item['name'], 'id': item['id'], 'tracks': item['tracks']['total']})
        results = sp.next(results) if results.get('next') else None

    if not playlists:
        print("❌ Nessuna playlist trovata nel tuo account.")
        exit(1)

    print(f"\n{'N°':<5} {'Playlist':<50} {'Brani':>6}")
    print("-" * 63)
    for i, p in enumerate(playlists, 1):
        nome = p['name'][:48] + ".." if len(p['name']) > 50 else p['name']
        print(f"{i:<5} {nome:<50} {p['tracks']:>6}")

    print()
    while True:
        try:
            scelta = int(input(f"Scegli una playlist (1-{len(playlists)}): "))
            if 1 <= scelta <= len(playlists):
                return playlists[scelta - 1]['id']
            print(f"⚠️  Inserisci un numero tra 1 e {len(playlists)}.")
        except ValueError:
            print("⚠️  Inserisci un numero valido.")

if __name__ == "__main__":
    playlist_id = scegli_playlist()
    riordina_playlist("https://open.spotify.com/playlist/" + playlist_id)