import os
import time
import threading
import flet as ft

from urllib.parse import urlparse
from spotipy import Spotify
from auth import create_oauth, wait_for_oauth_callback, CACHE_PATH
from playlist import (
    fetch_tracks,
    calcola_ordine_target,
    applica_riordinamento,
    enrich_with_audio_features,
    CRITERI_ORDINAMENTO,
    estrai_playlist_id,
)

# Spotify colour palette
_GREEN = "#1DB954"
_BLACK = "#121212"
_SURFACE = "#181818"
_CARD = "#282828"
_BORDER = "#3E3E3E"
_MUTED = "#B3B3B3"


def _p(horizontal: int, vertical: int) -> ft.Padding:
    return ft.Padding(left=horizontal, top=vertical, right=horizontal, bottom=vertical)


def main(page: ft.Page) -> None:
    page.title = "Spotify Playlist Reorder"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = _BLACK
    page.padding = 0
    page.window.width = 860
    page.window.height = 680
    page.window.min_width = 560
    page.window.min_height = 480

    state: dict = {"sp": None}
    _cards: list[tuple[ft.Checkbox, str]] = []

    # ── status indicator ──────────────────────────────────────────────────────
    _dot = ft.Container(width=8, height=8, border_radius=4, bgcolor=_BORDER)
    _status = ft.Text("Non connesso", size=13, color=_MUTED)

    def set_status(msg: str, kind: str = "ok") -> None:
        colour = {"ok": _GREEN, "warn": "#FF9800", "err": "#F44336"}.get(kind, _GREEN)
        _dot.bgcolor = colour
        _status.value = msg
        _status.color = colour
        page.update()

    # ── selection counter ─────────────────────────────────────────────────────
    _counter = ft.Text("0 selezionate", size=12, color=_MUTED, visible=False)

    def _update_counter() -> None:
        n = sum(1 for cb, _ in _cards if cb.value)
        _counter.value = f"{n} selezionate" if n else "0 selezionate"
        _reorder_btn.disabled = n == 0
        page.update()

    # ── playlist list ─────────────────────────────────────────────────────────
    _list = ft.ListView(controls=[], spacing=4, expand=True, padding=4)

    def _make_card(p: dict) -> ft.Container:
        count = (p.get("tracks") or {}).get("total", "?")
        cb = ft.Checkbox(
            value=False,
            fill_color={
                ft.ControlState.SELECTED: _GREEN,
                ft.ControlState.DEFAULT: _BORDER,
                ft.ControlState.HOVERED: _MUTED,
            },
            on_change=lambda _: _update_counter(),
        )
        _cards.append((cb, p["id"]))

        def _toggle(e, _cb=cb):
            _cb.value = not _cb.value
            _update_counter()

        return ft.Container(
            content=ft.Row(
                controls=[
                    cb,
                    ft.Icon(ft.Icons.QUEUE_MUSIC, color=_GREEN, size=20),
                    ft.Column(
                        controls=[
                            ft.Text(
                                p["name"],
                                size=14,
                                weight=ft.FontWeight.W_500,
                                color="white",
                                no_wrap=True,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Text(f"{count} brani", size=11, color=_MUTED),
                        ],
                        spacing=1,
                        expand=True,
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=12,
            ),
            bgcolor=_CARD,
            border_radius=8,
            padding=_p(16, 10),
            on_click=_toggle,
            ink=True,
        )

    # ── search ────────────────────────────────────────────────────────────────
    def _filter(query: str) -> None:
        q = query.strip().lower()
        for ctrl in _list.controls:
            if isinstance(ctrl, ft.Container):
                name_col = ctrl.content.controls[2]
                name = name_col.controls[0].value.lower()
                ctrl.visible = not q or q in name
        page.update()

    _search = ft.TextField(
        hint_text="Cerca playlist…",
        prefix_icon=ft.Icons.SEARCH,
        border_color=_BORDER,
        focused_border_color=_GREEN,
        bgcolor=_CARD,
        color="white",
        hint_style=ft.TextStyle(color="#555555"),
        border_radius=20,
        height=40,
        text_size=13,
        content_padding=_p(16, 0),
        visible=False,
        on_change=lambda e: _filter(e.control.value),
        expand=True,
    )

    # ── toolbar buttons ───────────────────────────────────────────────────────
    _sel_all = ft.TextButton(
        "Seleziona tutto",
        style=ft.ButtonStyle(color=_MUTED),
        visible=False,
    )
    _desel_all = ft.TextButton(
        "Deseleziona tutto",
        style=ft.ButtonStyle(color=_MUTED),
        visible=False,
    )

    # ── sort dropdown ─────────────────────────────────────────────────────────
    _criteria = ft.Dropdown(
        label="Criterio di ordinamento",
        options=[ft.dropdown.Option(c["label"]) for c in CRITERI_ORDINAMENTO],
        value=CRITERI_ORDINAMENTO[0]["label"],
        border_color=_BORDER,
        focused_border_color=_GREEN,
        fill_color=_CARD,
        color="white",
        label_style=ft.TextStyle(color=_MUTED),
        visible=False,
        expand=True,
    )

    # ── action buttons ────────────────────────────────────────────────────────
    _btn_style = ft.ButtonStyle(
        color={ft.ControlState.DEFAULT: "black", ft.ControlState.DISABLED: _MUTED},
        bgcolor={ft.ControlState.DEFAULT: _GREEN, ft.ControlState.DISABLED: _BORDER},
        shape=ft.RoundedRectangleBorder(radius=20),
        padding=_p(20, 10),
    )

    _auth_btn = ft.Button(
        "Connetti a Spotify",
        icon=ft.Icons.LOGIN,
        style=_btn_style,
    )

    _switch_btn = ft.TextButton(
        "Cambia account",
        icon=ft.Icons.SWAP_HORIZ,
        style=ft.ButtonStyle(color=_MUTED),
        visible=False,
    )

    _reorder_btn = ft.Button(
        "Riordina",
        icon=ft.Icons.SORT,
        disabled=True,
        visible=False,
        style=_btn_style,
    )

    # ── progress ──────────────────────────────────────────────────────────────
    _ring = ft.ProgressRing(width=18, height=18, stroke_width=2, color=_GREEN, visible=False)
    _prog_label = ft.Text("", size=12, color=_MUTED)
    _prog_bar = ft.ProgressBar(
        width=None,
        expand=True,
        color=_GREEN,
        bgcolor=_BORDER,
        value=0,
        visible=False,
    )

    # ── event handlers ────────────────────────────────────────────────────────
    def do_auth(_) -> None:
        _auth_btn.disabled = True
        page.update()

        def _run() -> None:
            try:
                oauth = create_oauth(show_dialog=not os.path.exists(CACHE_PATH))
                if not oauth.get_cached_token():
                    auth_url = oauth.get_authorize_url()
                    port = urlparse(oauth.redirect_uri).port or 8888
                    set_status("Il browser si aprirà: clicca 'Accetta' per continuare", "warn")
                    os.startfile(auth_url)
                    code = wait_for_oauth_callback(port)
                    oauth.get_access_token(code, as_dict=False)
                else:
                    set_status("Connessione in corso…", "warn")

                sp = Spotify(auth_manager=oauth)
                sp.me()
                state["sp"] = sp
                set_status("Caricamento playlist…", "warn")
                _load_playlists(sp)
                set_status("Connesso")
            except Exception as exc:
                set_status(f"Errore: {exc}", "err")
                _auth_btn.disabled = False
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

        _cards.clear()
        _list.controls.clear()
        for p in items:
            _list.controls.append(_make_card(p))

        for w in (_sel_all, _desel_all, _counter, _criteria, _reorder_btn, _search, _switch_btn):
            w.visible = True
        _auth_btn.visible = False
        _update_counter()
        page.update()

    def do_select_all(_) -> None:
        for ctrl in _list.controls:
            if isinstance(ctrl, ft.Container) and ctrl.visible:
                cb_widget = ctrl.content.controls[0]
                if isinstance(cb_widget, ft.Checkbox):
                    cb_widget.value = True
        _update_counter()

    def do_deselect_all(_) -> None:
        for cb, _ in _cards:
            cb.value = False
        _update_counter()

    def do_reorder(_) -> None:
        selected = [(cb, pid) for cb, pid in _cards if cb.value]
        if not selected:
            set_status("Nessuna playlist selezionata.", "warn")
            return

        criterio = next(c for c in CRITERI_ORDINAMENTO if c["label"] == _criteria.value)

        def _run() -> None:
            _reorder_btn.disabled = True
            _ring.visible = True
            _prog_bar.visible = True
            _prog_bar.value = 0
            page.update()

            _last_ui = [0.0]

            def _on_progress(done: int, total: int) -> None:
                _prog_bar.value = done / total if total else 0
                now = time.monotonic()
                if done == total or now - _last_ui[0] >= 0.2:
                    _last_ui[0] = now
                    page.update()

            errors: list[str] = []
            for idx, (_, pid) in enumerate(selected, 1):
                _prog_label.value = f"Playlist {idx}/{len(selected)}: elaborazione…"
                _prog_bar.value = 0
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
                        _prog_label.value = f"Playlist {idx}/{len(selected)}: audio features…"
                        page.update()
                        tracks = enrich_with_audio_features(sp, tracks)

                    target_order = calcola_ordine_target(tracks, criterio)
                    if target_order != list(range(len(tracks))):
                        applica_riordinamento(sp, playlist_id, target_order, on_progress=_on_progress)
                except Exception as exc:
                    errors.append(str(exc))

            _ring.visible = False
            _prog_bar.visible = False
            _prog_label.value = ""
            _reorder_btn.disabled = not any(cb.value for cb, _ in _cards)

            if errors:
                set_status(f"Completato con {len(errors)} errori: {errors[0]}", "err")
            else:
                set_status(f"{len(selected)} playlist riordinate ✓")

        threading.Thread(target=_run, daemon=True).start()

    def do_switch_account(_) -> None:
        if os.path.exists(CACHE_PATH):
            os.remove(CACHE_PATH)
        state["sp"] = None
        _cards.clear()
        _list.controls.clear()
        for w in (_sel_all, _desel_all, _counter, _criteria, _reorder_btn, _search, _switch_btn):
            w.visible = False
        _auth_btn.visible = True
        _auth_btn.disabled = False
        _dot.bgcolor = _BORDER
        _status.value = "Non connesso"
        _status.color = _MUTED
        page.update()

    # ── wire events ──────────────────────────────────────────────────────────
    _auth_btn.on_click = do_auth
    _switch_btn.on_click = do_switch_account
    _sel_all.on_click = do_select_all
    _desel_all.on_click = do_deselect_all
    _reorder_btn.on_click = do_reorder

    # ── layout ───────────────────────────────────────────────────────────────
    header = ft.Container(
        content=ft.Row(
            controls=[
                ft.Row(
                    [
                        ft.Icon(ft.Icons.LIBRARY_MUSIC, color=_GREEN, size=28),
                        ft.Text(
                            "Playlist Reorder",
                            size=18,
                            weight=ft.FontWeight.BOLD,
                            color="white",
                        ),
                    ],
                    spacing=10,
                ),
                ft.Row(
                    [_dot, _status, _auth_btn, _switch_btn],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=_SURFACE,
        padding=_p(24, 14),
        border=ft.Border(bottom=ft.BorderSide(1, _BORDER)),
    )

    toolbar = ft.Container(
        content=ft.Row(
            controls=[
                _sel_all,
                _desel_all,
                _counter,
                _search,
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=4,
        ),
        padding=_p(20, 6),
        border=ft.Border(bottom=ft.BorderSide(1, _BORDER)),
    )

    body = ft.Container(
        content=_list,
        padding=_p(16, 8),
        expand=True,
    )

    bottom_bar = ft.Container(
        content=ft.Column(
            controls=[
                _prog_bar,
                ft.Row(
                    controls=[
                        _criteria,
                        ft.Row(
                            [_ring, _prog_label, _reorder_btn],
                            spacing=10,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=16,
                ),
            ],
            spacing=8,
        ),
        bgcolor=_SURFACE,
        padding=_p(24, 14),
        border=ft.Border(top=ft.BorderSide(1, _BORDER)),
    )

    page.add(
        ft.Column(
            controls=[header, toolbar, body, bottom_bar],
            expand=True,
            spacing=0,
        )
    )


if __name__ == "__main__":
    ft.run(main)
