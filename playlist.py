import time
from spotipy import Spotify
from tqdm import tqdm
from colori import bold, dim, cyan, verde, giallo

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
                    "nome": content.get("name", "Sconosciuto"),
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


def applica_riordinamento(
    sp: Spotify,
    playlist_id: str,
    target_order: list[int],
    on_progress=None,
) -> int:
    """Reorder playlist tracks. on_progress(done, total) is called after each step."""
    current_order = list(range(len(target_order)))
    snapshot_id = None
    moves = 0
    total = len(target_order)

    with tqdm(total=total, desc="Riordinamento", unit="pos") as pbar:
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
            if on_progress:
                on_progress(i + 1, total)

    return moves


def verifica_proprietario(sp: Spotify, playlist_id: str, me_id: str) -> tuple[bool, str]:
    """Controlla se l'utente può modificare la playlist.

    Ritorna (modificabile, dettaglio): se True, `dettaglio` è il nome della
    playlist; se False, è il motivo per cui non è modificabile.
    """
    try:
        info = sp.playlist(playlist_id, fields="name,owner.id,collaborative")
    except Exception as e:
        return False, f"impossibile leggere la playlist ({e})"
    nome = info.get("name", "")
    owner = (info.get("owner") or {}).get("id")
    if owner == me_id or info.get("collaborative", False):
        return True, nome
    return False, f"la playlist \"{nome}\" è di '{owner}', non tua e non collaborativa"


def _mostra_anteprima(tracks: list[dict], target_order: list[int], quanti: int = 10) -> None:
    """Stampa i primi brani nell'ordine risultante."""
    mostrati = min(quanti, len(target_order))
    print("\n" + bold(cyan(f"  Anteprima del nuovo ordine")) + dim(f"  (primi {mostrati} di {len(target_order)})") + "\n")
    for pos, orig_idx in enumerate(target_order[:quanti], 1):
        t = tracks[orig_idx]
        anno = str(t.get("data_uscita", ""))[:4]
        print(f"  {dim(f'{pos:>2}.')} {t.get('artista', '?')} — {t.get('nome', '?')} {dim(f'({anno})')}")
    if len(target_order) > quanti:
        print(dim(f"   ... e altri {len(target_order) - quanti} brani"))


def _conferma_interattiva(prompt: str) -> bool:
    return input(prompt).strip().lower() in ("s", "si", "sì", "y", "yes")


def riordina_playlist(
    sp: Spotify,
    playlist_url: str,
    criterio: dict = None,
    me_id: str = None,
    chiedi_conferma: bool = False,
) -> None:
    if criterio is None:
        criterio = DEFAULT_CRITERIO
    playlist_id = estrai_playlist_id(playlist_url)

    # Controllo proprietario: evita l'errore 403 grezzo su playlist non tue.
    if me_id is not None:
        modificabile, dettaglio = verifica_proprietario(sp, playlist_id, me_id)
        if not modificabile:
            print(giallo(f"⚠️  Salto: {dettaglio}."))
            print(dim("   Non hai i permessi per riordinarla (Spotify risponderebbe 403 Forbidden)."))
            return

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

    if chiedi_conferma:
        _mostra_anteprima(tracks, target_order)
        if not _conferma_interattiva(f"\n{giallo('›')} Applicare questo ordine alla playlist? {dim('(s/N)')}: "):
            print(dim("↩️  Operazione annullata, la playlist non è stata modificata."))
            return

    print("💾 Riordinamento su Spotify in corso " + dim("(date di aggiunta preservate)") + "...")
    try:
        moves = applica_riordinamento(sp, playlist_id, target_order)
        print(verde(f"✅ Playlist riordinata con successo!") + dim(f" ({moves} spostamenti effettuati)"))
    except Exception as e:
        print(giallo(f"❌ Errore durante il riordinamento: {e}"))
