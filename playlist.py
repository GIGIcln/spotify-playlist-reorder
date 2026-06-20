import time
from spotipy import Spotify
from tqdm import tqdm

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
    {
        "label": "BPM (dal più lento)",
        "key": lambda t: t.get("bpm", 0.0),
        "reverse": False,
        "needs_audio": True,
    },
    {
        "label": "BPM (dal più veloce)",
        "key": lambda t: t.get("bpm", 0.0),
        "reverse": True,
        "needs_audio": True,
    },
    {
        "label": "Energia (dalla più alta)",
        "key": lambda t: t.get("energy", 0.0),
        "reverse": True,
        "needs_audio": True,
    },
    {
        "label": "Danceability (dalla più alta)",
        "key": lambda t: t.get("danceability", 0.0),
        "reverse": True,
        "needs_audio": True,
    },
    {
        "label": "Valence / positività (dalla più alta)",
        "key": lambda t: t.get("valence", 0.0),
        "reverse": True,
        "needs_audio": True,
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


def enrich_with_audio_features(sp: Spotify, tracks: list[dict]) -> list[dict]:
    """Fetch BPM/energy/danceability/valence from Spotify and add them to each track dict."""
    uris = [t["uri"] for t in tracks]
    uri_to_idx = {uri: i for i, uri in enumerate(uris)}

    for batch_start in range(0, len(uris), 100):
        batch_uris = uris[batch_start:batch_start + 100]
        batch_ids = [u.split(":")[-1] for u in batch_uris]
        try:
            features_batch = sp.audio_features(batch_ids)
        except Exception as e:
            print(f"⚠️ Audio features non disponibili (batch {batch_start // 100 + 1}): {e}")
            continue

        for uri, feat in zip(batch_uris, features_batch or []):
            if not feat:
                continue
            idx = uri_to_idx[uri]
            tracks[idx]["bpm"] = feat.get("tempo", 0.0)
            tracks[idx]["energy"] = feat.get("energy", 0.0)
            tracks[idx]["danceability"] = feat.get("danceability", 0.0)
            tracks[idx]["valence"] = feat.get("valence", 0.0)

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


def _reorder_with_retry(sp: Spotify, playlist_id: str, max_retries: int = 5, **kwargs) -> dict:
    """Call playlist_reorder_items with exponential backoff on 429/5xx errors."""
    for attempt in range(max_retries):
        try:
            return sp.playlist_reorder_items(playlist_id, **kwargs)
        except Exception as e:
            http_status = getattr(e, "http_status", None)
            if http_status in (429, 500, 502, 503) and attempt < max_retries - 1:
                headers = getattr(e, "headers", {}) or {}
                retry_after = int(headers.get("Retry-After", 0))
                wait = max(retry_after, 2 ** attempt)
                time.sleep(wait)
            else:
                raise


def applica_riordinamento(sp: Spotify, playlist_id: str, target_order: list[int]) -> int:
    current_order = list(range(len(target_order)))
    snapshot_id = None
    moves = 0

    with tqdm(total=len(target_order), desc="Riordinamento", unit="pos") as pbar:
        for i, orig_idx in enumerate(target_order):
            current_pos = current_order.index(orig_idx)
            if current_pos != i:
                insert_before = i if current_pos > i else i + 1
                result = _reorder_with_retry(
                    sp,
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
            pbar.update(1)
            pbar.set_postfix(spostamenti=moves)

    return moves


def riordina_playlist(sp: Spotify, playlist_url: str, criterio: dict = None) -> None:
    if criterio is None:
        criterio = DEFAULT_CRITERIO
    playlist_id = estrai_playlist_id(playlist_url)
    print("⏳ Download dei brani e metadati in corso...")

    tracks = fetch_tracks(sp, playlist_id)

    if not tracks:
        print("❌ Nessun brano valido trovato.")
        print("💡 Controlla che la playlist contenga canzoni (non podcast) e che non siano file locali.")
        return

    if criterio.get("needs_audio"):
        print("⏳ Download audio features in corso...")
        tracks = enrich_with_audio_features(sp, tracks)

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
