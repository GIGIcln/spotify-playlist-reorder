import json
import os
import time
from collections import Counter, defaultdict, deque
from datetime import datetime

from spotipy import Spotify
from tqdm import tqdm
from colori import bold, dim, cyan, verde, giallo

CRITERI_ORDINAMENTO = [
    {
        "slug": "default",
        "label": "Artista → Data → Posizione (attuale)",
        "key": lambda t: (t["artista"], t["data_uscita"], t["posizione_album"]),
        "reverse": False,
    },
    {
        "slug": "data-asc",
        "label": "Data di uscita (dal più vecchio)",
        "key": lambda t: t["data_uscita"],
        "reverse": False,
    },
    {
        "slug": "data-desc",
        "label": "Data di uscita (dal più recente)",
        "key": lambda t: t["data_uscita"],
        "reverse": True,
    },
    {
        "slug": "artista",
        "label": "Artista (A→Z)",
        "key": lambda t: t["artista"],
        "reverse": False,
    },
    {
        "slug": "popolarita",
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
            album = content.get("album") or {}
            artisti = content.get("artists") or []
            try:
                tracks.append({
                    "uri": content["uri"],
                    "nome": content.get("name", "Sconosciuto"),
                    "artista": artisti[0]["name"].strip().lower() if artisti else "zzz_unknown",
                    "artista_nome": artisti[0]["name"].strip() if artisti else "Sconosciuto",
                    "data_uscita": normalizza_data(album.get("release_date")),
                    "posizione_album": content.get("track_number", 0),
                    "popularity": content.get("popularity", 0),
                })
            except (KeyError, IndexError, TypeError, AttributeError) as e:
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
    """Reorder playlist tracks. on_progress(done, total) is called after each step.

    Ritorna il numero di chiamate `playlist_reorder_items` effettuate.

    L'algoritmo scorre le posizioni da sinistra a destra mantenendo l'invariante
    che le prime `i` posizioni sono già corrette. Ad ogni passo cerca in O(1) dove
    si trova il prossimo brano e, se combacia con un blocco già contiguo, lo sposta
    con un'unica chiamata (`range_length > 1`) invece di una per brano.
    """
    current_order = list(range(len(target_order)))
    pos_of = {v: idx for idx, v in enumerate(current_order)}
    snapshot_id = None
    moves = 0
    total = len(target_order)

    with tqdm(total=total, desc="Riordinamento", unit="pos") as pbar:
        i = 0
        while i < total:
            p = pos_of[target_order[i]]  # posizione attuale del brano atteso in i (>= i)

            # Estende il blocco finché i brani contigui a partire da p combaciano
            # con la sequenza target: verranno spostati tutti in una sola chiamata.
            k = 1
            while (
                i + k < total
                and p + k < total
                and current_order[p + k] == target_order[i + k]
            ):
                k += 1

            if p != i:
                result = _reorder_with_retry(
                    sp,
                    playlist_id,
                    range_start=p,
                    insert_before=i,  # p >= i: il blocco va sempre inserito prima di i
                    range_length=k,
                    snapshot_id=snapshot_id,
                )
                snapshot_id = result.get("snapshot_id")
                moves += 1

                block = current_order[p:p + k]
                del current_order[p:p + k]
                current_order[i:i] = block
                # Riallinea le posizioni nella sola regione modificata [i, p+k).
                for j in range(i, p + k):
                    pos_of[current_order[j]] = j

            i += k
            pbar.update(k)
            pbar.set_postfix(spostamenti=moves)
            if on_progress:
                on_progress(i, total)

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
    dry_run: bool = False,
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

    if dry_run:
        _mostra_anteprima(tracks, target_order)
        print(dim("\n🔍 Dry-run: nessuna modifica applicata alla playlist."))
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


def esporta_backup(sp: Spotify, playlist_id: str, dest_dir: str = ".") -> str:
    """Salva l'ordine attuale della playlist in un file JSON. Ritorna il percorso.

    Il backup contiene l'ordine dei brani (URI + etichetta leggibile) e serve
    come rete di sicurezza: `ripristina_backup` riporta la playlist a questo ordine.
    """
    try:
        info = sp.playlist(playlist_id, fields="name")
    except Exception:
        info = {}
    nome = info.get("name", playlist_id)
    tracks = fetch_tracks(sp, playlist_id)

    data = {
        "playlist_id": playlist_id,
        "playlist_name": nome,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "tracks": [{"uri": t["uri"], "nome": f"{t['artista']} — {t['nome']}"} for t in tracks],
    }

    os.makedirs(dest_dir, exist_ok=True)
    path = os.path.join(dest_dir, f"{playlist_id}-{datetime.now():%Y%m%d-%H%M%S}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def ripristina_backup(
    sp: Spotify,
    file_path: str,
    me_id: str = None,
    chiedi_conferma: bool = False,
    dry_run: bool = False,
) -> None:
    """Ripristina l'ordine di una playlist da un file di backup.

    Per prudenza il ripristino si rifiuta se la playlist è cambiata dal backup
    (brani aggiunti o rimossi): l'insieme dei brani deve combaciare esattamente.
    """
    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)
    playlist_id = data["playlist_id"]
    saved_uris = [t["uri"] for t in data["tracks"]]

    if me_id is not None:
        modificabile, dettaglio = verifica_proprietario(sp, playlist_id, me_id)
        if not modificabile:
            print(giallo(f"⚠️  Salto: {dettaglio}."))
            print(dim("   Non hai i permessi per modificarla."))
            return

    print("⏳ Confronto con lo stato attuale della playlist...")
    current = fetch_tracks(sp, playlist_id)
    current_uris = [t["uri"] for t in current]

    if Counter(saved_uris) != Counter(current_uris):
        aggiunti = sum((Counter(current_uris) - Counter(saved_uris)).values())
        rimossi = sum((Counter(saved_uris) - Counter(current_uris)).values())
        print(giallo("❌ La playlist è cambiata rispetto al backup: ripristino annullato."))
        print(dim(f"   Backup: {len(saved_uris)} brani · Attuale: {len(current_uris)} brani "
                  f"(+{aggiunti} aggiunti, −{rimossi} rimossi)."))
        return

    # I brani combaciano: costruisce l'ordine bersaglio che riproduce il backup.
    buckets = defaultdict(deque)
    for idx, t in enumerate(current):
        buckets[t["uri"]].append(idx)
    target_order = [buckets[uri].popleft() for uri in saved_uris]

    if target_order == list(range(len(current))):
        print("✅ La playlist è già nell'ordine del backup. Nessuna modifica necessaria.")
        return

    if dry_run:
        _mostra_anteprima(current, target_order)
        print(dim("\n🔍 Dry-run: nessuna modifica applicata alla playlist."))
        return

    if chiedi_conferma:
        _mostra_anteprima(current, target_order)
        if not _conferma_interattiva(f"\n{giallo('›')} Ripristinare questo ordine dal backup? {dim('(s/N)')}: "):
            print(dim("↩️  Operazione annullata, la playlist non è stata modificata."))
            return

    print("💾 Ripristino su Spotify in corso " + dim("(date di aggiunta preservate)") + "...")
    try:
        moves = applica_riordinamento(sp, playlist_id, target_order)
        print(verde("✅ Playlist ripristinata dal backup!") + dim(f" ({moves} spostamenti effettuati)"))
    except Exception as e:
        print(giallo(f"❌ Errore durante il ripristino: {e}"))


def _stampa_analisi(nome: str, tracks: list[dict], quanti: int = 10) -> None:
    n = len(tracks)
    print("\n" + bold(cyan(f"  📊 Analisi: {nome}")) + dim(f"  ({n} brani)") + "\n")

    # Artisti più presenti (raggruppa per nome normalizzato, mostra l'originale).
    conteggio = Counter()
    display = {}
    for t in tracks:
        chiave = t["artista"]
        conteggio[chiave] += 1
        display.setdefault(chiave, t.get("artista_nome", chiave))
    print(bold("  Artisti più presenti"))
    for i, (chiave, c) in enumerate(conteggio.most_common(quanti), 1):
        brani = "brano" if c == 1 else "brani"
        print(f"  {dim(f'{i:>2}.')} {display[chiave]} {dim(f'· {c} {brani}')}")


def analizza_playlist(sp: Spotify, playlist_id: str) -> None:
    """Stampa statistiche di una playlist senza modificarla (sola lettura)."""
    try:
        info = sp.playlist(playlist_id, fields="name")
    except Exception:
        info = {}
    nome = info.get("name", playlist_id)

    print("⏳ Download dei brani e metadati in corso...")
    tracks = fetch_tracks(sp, playlist_id)
    if not tracks:
        print("❌ Nessun brano da analizzare.")
        return
    _stampa_analisi(nome, tracks)
