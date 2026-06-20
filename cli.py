from auth import create_client
from playlist import riordina_playlist, CRITERI_ORDINAMENTO


def scegli_playlist(sp) -> str:
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

    print(f"\n{'N°':<5} {'Playlist':<50} {'Brani':>6}")
    print("-" * 63)
    for i, p in enumerate(playlists, 1):
        nome = p["name"][:48] + ".." if len(p["name"]) > 50 else p["name"]
        print(f"{i:<5} {nome:<50} {p['tracks']:>6}")

    print()
    while True:
        try:
            scelta = int(input(f"Scegli una playlist (1-{len(playlists)}): "))
            if 1 <= scelta <= len(playlists):
                return playlists[scelta - 1]["id"]
            print(f"⚠️  Inserisci un numero tra 1 e {len(playlists)}.")
        except ValueError:
            print("⚠️  Inserisci un numero valido.")


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

    playlist_id = scegli_playlist(sp)
    criterio = scegli_criterio()
    riordina_playlist(sp, "https://open.spotify.com/playlist/" + playlist_id, criterio)


if __name__ == "__main__":
    main()
