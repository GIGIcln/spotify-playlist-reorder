from auth import create_client
from playlist import riordina_playlist, CRITERI_ORDINAMENTO


def _parse_selezione(raw: str, n: int) -> list[int] | None:
    """Converte '1,3-5,7' in lista di indici 0-based. Ritorna None se non valido."""
    indices = []
    for token in raw.split(","):
        token = token.strip()
        if "-" in token:
            parts = token.split("-", 1)
            try:
                a, b = int(parts[0]), int(parts[1])
            except ValueError:
                return None
            if not (1 <= a <= b <= n):
                return None
            indices.extend(range(a - 1, b))
        else:
            try:
                v = int(token)
            except ValueError:
                return None
            if not (1 <= v <= n):
                return None
            indices.append(v - 1)
    seen = set()
    return [i for i in indices if not (i in seen or seen.add(i))]


def scegli_playlist(sp) -> list[str]:
    print("📋 Caricamento delle tue playlist...")
    playlists = []
    results = sp.current_user_playlists()
    while results:
        for item in results["items"]:
            if item:
                playlists.append({
                    "name": item["name"],
                    "id": item["id"],
                    "tracks": item["tracks"]["total"],
                })
        results = sp.next(results) if results.get("next") else None

    if not playlists:
        print("❌ Nessuna playlist trovata nel tuo account.")
        raise SystemExit(1)

    n = len(playlists)
    print(f"\n{'N°':<5} {'Playlist':<50} {'Brani':>6}")
    print("-" * 63)
    for i, p in enumerate(playlists, 1):
        nome = p["name"][:48] + ".." if len(p["name"]) > 50 else p["name"]
        print(f"{i:<5} {nome:<50} {p['tracks']:>6}")

    print()
    while True:
        raw = input(f"Scegli playlist (es. 1 | 1,3 | 2-5): ").strip()
        indices = _parse_selezione(raw, n)
        if indices:
            return [playlists[i]["id"] for i in indices]
        print(f"⚠️  Formato non valido. Usa numeri tra 1 e {n}, separati da virgola o range (es. 2-4).")


def scegli_criterio() -> dict:
    print(f"\n{'N°':<5} {'Criterio di ordinamento'}")
    print("-" * 55)
    for i, c in enumerate(CRITERI_ORDINAMENTO, 1):
        default = " (default)" if i == 1 else ""
        print(f"{i:<5} {c['label']}{default}")
    print()
    while True:
        raw = input(f"Scegli criterio (1-{len(CRITERI_ORDINAMENTO)}, invio per default): ").strip()
        if raw == "":
            return CRITERI_ORDINAMENTO[0]
        try:
            scelta = int(raw)
            if 1 <= scelta <= len(CRITERI_ORDINAMENTO):
                return CRITERI_ORDINAMENTO[scelta - 1]
            print(f"⚠️  Inserisci un numero tra 1 e {len(CRITERI_ORDINAMENTO)}.")
        except ValueError:
            print("⚠️  Inserisci un numero valido.")


def main() -> None:
    print("⏳ Avvio procedura di autenticazione Spotify...")
    print("🌐 Il browser dovrebbe aprirsi automaticamente a breve.\n")

    try:
        sp = create_client()
    except ValueError as e:
        print(f"❌ {e}")
        raise SystemExit(1)

    print("✅ Autenticazione completata con successo!\n")

    playlist_ids = scegli_playlist(sp)
    criterio = scegli_criterio()

    for i, playlist_id in enumerate(playlist_ids, 1):
        if len(playlist_ids) > 1:
            print(f"\n▶ Playlist {i}/{len(playlist_ids)}")
        riordina_playlist(sp, "https://open.spotify.com/playlist/" + playlist_id, criterio)


if __name__ == "__main__":
    main()
