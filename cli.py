import argparse
import os

from auth import create_client, _get_app_dir
from playlist import (
    riordina_playlist,
    esporta_backup,
    ripristina_backup,
    analizza_playlist,
    estrai_playlist_id,
    CRITERI_ORDINAMENTO,
)
from colori import bold, dim, cyan, blu, verde, giallo


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


def _totale_brani(item: dict) -> int:
    """Numero di brani della playlist, robusto al cambio di schema Spotify.

    L'endpoint restituisce il totale sotto 'tracks' (schema classico) oppure
    sotto 'items' (nuovo schema), con l'altro campo a None.
    """
    for chiave in ("tracks", "items"):
        campo = item.get(chiave)
        if isinstance(campo, dict) and campo.get("total") is not None:
            return campo["total"]
    return 0


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
                    "tracks": _totale_brani(item),
                })
        results = sp.next(results) if results.get("next") else None

    if not playlists:
        print(giallo("❌ Nessuna playlist trovata nel tuo account."))
        raise SystemExit(1)

    n = len(playlists)
    print("\n" + bold(cyan("  Le tue playlist")) + "\n")
    for i, p in enumerate(playlists, 1):
        nome = p["name"][:40] + ".." if len(p["name"]) > 42 else p["name"]
        numero = blu(f"{i:>3}")
        conteggio = dim(f"{p['tracks']:>5}")
        print(f"  {numero}  {nome:<44} {conteggio}")

    print()
    while True:
        raw = input(f"{giallo('›')} Scegli playlist {dim('(es. 1 · 1,3 · 2-5)')}: ").strip()
        indices = _parse_selezione(raw, n)
        if indices:
            return [playlists[i]["id"] for i in indices]
        print(giallo(f"  Formato non valido. Usa numeri tra 1 e {n}, separati da virgola o range (es. 2-4)."))


def scegli_criterio() -> dict:
    print("\n" + bold(cyan("  Criterio di ordinamento")) + "\n")
    for i, c in enumerate(CRITERI_ORDINAMENTO, 1):
        default = dim(" (default)") if i == 1 else ""
        print(f"  {blu(f'{i:>3}')}  {c['label']}{default}")
    print()
    while True:
        raw = input(f"{giallo('›')} Scegli criterio {dim(f'(1-{len(CRITERI_ORDINAMENTO)}, invio per default)')}: ").strip()
        if raw == "":
            return CRITERI_ORDINAMENTO[0]
        try:
            scelta = int(raw)
            if 1 <= scelta <= len(CRITERI_ORDINAMENTO):
                return CRITERI_ORDINAMENTO[scelta - 1]
            print(giallo(f"  Inserisci un numero tra 1 e {len(CRITERI_ORDINAMENTO)}."))
        except ValueError:
            print(giallo("  Inserisci un numero valido."))


def risolvi_criterio(valore: str) -> dict | None:
    """Risolve un criterio da numero (1-N) o slug. Ritorna None se non valido."""
    valore = valore.strip().lower()
    if valore.isdigit():
        n = int(valore)
        if 1 <= n <= len(CRITERI_ORDINAMENTO):
            return CRITERI_ORDINAMENTO[n - 1]
        return None
    for c in CRITERI_ORDINAMENTO:
        if c["slug"] == valore:
            return c
    return None


def stampa_lista_criteri() -> None:
    print("\n" + bold(cyan("  Criteri di ordinamento")) + "\n")
    for i, c in enumerate(CRITERI_ORDINAMENTO, 1):
        default = dim(" (default)") if i == 1 else ""
        print(f"  {blu(f'{i:>3}')}  {c['slug']:<11} {c['label']}{default}")
    print()


