from spotipy import Spotify

CRITERI_ORDINAMENTO = [
    {
        "label": "Artista → Data → Posizione (attuale)",
        "key": lambda t: (t["artista"], t["data_uscita"], t["posizione_album"]),
        "reverse": False,
    },
    {
        "label": "Data di uscita (dal più vecchio)",
        "key": lambda t: t["data_uscita"],
        "reverse": False,
    },
    {
        "label": "Data di uscita (dal più recente)",
        "key": lambda t: t["data_uscita"],
        "reverse": True,
    },
    {
        "label": "Artista (A→Z)",
        "key": lambda t: t["artista"],
        "reverse": False,
    },
    {
        "label": "Popolarità (dal più popolare)",
        "key": lambda t: t.get("popularity", 0),
        "reverse": True,
    },
]

DEFAULT_CRITERIO = CRITERI_ORDINAMENTO[0]


def estrai_playlist_id(url: str) -> str:
    return url.split("/")[-1].split("?")[0]


def normalizza_data(data_str: str) -> str:
    if not data_str:
        return "9999-99-99"
    parti = data_str.split("-")
    anno = parti[0]
    mese = parti[1].zfill(2) if len(parti) > 1 else "01"
    giorno = parti[2].zfill(2) if len(parti) > 2 else "01"
    return f"{anno}-{mese}-{giorno}"


def fetch_tracks(sp: Spotify, playlist_id: str) -> list[dict]:
    tracks = []
    results = sp.playlist_items(playlist_id, additional_types=["track"])
    while results:
        for entry in results["items"]:
            content = entry.get("item") or entry.get("track")
            if content is None or content.get("type") != "track":
                continue
            if content.get("is_local", False) or not content.get("uri"):
                continue
            try:
                tracks.append({
                    "uri": content["uri"],
                    "artista": content["artists"][0]["name"].strip().lower()
                               if content.get("artists") else "zzz_unknown",
                    "data_uscita": normalizza_data(content["album"]["release_date"])
                                   if content.get("album") else "9999-99-99",
                    "posizione_album": content.get("track_number", 0),
                    "popularity": content.get("popularity", 0),
                })
            except Exception as e:
                print(f"⚠️ Traccia ignorata: {e}")
        results = sp.next(results) if results.get("next") else None
    return tracks


def calcola_ordine_target(tracks: list[dict], criterio: dict = None) -> list[int]:
    if criterio is None:
        criterio = DEFAULT_CRITERIO
    indexed = list(enumerate(tracks))
    indexed_sorted = sorted(
        indexed,
        key=lambda x: criterio["key"](x[1]),
        reverse=criterio["reverse"],
    )
    return [orig_idx for orig_idx, _ in indexed_sorted]


def applica_riordinamento(sp: Spotify, playlist_id: str, target_order: list[int]) -> int:
    current_order = list(range(len(target_order)))
    snapshot_id = None
    moves = 0

    for i, orig_idx in enumerate(target_order):
        current_pos = current_order.index(orig_idx)
        if current_pos == i:
            continue
        insert_before = i if current_pos > i else i + 1
        result = sp.playlist_reorder_items(
            playlist_id,
            range_start=current_pos,
            insert_before=insert_before,
            range_length=1,
            snapshot_id=snapshot_id,
        )
        snapshot_id = result.get("snapshot_id")
        moves += 1
        item = current_order.pop(current_pos)
        current_order.insert(i, item)

    return moves


def riordina_playlist(sp: Spotify, playlist_url: str, criterio: dict = None) -> None:
    playlist_id = estrai_playlist_id(playlist_url)
    print("⏳ Download dei brani e metadati in corso...")

    tracks = fetch_tracks(sp, playlist_id)

    if not tracks:
        print("❌ Nessun brano valido trovato.")
        print("💡 Controlla che la playlist contenga canzoni (non podcast) e che non siano file locali.")
        return

    print(f"🎵 Trovati {len(tracks)} brani. Calcolo dell'ordine in corso...")

    target_order = calcola_ordine_target(tracks, criterio)
    if target_order == list(range(len(tracks))):
        print("✅ La playlist è già nell'ordine corretto. Nessuna modifica necessaria.")
        return

    print("💾 Riordinamento su Spotify in corso (date di aggiunta preservate)...")
    try:
        moves = applica_riordinamento(sp, playlist_id, target_order)
        print(f"✅ Playlist riordinata con successo! ({moves} spostamenti effettuati)")
    except Exception as e:
        print(f"❌ Errore durante il riordinamento: {e}")
