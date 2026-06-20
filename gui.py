import os
import threading
import flet as ft

from auth import create_client, CACHE_PATH
from playlist import (
    fetch_tracks,
    calcola_ordine_target,
    applica_riordinamento,
    enrich_with_audio_features,
    CRITERI_ORDINAMENTO,
    estrai_playlist_id,
)


def main(page: ft.Page) -> None:
    page.title = "Spotify Playlist Reorder"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 24
    page.scroll = ft.ScrollMode.AUTO

    state: dict = {"sp": None}

    # ── widgets ──────────────────────────────────────────────────────────────
    heading = ft.Text("Spotify Playlist Reorder", size=26, weight=ft.FontWeight.BOLD)
    status_text = ft.Text("", size=13)
    auth_btn = ft.FilledButton("Connetti a Spotify")

    select_all_btn = ft.TextButton("Seleziona tutto", visible=False)
    deselect_all_btn = ft.TextButton("Deseleziona tutto", visible=False)

    playlist_column = ft.Column(controls=[], scroll=ft.ScrollMode.AUTO, height=320)

    criteria_dd = ft.Dropdown(
        label="Criterio di ordinamento",
        options=[ft.dropdown.Option(c["label"]) for c in CRITERI_ORDINAMENTO],
        value=CRITERI_ORDINAMENTO[0]["label"],
        width=460,
        visible=False,
    )

    reorder_btn = ft.FilledButton("Riordina selezionate", disabled=True, visible=False)
    progress_bar = ft.ProgressBar(width=460, visible=False)
    progress_label = ft.Text("", size=12)

    # ── helpers ───────────────────────────────────────────────────────────────
    def set_status(msg: str, color: str = "#4CAF50") -> None:
        status_text.value = msg
        status_text.color = color
        page.update()

    def get_selected_ids() -> list[str]:
        return [
            cb.data
            for cb in playlist_column.controls
            if isinstance(cb, ft.Checkbox) and cb.value
        ]

    # ── event handlers ────────────────────────────────────────────────────────
    def do_auth(_) -> None:
        auth_btn.disabled = True
        if os.path.exists(CACHE_PATH):
            set_status("Connessione in corso…", "#FF9800")
        else:
            set_status("Il browser Spotify si aprirà: clicca 'Accetta' per continuare", "#FF9800")

        def _run() -> None:
            try:
                sp = create_client()
                sp.me()  # prima chiamata API: qui si apre il browser se serve
                state["sp"] = sp
                set_status("Caricamento playlist…", "#FF9800")
                _load_playlists(sp)
                set_status("✓ Connesso con successo!")
            except Exception as exc:
                set_status(f"Errore autenticazione: {exc}", "#F44336")
                auth_btn.disabled = False
                page.update()

        threading.Thread(target=_run, daemon=True).start()

    def _load_playlists(sp) -> None:
        items: list[dict] = []
        results = sp.current_user_playlists()
        while results:
            for item in results["items"]:
                if item:
                    items.append(item)
            results = sp.next(results) if results.get("next") else None

        playlist_column.controls.clear()
        for p in items:
            playlist_column.controls.append(
                ft.Checkbox(
                    label=f"{p['name']}  ({p['tracks']['total']} brani)",
                    value=False,
                    data=p["id"],
                )
            )

        for w in (select_all_btn, deselect_all_btn, criteria_dd, reorder_btn):
            w.visible = True
        reorder_btn.disabled = False
        page.update()

    def do_select_all(_) -> None:
        for cb in playlist_column.controls:
            if isinstance(cb, ft.Checkbox):
                cb.value = True
        page.update()

    def do_deselect_all(_) -> None:
        for cb in playlist_column.controls:
            if isinstance(cb, ft.Checkbox):
                cb.value = False
        page.update()

    def do_reorder(_) -> None:
        ids = get_selected_ids()
        if not ids:
            set_status("⚠ Nessuna playlist selezionata.", "#FF9800")
            return

        criterio = next(c for c in CRITERI_ORDINAMENTO if c["label"] == criteria_dd.value)

        def _run() -> None:
            reorder_btn.disabled = True
            progress_bar.visible = True
            progress_bar.value = None  # indeterminate spinner
            page.update()

            errors: list[str] = []
            for idx, pid in enumerate(ids, 1):
                progress_label.value = f"Playlist {idx}/{len(ids)}: elaborazione…"
                page.update()
                try:
                    sp = state["sp"]
                    playlist_id = estrai_playlist_id(
                        "https://open.spotify.com/playlist/" + pid
                    )
                    tracks = fetch_tracks(sp, playlist_id)
                    if not tracks:
                        continue

                    if criterio.get("needs_audio"):
                        progress_label.value = f"Playlist {idx}/{len(ids)}: audio features…"
                        page.update()
                        tracks = enrich_with_audio_features(sp, tracks)

                    target_order = calcola_ordine_target(tracks, criterio)
                    if target_order != list(range(len(tracks))):
                        applica_riordinamento(sp, playlist_id, target_order)
                except Exception as exc:
                    errors.append(str(exc))

            progress_bar.visible = False
            progress_label.value = ""
            reorder_btn.disabled = False

            if errors:
                set_status(
                    f"Completato con {len(errors)} errori. Es: {errors[0]}", "#F44336"
                )
            else:
                set_status(f"✓ {len(ids)} playlist riordinate con successo!")

        threading.Thread(target=_run, daemon=True).start()

    # ── wire events ───────────────────────────────────────────────────────────
    auth_btn.on_click = do_auth
    select_all_btn.on_click = do_select_all
    deselect_all_btn.on_click = do_deselect_all
    reorder_btn.on_click = do_reorder

    # ── layout ────────────────────────────────────────────────────────────────
    page.add(
        heading,
        ft.Divider(height=8),
        ft.Row([auth_btn, status_text], vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ft.Divider(height=8),
        ft.Row([select_all_btn, deselect_all_btn]),
        playlist_column,
        ft.Divider(height=8),
        criteria_dd,
        ft.Row([reorder_btn]),
        progress_bar,
        progress_label,
    )


if __name__ == "__main__":
    ft.run(main)