def _parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="spotify-reorder",
        description="Riordina le tue playlist Spotify da terminale, "
                    "senza alterare la data di aggiunta dei brani.",
    )
    parser.add_argument(
        "-p", "--playlist", action="append", metavar="ID_O_URL",
        help="ID o URL di una playlist (ripetibile). Se omesso, scelta interattiva.",
    )
    parser.add_argument(
        "-c", "--criterio", metavar="N_O_SLUG",
        help="Numero (1-%d) o slug del criterio. In modalità non-interattiva "
             "il default è il primo criterio. Vedi --lista-criteri."
             % len(CRITERI_ORDINAMENTO),
    )
    parser.add_argument(
        "-y", "--yes", action="store_true",
        help="Applica senza chiedere conferma (utile per script e automazioni).",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Mostra l'anteprima del nuovo ordine senza applicare modifiche.",
    )
    parser.add_argument(
        "--backup-before", action="store_true",
        help="Salva un backup dell'ordine attuale prima di riordinare (rete di sicurezza).",
    )
    parser.add_argument(
        "--no-browser", action="store_true",
        help="Non aprire mai il browser per l'auth (per esecuzioni programmate).",
    )
    parser.add_argument(
        "--analizza", action="store_true",
        help="Mostra statistiche della/e playlist (sola lettura), senza riordinare.",
    )
    parser.add_argument(
        "--lista-criteri", action="store_true",
        help="Mostra i criteri di ordinamento disponibili ed esce.",
    )
    gruppo = parser.add_mutually_exclusive_group()
    gruppo.add_argument(
        "--backup", action="store_true",
        help="Salva l'ordine attuale della/e playlist in un file, senza riordinare.",
    )
    gruppo.add_argument(
        "--restore", metavar="FILE",
        help="Ripristina l'ordine di una playlist da un file di backup.",
    )
    return parser.parse_args(argv)


def _esegui(argv=None) -> None:
    args = _parse_args(argv)

    if args.lista_criteri:
        stampa_lista_criteri()
        return

    # Valida il criterio prima di autenticarsi, così un errore fallisce subito.
    criterio = None
    if args.criterio is not None:
        criterio = risolvi_criterio(args.criterio)
        if criterio is None:
            print(giallo(f"❌ Criterio '{args.criterio}' non valido."))
            print(dim("   Usa --lista-criteri per vedere numeri e slug disponibili."))
            raise SystemExit(1)

    if args.restore and not os.path.isfile(args.restore):
        print(giallo(f"❌ File di backup non trovato: {args.restore}"))
        raise SystemExit(1)

    print(bold(cyan("\n  🎧 Spotify Playlist Reorder\n")))
    print("⏳ Avvio autenticazione Spotify...")
    print(dim("🌐 Se necessario, il browser si aprirà per autorizzare l'app.\n"))

    try:
        sp = create_client(open_browser=not args.no_browser)
    except ValueError as e:
        print(giallo(f"❌ {e}"))
        raise SystemExit(1)

    print(verde("✅ Autenticazione completata con successo!"))

    me_id = sp.current_user()["id"]

    if args.restore:
        ripristina_backup(
            sp, args.restore, me_id=me_id,
            chiedi_conferma=not args.yes, dry_run=args.dry_run,
        )
        return

    if args.playlist:
        playlist_ids = [estrai_playlist_id(p) for p in args.playlist]
    else:
        playlist_ids = scegli_playlist(sp)

    if args.analizza:
        for playlist_id in playlist_ids:
            analizza_playlist(sp, playlist_id)
        return

    if args.backup:
        dest = os.path.join(_get_app_dir(), "backups")
        for playlist_id in playlist_ids:
            path = esporta_backup(sp, playlist_id, dest)
            print(verde("💾 Backup salvato: ") + dim(path))
        return

    # Criterio: esplicito > (interattivo: menu) > (non-interattivo: default).
    if criterio is None:
        criterio = scegli_criterio() if not args.playlist else CRITERI_ORDINAMENTO[0]

    chiedi_conferma = not args.yes
    backup_dir = os.path.join(_get_app_dir(), "backups")

    for i, playlist_id in enumerate(playlist_ids, 1):
        if len(playlist_ids) > 1:
            print(bold(cyan(f"\n▶ Playlist {i}/{len(playlist_ids)}")))
        if args.backup_before and not args.dry_run:
            path = esporta_backup(sp, playlist_id, backup_dir)
            print(verde("💾 Backup salvato: ") + dim(path))
        riordina_playlist(
            sp,
            "https://open.spotify.com/playlist/" + playlist_id,
            criterio,
            me_id=me_id,
            chiedi_conferma=chiedi_conferma,
            dry_run=args.dry_run,
        )


def main(argv=None) -> None:
    try:
        _esegui(argv)
    except (KeyboardInterrupt, EOFError):
        print(dim("\n↩️  Operazione annullata."))
        raise SystemExit(130)


if __name__ == "__main__":
    main()
