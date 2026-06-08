import flet as ft
import json
import os
import re
import time
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import threading

SETTINGS_FILE = "settings.json"

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_settings(client_id, client_secret):
    settings = {"client_id": client_id, "client_secret": client_secret}
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f)

def get_playlist_id(url):
    match = re.search(r"playlist/([a-zA-Z0-9]+)", url)
    return match.group(1) if match else None

def normalizza_data(data_str):
    if not data_str:
        return "9999-99-99"
    parti = data_str.split("-")
    anno = parti[0]
    mese = parti[1].zfill(2) if len(parti) > 1 else "01"
    giorno = parti[2].zfill(2) if len(parti) > 2 else "01"
    return f"{anno}-{mese}-{giorno}"


def main(page: ft.Page):
    # Configurazione pagina
    page.title = "Spotify Playlist Reorderer"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    page.window.width = 500
    page.window.height = 650
    
    # Carica credenziali salvate
    settings = load_settings()
    
    # Controlli UI
    client_id_field = ft.TextField(
        label="Client ID",
        hint_text="Inserisci il tuo Client ID Spotify",
        value=settings.get("client_id", ""),
        border=ft.InputBorder.OUTLINE,
        width=450,
    )
    
    client_secret_field = ft.TextField(
        label="Client Secret",
        hint_text="Inserisci il tuo Client Secret",
        value=settings.get("client_secret", ""),
        password=True,
        can_reveal_password=True,
        border=ft.InputBorder.OUTLINE,
        width=450,
    )
    
    playlist_url_field = ft.TextField(
        label="Link Playlist Spotify",
        hint_text="https://open.spotify.com/playlist/...",
        border=ft.InputBorder.OUTLINE,
        width=450,
    )
    
    progress_bar = ft.ProgressBar(width=450, value=0, color="green")
    status_text = ft.Text("In attesa...", size=14, color=ft.Colors.GREY)
    log_text = ft.Text("", size=11, color=ft.Colors.GREY_400, selectable=True)
    
    def show_dialog(title, content):
        dlg = ft.AlertDialog(
            title=ft.Text(title),
            content=ft.Text(content),
            actions=[
                ft.TextButton("OK", on_click=lambda e: close_dialog(dlg))
            ]
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()
    
    def close_dialog(dlg):
        dlg.open = False
        page.update()
    
    def riordina(e):
        client_id = client_id_field.value.strip()
        client_secret = client_secret_field.value.strip()
        playlist_url = playlist_url_field.value.strip()
        
        if not client_id or not client_secret or not playlist_url:
            show_dialog("Errore", "Compila tutti i campi!")
            return
        
        # Salva credenziali
        save_settings(client_id, client_secret)
        
        playlist_id = get_playlist_id(playlist_url)
        if not playlist_id:
            show_dialog("Errore", "Link playlist non valido!")
            return
        
        # Disabilita i campi durante l'elaborazione
        client_id_field.disabled = True
        client_secret_field.disabled = True
        playlist_url_field.disabled = True
        reorder_btn.disabled = True
        log_text.value = ""
        page.update()
        
        # Esegui in un thread separato per non bloccare l'UI
        def processa():
            try:
                scope = "playlist-modify-public playlist-modify-private playlist-read-private"
                sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
                    client_id=client_id,
                    client_secret=client_secret,
                    redirect_uri="http://127.0.0.1:8888/callback",
                    scope=scope
                ))
                
                # FASE 1: Download
                status_text.value = "⏳ Download brani in corso..."
                progress_bar.value = 0
                page.update()
                
                tracks_data = []
                offset = 0
                limit = 100
                
                results = sp.playlist_items(playlist_id, offset=offset, limit=limit)
                
                if not results or 'items' not in results:
                    raise Exception("Impossibile leggere la playlist.")
                
                total_tracks = results.get('total', 0)
                log_text.value += f"Playlist con {total_tracks} elementi totali\n"
                page.update()
                
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
                        except Exception as ex:
                            log_text.value += f"⚠️ Traccia ignorata: {ex}\n"
                            page.update()
                            continue
                    
                    offset += limit
                    progress = min((offset / total_tracks) * 0.5, 0.5)
                    progress_bar.value = progress
                    status_text.value = f"⏳ Download: {min(offset, total_tracks)}/{total_tracks} brani..."
                    page.update()
                    
                    if results.get('next'):
                        results = sp.next(results)
                    else:
                        break
                
                log_text.value += f"🎵 Trovati {len(tracks_data)} brani validi\n"
                page.update()
                
                if not tracks_data:
                    raise Exception("Nessun brano valido trovato.")
                
                # FASE 2: Ordinamento
                status_text.value = "🔄 Ordinamento in corso..."
                progress_bar.value = 0.5
                page.update()
                
                tracks_data.sort(key=lambda t: (
                    t['artista'],
                    t['data_uscita'],
                    t['posizione_album']
                ))
                
                nuovo_ordine = [t['uri'] for t in tracks_data]
                log_text.value += f"✅ Ordinamento completato: {len(nuovo_ordine)} brani\n"
                page.update()
                
                # FASE 3: Upload
                status_text.value = "💾 Salvataggio su Spotify..."
                page.update()
                
                if len(nuovo_ordine) > 100:
                    log_text.value += f"📤 Playlist grande: {len(nuovo_ordine)} brani\n"
                    page.update()
                    
                    status_text.value = "🗑️ Svuotamento playlist..."
                    page.update()
                    sp.playlist_replace_items(playlist_id, [])
                    time.sleep(1)
                    
                    total_batches = (len(nuovo_ordine) + 99) // 100
                    
                    for i in range(0, len(nuovo_ordine), 100):
                        batch_num = (i // 100) + 1
                        batch = nuovo_ordine[i:i+100]
                        
                        log_text.value += f"   Batch {batch_num}/{total_batches}: brani {i+1}-{min(i+100, len(nuovo_ordine))}\n"
                        status_text.value = f"💾 Batch {batch_num}/{total_batches}..."
                        page.update()
                        
                        max_retries = 3
                        for attempt in range(max_retries):
                            try:
                                sp.playlist_add_items(playlist_id, batch)
                                break
                            except Exception as ex:
                                if attempt < max_retries - 1:
                                    log_text.value += f"   ⚠️ Tentativo {attempt+1} fallito, retry...\n"
                                    page.update()
                                    time.sleep(2)
                                else:
                                    raise Exception(f"Errore nel batch {batch_num}: {ex}")
                        
                        progress = 0.5 + (batch_num / total_batches) * 0.5
                        progress_bar.value = progress
                        page.update()
                        
                        if batch_num < total_batches:
                            time.sleep(0.5)
                else:
                    log_text.value += f"📦 Playlist piccola: {len(nuovo_ordine)} brani\n"
                    page.update()
                    sp.playlist_replace_items(playlist_id, nuovo_ordine)
                    progress_bar.value = 1.0
                    page.update()
                
                status_text.value = "✅ Playlist riordinata con successo!"
                log_text.value += f"\n✅ COMPLETATO! {len(nuovo_ordine)} brani ordinati.\n"
                progress_bar.value = 1.0
                page.update()
                
                show_dialog(
                    "Successo! 🎉",
                    f"Playlist riordinata con {len(nuovo_ordine)} brani!\n\n"
                    f"Ordinamento:\n"
                    f"1. Artista (A-Z)\n"
                    f"2. Data di uscita\n"
                    f"3. Posizione album"
                )
                
            except spotipy.exceptions.SpotifyException as ex:
                status_text.value = "❌ Errore API Spotify"
                log_text.value += f"❌ Errore {ex.http_status}: {ex.msg}\n"
                page.update()
            except Exception as ex:
                status_text.value = "❌ Errore durante il riordino"
                log_text.value += f"❌ {str(ex)}\n"
                page.update()
            finally:
                # Riabilita i campi
                client_id_field.disabled = False
                client_secret_field.disabled = False
                playlist_url_field.disabled = False
                reorder_btn.disabled = False
                page.update()
        
        # Avvia il thread
        thread = threading.Thread(target=processa, daemon=True)
        thread.start()
    
    # Layout principale
    reorder_btn = ft.ElevatedButton(
        "🎵 Riordina Playlist",
        on_click=riordina,
        color=ft.Colors.WHITE,
        bgcolor=ft.Colors.GREEN_700,
        height=50,
        width=300,
    )
    
    page.add(
        ft.Text("Spotify Playlist Reorderer", size=24, weight=ft.FontWeight.BOLD),
        ft.Text("Ordina per: Artista → Data → Album", size=12, color=ft.Colors.GREY),
        ft.Divider(),
        client_id_field,
        ft.Container(height=5),
        client_secret_field,
        ft.Container(height=5),
        playlist_url_field,
        ft.Container(height=15),
        ft.Container(content=reorder_btn, alignment=ft.Alignment(0, 0)),
        ft.Container(height=10),
        progress_bar,
        ft.Container(height=5),
        status_text,
        ft.Divider(),
        ft.Text("Log:", size=12, weight=ft.FontWeight.BOLD),
        ft.Container(
            content=ft.Column(
                [log_text],
                scroll=ft.ScrollMode.AUTO,
                height=150,
            ),
            padding=10,
            width=450,
            bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.GREY),
            border_radius=5,
        ),
    )

ft.app(target=main)