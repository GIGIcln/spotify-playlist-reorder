# Spotify Playlist Reorder

A Python tool that reorders your Spotify playlists by artist, release date, popularity, BPM, energy, danceability, or valence — without touching the "date added" metadata. Runs on **Windows and macOS**. Comes with both an interactive CLI and a desktop GUI.

---

## Features

- **10 sorting criteria** — from classic (artist → album → track) to audio-feature-based (BPM, energy, danceability, valence)
- **Batch processing** — select and reorder multiple playlists at once
- **Resilient API calls** — exponential backoff on 429 / 5xx errors, respects `Retry-After` headers
- **Audio-feature enrichment** — fetches tempo, energy, danceability, and valence from the Spotify API in batches of 100
- **Progress bar** — real-time feedback via `tqdm` (CLI) or a progress indicator (GUI)
- **Safe filtering** — automatically skips local files and podcast episodes
- **Token caching** — re-uses the OAuth token so you only authenticate once
- **User profile in GUI** — shows your Spotify avatar and display name after login
- **Standalone executable** — package the GUI as a self-contained app (`build.py`) for Windows (`.exe`) or macOS (`.app`)
- **Cross-platform** — all paths and browser handling work identically on Windows and macOS

---

## Project Structure

```
spotify-playlist-reorder/
├── auth.py              # OAuth client factory (SpotifyOAuth)
├── playlist.py          # Core logic: fetch, enrich, sort, reorder
├── cli.py               # Interactive terminal interface
├── gui.py               # Desktop GUI built with Flet
├── reorder_playlist.py  # CLI entry point
├── build.py             # Packages the GUI as a standalone executable
├── create_icon.py       # Generates icon.png and icon.ico from code
├── icon.png             # App icon 1024×1024 (used by macOS build)
├── icon.ico             # App icon multi-size (used by Windows build)
├── requirements.txt
├── .env                 # Spotify credentials (never commit this)
└── tests/
    ├── test_playlist.py # Unit tests for sorting & API helpers
    └── test_cli.py      # Unit tests for selection parser
```

---

## Prerequisites

- Python 3.11+
- A Spotify account
- A registered Spotify application (to obtain API credentials)

---

## Spotify App Setup

1. Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).
2. Click **Create app**.
3. Fill in any name and description.
4. Set **Redirect URI** to `http://127.0.0.1:8888/callback` and save.
5. Copy the **Client ID** and **Client Secret** from the app settings page.

---

## Installation

```bash
# Clone the repository
git clone https://github.com/GIGIcln/spotify-playlist-reorder.git
cd spotify-playlist-reorder

# Create and activate a virtual environment
python -m venv spotify-env

# Windows
spotify-env\Scripts\activate

# macOS / Linux
source spotify-env/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Configuration

Create a `.env` file in the project root (never commit it):

```dotenv
SPOTIPY_CLIENT_ID=your_client_id_here
SPOTIPY_CLIENT_SECRET=your_client_secret_here
SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
```

The first time the app runs it will open a browser tab asking you to authorise access. After you accept, the token is cached in `.spotify_token_cache` so subsequent runs are instant.

---

## Usage

### CLI

```bash
python reorder_playlist.py
```

**Interactive flow:**

1. The browser opens for OAuth (first run only).
2. A numbered table of all your playlists is displayed.
3. Select one or more playlists using numbers, comma-separated lists, or ranges:
   - `3` — playlist 3 only
   - `1,4,7` — playlists 1, 4 and 7
   - `2-5` — playlists 2 through 5
   - `1,3-5,7` — mixed syntax
4. Choose a sorting criterion.
5. The tool reorders each playlist and reports the number of moves made.

### GUI

```bash
python gui.py
```

A dark-themed desktop window opens where you can:

1. Click **Connetti a Spotify** to authenticate. Your Spotify avatar and display name will appear in the header.
2. Tick the playlists you want to reorder (or use **Seleziona tutto** / **Deseleziona tutto**).
3. Filter playlists by name using the search bar.
4. Pick a sorting criterion from the dropdown.
5. Click **Riordina** and watch the progress bar.

---

## Building a Standalone Executable

`build.py` packages the GUI into a self-contained app using `flet pack` (bundled with Flet). No Python installation is required on the target machine.

```bash
# Windows → produces dist/SpotifyPlaylistReorder.exe
python build.py

# macOS  → produces dist/SpotifyPlaylistReorder.app
python build.py
```

After the build, copy your `.env` file into the same folder as the `.exe` (Windows) or next to the `.app` bundle (macOS) before launching.

> **Icon:** the app icon is pre-built (`icon.ico` / `icon.png`). To regenerate it after design changes, run `python create_icon.py`.

---

## Sorting Criteria

| # | Criterion | Audio features required |
|---|-----------|------------------------|
| 1 | Artist → Release date → Track number *(default)* | No |
| 2 | Release date — oldest first | No |
| 3 | Release date — newest first | No |
| 4 | Artist A → Z | No |
| 5 | Popularity — highest first | No |
| 6 | BPM — slowest first | Yes |
| 7 | BPM — fastest first | Yes |
| 8 | Energy — highest first | Yes |
| 9 | Danceability — highest first | Yes |
| 10 | Valence / positivity — highest first | Yes |

Criteria 6–10 fetch audio features from Spotify in batches of 100 tracks. This adds one extra API round-trip per 100 songs but does not cost any additional API quota.

---

## How Reordering Works

The algorithm avoids a full snapshot replacement (which would reset "date added") and instead issues individual `playlist_reorder_items` calls — one per out-of-place track — while tracking the evolving `snapshot_id` to keep every call consistent. Only tracks that are actually out of position are moved, so an already-sorted playlist requires zero API calls.

---

## Rate Limit Handling

Every reorder call goes through `_reorder_with_retry`, which catches HTTP 429 (Too Many Requests), 500, 502, and 503 errors and retries with exponential backoff:

- Waits at least `2^attempt` seconds between retries.
- Respects the `Retry-After` header when present.
- Gives up after 5 attempts and re-raises the exception.

---

## Running Tests

```bash
pytest tests/
```

The test suite covers:

- URL / ID parsing
- Date normalisation (year-only, year-month, full date, empty string)
- All 10 sort criteria, including edge cases (empty list, single track, duplicates)
- Audio-feature enrichment: batching, `None` responses, API errors
- Retry logic: 429 / 503 backoff, `Retry-After` header, non-retryable errors (400)
- CLI selection parser: single, comma list, range, mixed, duplicates, invalid input

---

## Known Limitations

- **Local files** are silently skipped (Spotify does not allow reordering them via the API).
- **Podcast episodes** and non-track items are skipped.
- **Collaborative / special playlists** (e.g. "Liked Songs") cannot be modified through the playlist-modification API.
- Audio features for very new or very obscure tracks may not be available; those tracks default to `0` for sorting purposes.

---

## License

MIT — do whatever you like, just don't blame me if Spotify changes their API again.
